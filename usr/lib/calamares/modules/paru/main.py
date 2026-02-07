#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Paru-only Calamares packages module (AUR best-effort).
# - Only backend: paru
# - No pkgcheck
# - All operations are best-effort: failures are logged but never abort the job
# - Supports operations: install / try_install / remove / try_remove / localInstall
# - Optional: update_db / update_system
#

import subprocess
import threading
from string import Template
import gettext

import libcalamares
from libcalamares.utils import check_target_env_call
from libcalamares.utils import gettext_path, gettext_languages

_translation = gettext.translation(
    "calamares-python",
    localedir=gettext_path(),
    languages=gettext_languages(),
    fallback=True,
)
_ = _translation.gettext
_n = _translation.ngettext


# --- Progress state (module-global, as in upstream packages module) ---
total_packages = 0
completed_packages = 0
group_packages = 0

custom_status_message = None

INSTALL = object()
REMOVE = object()
mode_packages = None


def _change_mode(mode):
    global mode_packages
    mode_packages = mode
    if total_packages > 0:
        libcalamares.job.setprogress(completed_packages * 1.0 / total_packages)


def pretty_name():
    return _("Install packages.")


def pretty_status_message():
    if custom_status_message is not None:
        return custom_status_message

    if not group_packages:
        if total_packages > 0:
            s = _("Processing packages (%(count)d / %(total)d)")
        else:
            s = _("Install packages.")
    elif mode_packages is INSTALL:
        s = _n("Installing one package.", "Installing %(num)d packages.", group_packages)
    elif mode_packages is REMOVE:
        s = _n("Removing one package.", "Removing %(num)d packages.", group_packages)
    else:
        s = _("Install packages.")

    return s % {"num": group_packages, "count": completed_packages, "total": total_packages}


def subst_locale(plist):
    """
    Locale-aware list of packages:
    substitutes ${LOCALE} with chosen locale; drops LOCALE-packages if locale is 'en'.
    """
    locale = libcalamares.globalstorage.value("locale") or "en"
    ret = []
    for packagedata in plist:
        if isinstance(packagedata, str):
            packagename = packagedata
        else:
            packagename = packagedata.get("package")

        if packagename is None:
            continue

        if locale != "en":
            packagename = Template(packagename).safe_substitute(LOCALE=locale)
        elif "LOCALE" in packagename:
            packagename = None

        if packagename is None:
            continue

        if isinstance(packagedata, str):
            ret.append(packagename)
        else:
            packagedata["package"] = packagename
            ret.append(packagedata)

    return ret


def _run_script(script: str):
    if script:
        check_target_env_call(script.split(" "))


