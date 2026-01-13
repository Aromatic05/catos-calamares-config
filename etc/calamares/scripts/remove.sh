#!/bin/bash

_remove_pacman_package() {
  local _pkgname="$1"
  pacman -Rsnc "$_pkgname" --noconfirm || true
}

# remove pkgs installed for VMs
_clean_vm_packages() {

  #remove virtualbox
  if pacman -Qi virtualbox-guest-utils &> /dev/null; then
    systemctl disable vboxservice.service
    _remove_pacman_package virtualbox-guest-utils
  fi

  if pacman -Qi virtualbox-guest-utils-nox &> /dev/null; then
    systemctl disable vboxservice.service
    _remove_pacman_package virtualbox-guest-utils-nox
  fi

  #remove vmware
  if [ -f /etc/xdg/autostart/vmware-user.desktop ]; then
    rm /etc/xdg/autostart/vmware-user.desktop
  fi

  if pacman -Qi open-vm-tools &> /dev/null; then
    systemctl disable vmtoolsd.service
    _remove_pacman_package open-vm-tools
  fi

  if [ -f /etc/systemd/system/multi-user.target.wants/vmtoolsd.service ]; then
    rm /etc/systemd/system/multi-user.target.wants/vmtoolsd.service
  fi

  #remove qemu
  if pacman -Qi qemu-guest-agent &> /dev/null; then
    systemctl disable qemu-guest-agent.service
    _remove_pacman_package qemu-guest-agent
  fi
}

_clean_files() {
local _files_to_remove=(
  /usr/local/bin/choose-mirror
  /usr/local/bin/prepare-live-desktop.sh
  /usr/local/bin/removeun-online
  /usr/local/share/livecd-sound
)

  local xx
  for xx in "${_files_to_remove[@]}"; do rm -rf "$xx" || true; done
}

_clean_packages() {
local _packages_to_remove=(
  gparted
  catos-calamares
  catos-calamares-config
  edk2-shell
  gpart
  arch-install-scripts
  squashfs-tools
  syslinux
  clonezilla
  memtest86+
  memtest86+-efi
  mkinitcpio-archiso
  tcpdump
)

  local _check_nvidia_card="$(chwd --is_nvidia_card | grep -q 'NVIDIA card found!'; echo $?)"
  if [[ "${_check_nvidia_card}" -ne 0 ]]; then
    echo "No NVIDIA card detected. Removing nvidia drivers"
    _packages_to_remove+=(nvidia-open nvidia-utils egl-wayland)
    _files_to_remove+=(/etc/mkinitcpio.conf.d/10-nvidia.conf)
  fi

  local xx
  # @ does one by one to avoid errors in the entire process
  # taken from Erik Dubois script
  for xx in "${_packages_to_remove[@]}"; do pacman -Rsnc "$xx" --noconfirm; done
}

_check_not_running_vm="$(systemd-detect-virt | grep -q 'none'; echo $?)"
if [[ "${_check_not_running_vm}" -eq 0 ]]; then
  _clean_vm_packages
fi

_clean_packages
_clean_files

# vim:set ft=bash sw=2 sts=2 et:
