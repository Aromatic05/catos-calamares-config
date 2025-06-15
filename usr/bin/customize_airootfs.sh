#!/usr/bin/env bash

## Script to perform several important tasks before `mkarchcraftiso` create filesystem image.

set -e -u

## -------------------------------------------------------------- ##

## lsb-release
rm /etc/lsb-release
touch /etc/catos-lsb-release
ln -s /etc/catos-lsb-release /etc/lsb-release
cat > "/etc/lsb-release" <<- _EOF_
	DISTRIB_ID="CatOS"

	DISTRIB_RELEASE="rolling"
	DISTRIB_DESCRIPTION="CatOS"

_EOF_

## -------------------------------------------------------------- ##

## -------------------------------------------------------------- ##

## /etc/os-release
rm /etc/os-release
touch catos-os-release
ln -s /etc/catos-os-release /etc/os-release
cat > "/etc/os-release" <<- _EOF_
	NAME="CatOS"
	PRETTY_NAME="CatOS"
	ID=catos
	BUILD_ID=rolling
	ANSI_COLOR="38;2;23;147;209"
	HOME_URL="https://github.com/CatOS-Home/CatOS"
	DOCUMENTATION_URL="https://github.com/CatOS-Home/CatOS"
	SUPPORT_URL="https://github.com/CatOS-Home/CatOS"
	BUG_REPORT_URL="https://github.com/CatOS-Home/CatOS"
	PRIVACY_POLICY_URL="https://github.com/CatOS-Home/CatOS"
	LOGO=catos

_EOF_

## -------------------------------------------------------------- ##

## -------------------------------------------------------------- ##

## /etc/issue
rm /etc/issue
touch /etc/catos-issue
ln -s /etc/catos-issue /etc/issue
cat > "/etc/issue" <<- _EOF_
	CatOS \r (\l)

_EOF_

## -------------------------------------------------------------- ##

## /etc/issue
rm /usr/share/pixmaps/archlinux-logo.png
ln -s /usr/share/pixmaps/logo.png /usr/share/pixmaps/archlinux-logo.png

rm /usr/share/pixmaps/archlinux-logo.svg
ln -s /usr/share/pixmaps/logo.svg /usr/share/pixmaps/archlinux-logo.svg

rm /usr/share/pixmaps/archlinux-logo-text.svg
ln -s /usr/share/pixmaps/logo-text.svg /usr/share/pixmaps/archlinux-logo-text.svg

rm /usr/share/pixmaps/archlinux-logo-text-dark.svg
ln -s /usr/share/pixmaps/logo-text-dark.svg /usr/share/pixmaps/archlinux-logo-text-dark.svg

## -------------------------------------------------------------- ##

## -------------------------------------------------------------- ##

## /etc/motd
touch /etc/catos-motd
ln -s /etc/catos-motd /etc/motd
cat > "/etc/motd" <<- _EOF_
_EOF_

## -------------------------------------------------------------- ##

## -------------------------------------------------------------- ##
## 更换国内源
echo 'Server = https://mirrors.ustc.edu.cn/archlinux/$repo/os/$arch' > /etc/pacman.d/mirrorlist
echo 'Server = https://mirrors.cernet.edu.cn/archlinux/$repo/os/$arch' >> /etc/pacman.d/mirrorlist
echo 'Server = https://mirrors.bfsu.edu.cn/archlinux/$repo/os/$arch' >> /etc/pacman.d/mirrorlist
echo 'Server = https://mirrors.aliyun.com/archlinux/$repo/os/$arch' >> /etc/pacman.d/mirrorlist
echo 'Server = https://mirrors.bfsu.edu.cn/archlinux/$repo/os/$arch' >> /etc/pacman.d/mirrorlist
echo 'Server = https://mirrors.xjtu.edu.cn/archlinux/$repo/os/$arch' >> /etc/pacman.d/mirrorlist
echo 'Server = https://mirrors.shanghaitech.edu.cn/archlinux/$repo/os/$arch' >> /etc/pacman.d/mirrorlist
echo 'Server = https://mirrors.tuna.tsinghua.edu.cn/archlinux/$repo/os/$arch' >> /etc/pacman.d/mirrorlist

##fcitx5
echo "GTK_IM_MODULE=fcitx" >> /etc/environment
echo "QT_IM_MODULE=fcitx" >> /etc/environment
echo "XMODIFIERS=@im=fcitx" >> /etc/environment
echo "SDL_IM_MODULE=fcitx" >> /etc/environment