class ParuManager:
    """
    Paru-only backend.
    AUR best-effort: any failure is logged and ignored (job never fails due to package failures).
    """

    backend = "paru"

    def __init__(self):
        import shutil

        paru_cfg = libcalamares.job.configuration.get("paru", None)
        if paru_cfg is None:
            paru_cfg = {}
        if type(paru_cfg) is not dict:
            libcalamares.utils.warning("Job configuration *paru* will be ignored.")
            paru_cfg = {}

        self.paru_num_retries = paru_cfg.get("num_retries", 0)
        self.paru_disable_timeout = paru_cfg.get("disable_download_timeout", False)
        self.paru_needed_only = paru_cfg.get("needed_only", False)
        # timeout in seconds for a single paru invocation; 0 or missing means no timeout
        self.paru_timeout = paru_cfg.get("timeout", 0)

        self.in_package_changes = False
        self.progress_fraction = 0.0

        # Ensure sudoers entry so nobody can run pacman without password
        pacman_path = shutil.which("pacman") or "/usr/bin/pacman"
        sudoers_line = f"nobody ALL=(ALL) NOPASSWD: {pacman_path}"
        # Create inside target: simplest through sh -c redirection
        try:
            libcalamares.utils.target_env_process_output(
                [
                    "sh",
                    "-c",
                    "printf %s {} > /etc/sudoers.d/calamares-paru && chmod 440 /etc/sudoers.d/calamares-paru".format(
                        repr(sudoers_line)
                    ),
                ]
            )
        except subprocess.CalledProcessError:
            libcalamares.utils.warning("Failed to create sudoers entry for paru (ignored).")

        # Ensure cache dir exists and is writable by nobody, and ensure nobody is not expired
        try:
            libcalamares.utils.target_env_process_output(
                [
                    "sh",
                    "-c",
                    "mkdir -p /var/cache/paru_cache && chown nobody:nobody /var/cache/paru_cache",
                ]
            )
        except subprocess.CalledProcessError:
            libcalamares.utils.warning("Failed to prepare /var/cache/paru_cache (ignored).")

        try:
            libcalamares.utils.target_env_process_output(
                [
                    "sh",
                    "-c",
                    "chage -E -1 nobody",
                ]
            )
        except subprocess.CalledProcessError:
            libcalamares.utils.warning("Failed to set account expiry for nobody (ignored).")

        def line_cb(line: str):
            if line.startswith(":: "):
                self.in_package_changes = ("package" in line) or ("hooks" in line)
            else:
                if self.in_package_changes and line.endswith("...\n"):
                    global custom_status_message
                    custom_status_message = "paru: " + line.strip()
                    libcalamares.job.setprogress(self.progress_fraction)
            libcalamares.utils.debug(line.strip())

        self.line_cb = line_cb

    def reset_progress(self):
        self.in_package_changes = False
        if total_packages > 0:
            self.progress_fraction = completed_packages * 1.0 / total_packages
        else:
            self.progress_fraction = 0.0

    def _set_build_env(self):
        # Keep paru cache in a writable location in target
        import os

        os.environ["PWD"] = "/var/cache/paru_cache"
        os.environ["XDG_CACHE_HOME"] = "/var/cache/paru_cache"
        os.environ["XDG_DATA_HOME"] = "/var/cache/paru_cache"

    def run_paru(self, command, callback=False):
        """
        Run paru with retries.
        Best-effort: after retries exhausted, still do NOT raise; just log warning.
        """
        self._set_build_env()
        attempts = 0
        last_exc = None

        while attempts <= self.paru_num_retries:
            attempts += 1
            try:
                # If no timeout configured, call directly as before
                if not self.paru_timeout:
                    if callback:
                        libcalamares.utils.target_env_process_output(command, self.line_cb)
                    else:
                        libcalamares.utils.target_env_process_output(command)
                    return True

                # With timeout: run the target call in a thread and wait
                result_container = {"exc": None}

                def target_call():
                    try:
                        if callback:
                            libcalamares.utils.target_env_process_output(command, self.line_cb)
                        else:
                            libcalamares.utils.target_env_process_output(command)
                    except Exception as e:
                        result_container["exc"] = e

                th = threading.Thread(target=target_call)
                th.daemon = True
                th.start()
                th.join(timeout=self.paru_timeout)

                if th.is_alive():
                    # timed out: best-effort kill any paru process running as nobody inside target
                    libcalamares.utils.warning(
                        "paru command timed out after {!s}s (attempting to terminate, ignored).".format(
                            self.paru_timeout
                        )
                    )
                    try:
                        libcalamares.utils.target_env_process_output([
                            "sudo",
                            "-E",
                            "-u",
                            "nobody",
                            "pkill",
                            "-f",
                            "paru",
                        ])
                    except Exception:
                        # ignore any failure to kill
                        pass
                    # emulate a CalledProcessError to go to retry logic / logging
                    last_exc = subprocess.CalledProcessError(returncode=124, cmd=command)
                    if attempts <= self.paru_num_retries:
                        continue
                    break

                # Thread finished: check for exceptions
                if result_container["exc"] is None:
                    return True
                # If it raised a CalledProcessError, propagate to retry handling
                if isinstance(result_container["exc"], subprocess.CalledProcessError):
                    last_exc = result_container["exc"]
                    if attempts <= self.paru_num_retries:
                        continue
                    break
                # Other exceptions: wrap and treat as failure
                last_exc = result_container["exc"]
                if attempts <= self.paru_num_retries:
                    continue
                break
            except subprocess.CalledProcessError as e:
                last_exc = e
                if attempts <= self.paru_num_retries:
                    continue
                break

        # Exhausted retries: log and ignore
        if last_exc is not None:
            libcalamares.utils.warning(
                "paru command failed (ignored): {!s} rc={!s}".format(
                    getattr(last_exc, "cmd", command), getattr(last_exc, "returncode", "?")
                )
            )
            libcalamares.utils.debug("stdout:" + str(getattr(last_exc, "stdout", "")))
            libcalamares.utils.debug("stderr:" + str(getattr(last_exc, "stderr", "")))
        else:
            libcalamares.utils.warning("paru command failed (ignored): {!s}".format(command))

        return False

    def install(self, pkgs, from_local=False):
        command = ["sudo", "-E", "-u", "nobody", "paru"]
        command.append("-U" if from_local else "-S")

        command.append("--noconfirm")
        command.append("--noprogressbar")

        if self.paru_needed_only:
            command.append("--needed")
        if self.paru_disable_timeout:
            command.append("--disable-download-timeout")

        command += pkgs
        self.reset_progress()
        self.run_paru(command, callback=True)

    def remove(self, pkgs):
        self.reset_progress()
        self.run_paru(["sudo", "-E", "-u", "nobody", "paru", "-Rs", "--noconfirm"] + pkgs, callback=True)

    def update_db(self):
        self.run_paru(["sudo", "-E", "-u", "nobody", "paru", "-Sy"], callback=False)

    def update_system(self):
        cmd = ["sudo", "-E", "-u", "nobody", "paru", "-Su", "--noconfirm"]
        if self.paru_disable_timeout:
            cmd.append("--disable-download-timeout")
        self.run_paru(cmd, callback=False)

    # --- packages module operations (we keep structure, but all are best-effort) ---
    def install_package(self, packagedata, from_local=False):
        try:
            if isinstance(packagedata, str):
                self.install([packagedata], from_local=from_local)
            else:
                _run_script(packagedata.get("pre-script", ""))
                self.install([packagedata["package"]], from_local=from_local)
                _run_script(packagedata.get("post-script", ""))
        except Exception as e:
            libcalamares.utils.warning(f"paru: install_package failed (ignored): {e!s}")

    def remove_package(self, packagedata):
        try:
            if isinstance(packagedata, str):
                self.remove([packagedata])
            else:
                _run_script(packagedata.get("pre-script", ""))
                self.remove([packagedata["package"]])
                _run_script(packagedata.get("post-script", ""))
        except Exception as e:
            libcalamares.utils.warning(f"paru: remove_package failed (ignored): {e!s}")

    def operation_install(self, package_list, from_local=False):
        # Best-effort even if "critical": install one-by-one to keep going on failures
        for p in package_list:
            self.install_package(p, from_local=from_local)

    def operation_try_install(self, package_list):
        for p in package_list:
            self.install_package(p)

    def operation_remove(self, package_list):
        for p in package_list:
            self.remove_package(p)

    def operation_try_remove(self, package_list):
        for p in package_list:
            self.remove_package(p)


