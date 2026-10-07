#!/usr/bin/env bash
# Desktop + phone screenshots of the offline snapshot with headless Chrome.
set -euo pipefail
cd "$(dirname "$0")"
SNAP="file://$PWD/dist/chelsea-tracker-2026-27.html"
F=(--headless=new --no-sandbox --disable-gpu --hide-scrollbars --virtual-time-budget=5000)
shot(){ timeout 120 nice -n 10 google-chrome "${F[@]}" "${@:3}" --window-size="$2" --screenshot="$PWD/screenshots/$1.png" "$SNAP" 2>/dev/null || echo "WARN $1"; echo "screenshots/$1.png"; }
shot 00-best-desktop-hero 1440,1500 --force-device-scale-factor=1
shot 01-desktop-full 1440,5200 --force-device-scale-factor=1
shot 02-phone-top 390,2400 --force-device-scale-factor=2
shot 03-phone-full 390,11500 --force-device-scale-factor=1
