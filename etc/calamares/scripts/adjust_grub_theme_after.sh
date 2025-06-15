#!/bin/bash

# 获取当前分辨率
resolution='1080p'
# 仅当分辨率不是1080p时才执行替换
if [[ "$resolution" != "1080p" ]]; then
    sed -i "s/catos-grub-theme-dark-1080p/catos-grub-theme-dark-${resolution}/g" /etc/default/grub
fi