def run_operations(pkgman: ParuManager, entry: dict):
    global group_packages, completed_packages

    for key in entry.keys():
        package_list = subst_locale(entry[key])
        group_packages = len(package_list)

        if key == "install":
            _change_mode(INSTALL)
            pkgman.operation_install(package_list)
        elif key == "try_install":
            _change_mode(INSTALL)
            pkgman.operation_try_install(package_list)
        elif key == "remove":
            _change_mode(REMOVE)
            pkgman.operation_remove(package_list)
        elif key == "try_remove":
            _change_mode(REMOVE)
            pkgman.operation_try_remove(package_list)
        elif key == "localInstall":
            _change_mode(INSTALL)
            pkgman.operation_install(package_list, from_local=True)
        elif key == "source":
            libcalamares.utils.debug("Package-list from {!s}".format(entry[key]))
        else:
            libcalamares.utils.warning("Unknown package-operation key {!s}".format(key))

        completed_packages += len(package_list)
        if total_packages > 0:
            libcalamares.job.setprogress(completed_packages * 1.0 / total_packages)

    group_packages = 0
    _change_mode(None)


def run():
    """
    Paru-only packages module.
    Never fails the job due to package failures (AUR best-effort).
    """
    global mode_packages, total_packages, completed_packages, group_packages, custom_status_message

    backend = libcalamares.job.configuration.get("backend", "paru")
    if backend != "paru":
        return "Bad backend", f'backend="{backend}" (paru-only module)'

    skip_this = libcalamares.job.configuration.get("skip_if_no_internet", False)
    if skip_this and not libcalamares.globalstorage.value("hasInternet"):
        libcalamares.utils.warning("Paru package installation skipped: no internet")
        return None

    pkgman = ParuManager()

    update_db = libcalamares.job.configuration.get("update_db", False)
    if update_db and libcalamares.globalstorage.value("hasInternet"):
        pkgman.update_db()  # best-effort internally

    update_system = libcalamares.job.configuration.get("update_system", False)
    if update_system and libcalamares.globalstorage.value("hasInternet"):
        pkgman.update_system()  # best-effort internally

    operations = libcalamares.job.configuration.get("operations", [])
    if libcalamares.globalstorage.contains("packageOperations"):
        operations += libcalamares.globalstorage.value("packageOperations")

    # --- FILTER IN paru operations ONLY ---
    filtered_ops = []
    for entry in operations:
        src = str(entry.get("source", "")).lower()
        if "paru" in src:
            filtered_ops.append(entry)
    operations = filtered_ops

    mode_packages = None
    total_packages = 0
    completed_packages = 0
    group_packages = 0
    custom_status_message = None

    for op in operations:
        for packagelist in op.values():
            total_packages += len(subst_locale(packagelist))

    if not total_packages:
        return None

    for entry in operations:
        group_packages = 0
        libcalamares.utils.debug(pretty_name())
        # Never let exceptions abort the job
        try:
            run_operations(pkgman, entry)
        except Exception as e:
            libcalamares.utils.warning(f"paru: operation failed (ignored): {e!s}")

    mode_packages = None
    libcalamares.job.setprogress(1.0)
    return None
