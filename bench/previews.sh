#!/usr/bin/env bash
# Remake the preview GIFs: each theme through the LUKS boot of record.sh at
# 1920x1080, cut to 18.6 seconds, cropped where the theme does not fill the
# screen, written to previews/<theme>.gif.
#
#   sudo bench/previews.sh [THEME...]
set -euo pipefail
B="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$B")"
declare -A CROP=(
  [oscilloscope]=1000:900:460:100
  [hilbert]=980:1080:470:0
  [sandpile]=1080:1024:420:56
  [pedro-raccoon-luks]=1200:1080:360:0
)
declare -A WIDTH=(
  [oscilloscope]=480 [hilbert]=440 [sandpile]=460 [pedro-raccoon-luks]=480
  [eca]=480 [waterfall]=480
)
declare -A COLOURS=([oscilloscope]=48)

THEMES=("$@")
if [ ${#THEMES[@]} -eq 0 ]; then
  for d in "$REPO"/themes/*/; do THEMES+=("$(basename "$d")"); done
fi
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
for t in "${THEMES[@]}"; do
  "$B/record.sh" "$t" "$TMP/$t" 1920x1080 luks
  "$B/make_gif.sh" "$TMP/$t/rec.mp4" "$REPO/previews/$t.gif" "${CROP[$t]:-}" "${WIDTH[$t]:-560}" \
    1.5 18.6 "${COLOURS[$t]:-96}"
  echo "previews/$t.gif: $(stat -c %s "$REPO/previews/$t.gif") bytes"
done
