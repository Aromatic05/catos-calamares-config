#!/usr/bin/env bash

## Script to perform several important tasks before `mkarchcraftiso` create filesystem image.

set -e -u

##grub
echo 'GRUB_THEME="/usr/share/grub/themes/catos-grub-theme-dark-1080p/theme.txt"' >> /etc/default/grub

echo 'GRUB_DISABLE_OS_PROBER=false' >> /etc/default/grub


#plymouth

echo '[Daemon]' >> /etc/plymouth/plymouthd.conf
echo 'Theme=catos' >> /etc/plymouth/plymouthd.conf
