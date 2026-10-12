#!/usr/bin/env bash
# Turn a recording into a preview GIF (10 fps, own palette).
#
#   bench/make_gif.sh IN.mp4 OUT.gif [crop w:h:x:y] [width] [start s] [duration s] [colours]
#
# bench/previews.sh calls it with the crop, width and colours of each preview.
set -euo pipefail
[ $# -ge 2 ] || { sed -n '2,6p' "$0"; exit 2; }
IN="$1"; OUT="$2"; CROP="${3:-}"; W="${4:-560}"; SS="${5:-1.5}"; T="${6:-18.6}"; COLORS="${7:-96}"
VF="fps=10"
[ -n "$CROP" ] && VF="$VF,crop=$CROP"
VF="$VF,scale=$W:-2:flags=lanczos"
ffmpeg -loglevel error -y -ss "$SS" -t "$T" -i "$IN" \
  -vf "$VF,split[a][b];[a]palettegen=max_colors=$COLORS:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
  "$OUT"
