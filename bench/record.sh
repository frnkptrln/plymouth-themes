#!/usr/bin/env bash
# Record a theme as video while driving it like a boot.
#
#   sudo bench/record.sh THEME OUTDIR [WxH] [mode]
#
# Modes: luks (default: prompt, typing, a wrong passphrase, the retry with a
# correction, unlock), plain (a boot without a prompt), shutdown, reboot.
# Writes OUTDIR/rec.mp4 and OUTDIR/ply.log; bench/make_gif.sh turns the video
# into a preview.
# shellcheck source-path=SCRIPTDIR source=lib.sh
source "$(dirname "$0")/lib.sh"
[ $# -ge 2 ] || { bench_usage; exit 2; }
THEME="$1"; OUT="$2"; GEOM="${3:-1920x1080}"; MODE="${4:-luks}"

bench_init ffmpeg
mkdir -p "$OUT"
OUT="$(realpath "$OUT")"
rm -f "$OUT/rec.mp4" "$OUT/ply.log" "$OUT"/answer*.txt
bench_stage "$THEME" || exit 1
bench_xvfb "$GEOM" || exit 1

ffmpeg -loglevel error -y -f x11grab -draw_mouse 0 -video_size "$GEOM" -framerate 25 -i "$DISPLAY" \
  -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "$OUT/rec.mp4" &
FF=$!
sleep 0.5

ARGS=()
[ "$MODE" = shutdown ] && ARGS=(--mode=shutdown)
[ "$MODE" = reboot ] && ARGS=(--mode=reboot)
bench_plymouthd "$THEME" "$OUT/ply.log" "${ARGS[@]}" || exit 1
plymouth show-splash

case "$MODE" in
  luks)
    sleep 1.2
    plymouth ask-for-password --prompt="$PROMPT_TEXT" >"$OUT/answer1.txt" 2>&1 &
    sleep 2.2; bench_focus
    bench_type_slowly "geheim"; sleep 0.4; xdotool key Return
    sleep 2.0
    plymouth ask-for-password --prompt="$PROMPT_TEXT" >"$OUT/answer2.txt" 2>&1 &
    sleep 1.4; bench_focus
    bench_type_slowly "korrekt-pferd"; sleep 0.2
    xdotool key BackSpace; sleep 0.3; xdotool key BackSpace; sleep 0.3
    bench_type_slowly "rd"; sleep 0.5; xdotool key Return
    sleep 6
    ;;
  plain) sleep 9 ;;
  shutdown|reboot) sleep 5 ;;
  *) echo "unknown mode: $MODE" >&2; exit 2 ;;
esac

bench_quit
sleep 0.5
kill "$FF" 2>/dev/null; wait "$FF" 2>/dev/null
[ "$MODE" = luks ] && echo "answers: $(cat "$OUT/answer1.txt") / $(cat "$OUT/answer2.txt")"
n="$(grep -c 'Parser error' "$OUT/ply.log")"
echo "parser errors: ${n:-0}"
ls -la "$OUT/rec.mp4"
