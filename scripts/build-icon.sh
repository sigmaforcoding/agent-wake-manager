#!/bin/zsh
# Package the PNG master into the standard macOS icon sizes; no app installation.
set -euo pipefail
task_root=${0:A:h:h}
task_source="$task_root/assets/AppIcon.png"
task_output=${1:-"$task_root/assets/AppIcon.icns"}
task_temp=$(/usr/bin/mktemp -d)
trap '/bin/rm -rf "$task_temp"' EXIT
task_iconset="$task_temp/AppIcon.iconset"
/bin/mkdir "$task_iconset"
for task_size in 16 32 128 256 512; do
    /usr/bin/sips -z "$task_size" "$task_size" "$task_source" \
        --out "$task_iconset/icon_${task_size}x${task_size}.png" >/dev/null
    task_retina=$((task_size * 2))
    /usr/bin/sips -z "$task_retina" "$task_retina" "$task_source" \
        --out "$task_iconset/icon_${task_size}x${task_size}@2x.png" >/dev/null
done
/usr/bin/iconutil --convert icns "$task_iconset" --output "$task_output"
print "Built: $task_output"
