#!/usr/bin/env bash
# CPU share of plymouthd while a theme runs a plain boot.
#
#   sudo bench/cpu.sh THEME [WxH] [warm-up seconds] [measured seconds]
#
# Xvfb's own share is printed too: it stands in for the copy to the screen
# that a real display does in the kernel.
# shellcheck source-path=SCRIPTDIR source=lib.sh
source "$(dirname "$0")/lib.sh"
[ $# -ge 1 ] || { bench_usage; exit 2; }
THEME="$1"; GEOM="${2:-1920x1080}"; WARM="${3:-8}"; MEAS="${4:-10}"

bench_init
bench_stage "$THEME" || exit 1
bench_xvfb "$GEOM" || exit 1
LOG="$(mktemp)"
bench_plymouthd "$THEME" "$LOG" || exit 1
plymouth show-splash
sleep "$WARM"
ticks() { awk '{print $14 + $15}' "/proc/$1/stat"; }
t0="$(ticks "$PLY_PID")"; x0="$(ticks "$XVFB_PID")"
sleep "$MEAS"
t1="$(ticks "$PLY_PID")"; x1="$(ticks "$XVFB_PID")"
HZ="$(getconf CLK_TCK)"
echo "$THEME $GEOM: plymouthd $(( (t1 - t0) * 100 / HZ / MEAS ))% cpu, Xvfb $(( (x1 - x0) * 100 / HZ / MEAS ))%"
bench_quit
rm -f "$LOG"
