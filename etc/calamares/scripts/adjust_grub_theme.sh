#!/bin/bash

# 获取当前分辨率
resolution=$(xrandr | grep '*' | head -n1 | awk '{print $1}')
width=$(echo "$resolution" | cut -d'x' -f1)
height=$(echo "$resolution" | cut -d'x' -f2)

# 判断分辨率类型
if [[ $width -ge 3840 && $height -ge 2160 ]]; then
    echo "当前分辨率：${width}x${height}，属于 4K"
    sed -i "s/resolution='1080p'/resolution='4k'/g" /etc/calamares/scripts/adjust_grub_theme_after.sh
elif [[ $width -ge 2560 && $height -ge 1440 ]]; then
    echo "当前分辨率：${width}x${height}，属于 2K"
    sed -i "s/resolution='1080p'/resolution='2k'/g" /etc/calamares/scripts/adjust_grub_theme_after.sh
elif [[ $width -ge 1920 && $height -ge 1080 ]]; then
    echo "当前分辨率：${width}x${height}，属于 1080p"
else
    echo "当前分辨率：${width}x${height}，不属于常见标准"
fi
