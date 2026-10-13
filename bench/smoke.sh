#!/usr/bin/env bash
# Smoke test: each theme through a boot with an encrypted disk (message,
# wrong passphrase, retry, question) and through a power-off, inside Xvfb.
# A run fails on a parser error in the script, on a plymouthd that dies or
# does not quit, on a wrong answer, and on a screen with (almost) nothing on it.
#
#   sudo bench/smoke.sh                          all themes, 1920x1080, boot and power-off
#   sudo bench/smoke.sh -g 1366x768 eca hilbert  only these, at another size
#   sudo bench/smoke.sh -m reboot -k shots       other modes; keep the screenshots in ./shots
#
# Modes: luks (the boot above), plain (boot without a prompt), shutdown, reboot.
# shellcheck source-path=SCRIPTDIR source=lib.sh
source "$(dirname "$0")/lib.sh"

GEOMS=()
MODES=()
KEEP=""
while getopts "g:m:k:" o; do
  case "$o" in
    g) GEOMS+=("$OPTARG") ;;
    m) MODES+=("$OPTARG") ;;
    k) KEEP="$OPTARG" ;;
    *) bench_usage; exit 2 ;;
  esac
done
shift $((OPTIND - 1))
[ ${#GEOMS[@]} -eq 0 ] && GEOMS=(1920x1080)
[ ${#MODES[@]} -eq 0 ] && MODES=(luks shutdown)
THEMES=("$@")
[ ${#THEMES[@]} -eq 0 ] && mapfile -t THEMES < <(bench_themes)

bench_init
WORK="${KEEP:-$(mktemp -d)}"
mkdir -p "$WORK"
WORK="$(realpath "$WORK")"

FAILS=0
RUNS=0
REASONS=""
fail() { REASONS="$REASONS $*;"; }

# a screen that shows only a background has a handful of colours at most
check_shot() {
  local f="$1" k
  [ -f "$f" ] || { fail "no screenshot $(basename "$f")"; return; }
  k="$(identify -format '%k' "$f" 2>/dev/null || echo 0)"
  [ "$k" -ge 8 ] || fail "$(basename "$f" .png) nearly empty ($k colours)"
}

ask() {   # ask password|question OUTFILE TEXT
  if [ "$1" = password ]; then
    plymouth ask-for-password --prompt="$3" >"$2" 2>&1 &
  else
    plymouth ask-question --prompt="$3" >"$2" 2>&1 &
  fi
}

answer_is() {   # answer_is FILE EXPECTED
  local got
  got="$(cat "$1" 2>/dev/null)"
  [ "$got" = "$2" ] || fail "answer '$got' instead of '$2'"
}

run_luks() {   # run_luks DIR THEME
  local d="$1"
  bench_plymouthd "$2" "$d/ply.log" || { fail "plymouthd did not start"; return; }
  plymouth show-splash
  bench_units initrd 0.02
  sleep 1.3
  bench_shot "$d/1-boot.png"
  plymouth display-message --text="Starting systemd-cryptsetup@root.service"
  sleep 0.5
  plymouth hide-message --text="Starting systemd-cryptsetup@root.service"
  ask password "$d/a1.txt" "$PROMPT_TEXT"
  sleep 0.8; bench_focus
  xdotool type --delay 60 "wrong"; sleep 0.3
  bench_shot "$d/2-prompt.png"
  xdotool key Return; sleep 1.2
  ask password "$d/a2.txt" "$PROMPT_TEXT"   # the same prompt again: the theme says "wrong"
  sleep 0.8; bench_focus
  xdotool type --delay 60 "correct horzz"; sleep 0.2
  xdotool key BackSpace; sleep 0.1; xdotool key BackSpace
  xdotool type --delay 60 "se"; sleep 0.4
  bench_shot "$d/3-retry.png"
  xdotool key Return; sleep 0.5
  bench_units unlock 0.02
  bench_units system 0.01 &
  local feeder=$!
  sleep 0.5
  ask question "$d/q.txt" "Continue booting? [y/N]"
  sleep 0.6; bench_focus
  xdotool type --delay 60 "y"; xdotool key Return
  wait "$feeder"; sleep 1.5
  bench_shot "$d/4-late.png"
  plymouth --ping 2>/dev/null || fail "plymouthd died"
  bench_quit || fail "plymouthd did not quit"
  answer_is "$d/a1.txt" "wrong"
  answer_is "$d/a2.txt" "correct horse"
  answer_is "$d/q.txt" "y"
  local f
  for f in 1-boot 2-prompt 3-retry 4-late; do check_shot "$d/$f.png"; done
}

run_simple() {   # run_simple DIR THEME MODE
  local d="$1" args=()
  [ "$3" = shutdown ] && args=(--mode=shutdown)
  [ "$3" = reboot ] && args=(--mode=reboot)
  bench_plymouthd "$2" "$d/ply.log" "${args[@]}" || { fail "plymouthd did not start"; return; }
  plymouth show-splash
  if [ "$3" = plain ]; then bench_units initrd 0.02; bench_units unlock 0.02; fi
  sleep 1.0; bench_shot "$d/1-early.png"
  [ "$3" = plain ] && bench_units system 0.01
  sleep 2.5; bench_shot "$d/2-later.png"
  plymouth --ping 2>/dev/null || fail "plymouthd died"
  bench_quit || fail "plymouthd did not quit"
  check_shot "$d/1-early.png"
  check_shot "$d/2-later.png"
}

for t in "${THEMES[@]}"; do
  bench_stage "$t" || { FAILS=$((FAILS + 1)); continue; }
  for g in "${GEOMS[@]}"; do
    bench_xvfb "$g" || exit 2
    for m in "${MODES[@]}"; do
      d="$WORK/$t/$g-$m"
      rm -rf "$d"; mkdir -p "$d"
      REASONS=""
      case "$m" in
        luks) run_luks "$d" "$t" ;;
        plain|shutdown|reboot) run_simple "$d" "$t" "$m" ;;
        *) echo "unknown mode: $m" >&2; exit 2 ;;
      esac
      n="$(grep -c 'Parser error' "$d/ply.log" 2>/dev/null)"
      [ "${n:-0}" -eq 0 ] || fail "$n parser errors: $(grep -m1 'Parser error' "$d/ply.log")"
      RUNS=$((RUNS + 1))
      if [ -z "$REASONS" ]; then
        printf 'ok    %-20s %-10s %s\n' "$t" "$g" "$m"
      else
        FAILS=$((FAILS + 1))
        printf 'FAIL  %-20s %-10s %s:%s\n' "$t" "$g" "$m" "$REASONS"
      fi
    done
  done
done

echo "$RUNS runs, $FAILS failed${KEEP:+; screenshots and logs in $WORK}"
[ -z "$KEEP" ] && rm -rf "$WORK"
[ "$FAILS" -eq 0 ]
