#!/usr/bin/env bash
# Edge cases, as screenshots: an answer typed the moment the prompt appears,
# a second disk with a very long prompt, and a 95-character passphrase.
#
#   sudo bench/edge.sh THEME OUTDIR [WxH]
#
# e1.png: after the early answer; e2.png: long prompt and passphrase being
# typed; e3.png: after it was sent.
# shellcheck source-path=SCRIPTDIR source=lib.sh
source "$(dirname "$0")/lib.sh"
[ $# -ge 2 ] || { bench_usage; exit 2; }
THEME="$1"; OUT="$2"; GEOM="${3:-1920x1080}"

bench_init
mkdir -p "$OUT"
OUT="$(realpath "$OUT")"
rm -f "$OUT"/e*.png "$OUT"/a*.txt "$OUT/ply.log"
bench_stage "$THEME" || exit 1
bench_xvfb "$GEOM" || exit 1
bench_plymouthd "$THEME" "$OUT/ply.log" || exit 1
plymouth show-splash
sleep 0.3

plymouth ask-for-password --prompt="Please enter passphrase for disk root (luks-1111):" >"$OUT/a1.txt" 2>&1 &
sleep 0.4; bench_focus
xdotool type --delay 30 "early"; xdotool key Return
sleep 2.5; bench_shot "$OUT/e1.png"

LONG="Please enter passphrase for disk WDC WD40EFRX-68N32N0 external backup enclosure USB3 (luks-8c1d2e3f-4a5b-6c7d-8e9f-0a1b2c3d4e5f) on /mnt/archive:"
plymouth ask-for-password --prompt="$LONG" >"$OUT/a2.txt" 2>&1 &
sleep 1.5; bench_focus
xdotool type --delay 5 "$(printf 'x%.0s' $(seq 1 95))"; sleep 0.8
bench_shot "$OUT/e2.png"
xdotool key Return; sleep 5
bench_shot "$OUT/e3.png"

bench_quit
n="$(grep -c 'Parser error' "$OUT/ply.log")"
echo "a1=$(cat "$OUT/a1.txt") a2: $(tr -d '\n' <"$OUT/a2.txt" | wc -c) characters, parser errors: ${n:-0}"
