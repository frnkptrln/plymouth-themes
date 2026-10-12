# shellcheck shell=bash
# Shared helpers for the bench scripts. Source it, do not run it.
#
# The bench runs plymouthd with its X11 renderer inside Xvfb, so a theme can
# be watched, typed into and timed without rebooting. It needs root, plymouth
# with the x11 renderer (Debian/Ubuntu: plymouth-x11), Xvfb, xdotool,
# ImageMagick and python3; record.sh also needs ffmpeg.
#
# Themes are staged into /run/plymouth/themes, which plymouthd searches before
# /usr/share/plymouth/themes, and selected with plymouth.splash= on the kernel
# command line handed to plymouthd. Nothing under /etc or /usr is changed, and
# the staged copies are removed on exit. Meant for a container, a VM or a
# machine you are not booting at the same time; it refuses to run while
# another plymouthd is up, because the plymouth client would talk to that one.
#
# On Ubuntu 24.04, `plymouth hide-message` never reaches a theme: its patched
# plymouth only remembers a message while no splash is shown, so a message
# stays until the theme times it out. Upstream plymouth, as on Arch, passes
# hide-message on.

set -u
BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$BENCH")"
STAGE=/run/plymouth/themes
PEDRO_ORIG=/usr/share/plymouth/themes/pedro-raccoon
# shellcheck disable=SC2034  # used by the scripts that source this
PROMPT_TEXT="Please enter passphrase for disk Samsung SSD 970 EVO (luks-3f2a9c1e):"

STAGED=()
XVFB_PID=""
PLY_PID=""
PTY_PID=""
PTY=""

bench_usage() {   # the comment block at the top of the calling script
  awk 'NR > 1 && /^# shellcheck/ { exit } NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"
}

bench_cleanup() {
  [ -n "$PLY_PID" ] && { plymouth quit 2>/dev/null; sleep 0.3; kill "$PLY_PID" 2>/dev/null; }
  [ -n "$XVFB_PID" ] && kill "$XVFB_PID" 2>/dev/null
  [ -n "$PTY_PID" ] && kill "$PTY_PID" 2>/dev/null
  local d
  for d in "${STAGED[@]}"; do
    [ -f "$d/.bench" ] && rm -rf "$d"
  done
  wait 2>/dev/null
  return 0
}

bench_init() {   # bench_init [extra commands to require]
  if [ "$(id -u)" -ne 0 ]; then
    echo "The bench runs plymouthd and needs root (sudo)." >&2; exit 2
  fi
  local c missing=()
  for c in plymouthd plymouth Xvfb xdotool import identify python3 "$@"; do
    command -v "$c" >/dev/null 2>&1 || missing+=("$c")
  done
  if ! compgen -G "/usr/lib*/plymouth/renderers/x11.so" >/dev/null &&
     ! compgen -G "/usr/lib*/*/plymouth/renderers/x11.so" >/dev/null; then
    missing+=("plymouth x11 renderer (Debian/Ubuntu: plymouth-x11)")
  fi
  if [ ${#missing[@]} -gt 0 ]; then
    printf 'missing: %s\n' "${missing[@]}" >&2; exit 2
  fi
  if pgrep -x plymouthd >/dev/null; then
    echo "Another plymouthd is running; the bench would talk to it. Stop it first." >&2; exit 2
  fi
  trap bench_cleanup EXIT
  trap 'exit 130' INT TERM
  # plymouthd wants a terminal; a pseudo-terminal held open by holdpty.py will do
  local f
  f="$(mktemp)"
  python3 "$BENCH/holdpty.py" "$f" &
  PTY_PID=$!
  for _ in $(seq 1 50); do [ -s "$f" ] && break; sleep 0.05; done
  PTY="$(cat "$f")"; rm -f "$f"
  [ -n "$PTY" ] || { echo "could not open a pseudo-terminal" >&2; exit 2; }
}

bench_themes() {   # every theme in the repository
  local d
  for d in "$REPO"/themes/*/; do
    d="${d%/}"
    [ -f "$d/$(basename "$d").plymouth" ] && basename "$d"
  done
}

bench_stage() {   # bench_stage NAME: copy themes/NAME to /run/plymouth/themes/NAME
  local n="$1" src="$REPO/themes/$1" dst="$STAGE/$1"
  [ -f "$src/$n.plymouth" ] || { echo "no such theme: $n" >&2; return 1; }
  if [ -e "$dst" ] && [ ! -f "$dst/.bench" ]; then
    echo "$dst exists and was not staged by the bench; leaving it alone" >&2; return 1
  fi
  rm -rf "$dst"
  mkdir -p "$dst"
  cp "$src"/* "$dst"/
  touch "$dst/.bench"
  STAGED+=("$dst")
  sed -i "s#/usr/share/plymouth/themes/$n#$dst#g" "$dst/$n.plymouth"
  if [ "$n" = readback ] && [ -n "${READBACK_NAME:-}" ]; then
    sed -i "s/^MACHINE = \"[^\"]*\";/MACHINE = \"$READBACK_NAME\";/" "$dst/readback.script"
  fi
  if [ "$n" = pedro-raccoon-luks ] && [ ! -f "$dst/animation-1.png" ]; then
    if [ -f "$PEDRO_ORIG/animation-198.png" ]; then
      cp "$PEDRO_ORIG"/animation-*.png "$dst"/
    else
      # the original frames are not in this repository: stand-ins, so the
      # script around them can still be tested
      convert -size 320x320 gradient:'#1c2a3a-#8ab4d8' "$dst/animation-1.png"
      local i
      for i in $(seq 2 198); do cp "$dst/animation-1.png" "$dst/animation-$i.png"; done
    fi
  fi
}

bench_xvfb() {   # bench_xvfb WxH: start an X server and export DISPLAY
  [ -n "$XVFB_PID" ] && { kill "$XVFB_PID" 2>/dev/null; wait "$XVFB_PID" 2>/dev/null; XVFB_PID=""; }
  local n=90
  while [ -e "/tmp/.X11-unix/X$n" ] || [ -e "/tmp/.X$n-lock" ]; do n=$((n + 1)); done
  Xvfb ":$n" -screen 0 "${1}x24" -nolisten tcp >/dev/null 2>&1 &
  XVFB_PID=$!
  export DISPLAY=":$n"
  for _ in $(seq 1 50); do xdotool getdisplaygeometry >/dev/null 2>&1 && return 0; sleep 0.1; done
  echo "Xvfb did not start" >&2; return 1
}

bench_plymouthd() {   # bench_plymouthd THEME LOGFILE [plymouthd options, e.g. --mode=shutdown]
  local t="$1" log
  log="$(realpath -m "$2")"   # plymouthd changes directory: the path must be absolute
  shift 2
  plymouthd --no-daemon --debug --debug-file="$log" "$@" \
    --kernel-command-line="quiet splash plymouth.splash=$t plymouth.splash-delay=0 plymouth.ignore-serial-consoles" \
    --ignore-serial-consoles --tty="$PTY" --no-boot-log >/dev/null 2>&1 &
  PLY_PID=$!
  for _ in $(seq 1 50); do plymouth --ping 2>/dev/null && return 0; sleep 0.1; done
  echo "plymouthd did not come up" >&2; return 1
}

bench_quit() {   # ask plymouthd to quit; returns 1 if it had to be killed
  local rc=0
  plymouth quit 2>/dev/null
  for _ in $(seq 1 50); do kill -0 "$PLY_PID" 2>/dev/null || break; sleep 0.1; done
  if kill -0 "$PLY_PID" 2>/dev/null; then kill -9 "$PLY_PID" 2>/dev/null; rc=1; fi
  wait "$PLY_PID" 2>/dev/null
  PLY_PID=""
  return $rc
}

bench_units() {   # bench_units SECTION [pause]: send one section of units.txt as status updates
  local sec="$1" pause="${2:-0.03}" on=0 line
  while IFS= read -r line; do
    case "$line" in
      "# $sec:"*) on=1 ;;
      "#"*) on=0 ;;
      "") ;;
      *) if [ "$on" = 1 ]; then plymouth update --status="$line"; sleep "$pause"; fi ;;
    esac
  done <"$BENCH/units.txt"
}

bench_focus() {   # keyboard focus to the plymouth window
  local w
  w="$(xdotool search --onlyvisible --class "" 2>/dev/null | head -1)"
  [ -n "$w" ] && xdotool windowfocus --sync "$w" 2>/dev/null
  return 0
}

bench_type_slowly() {   # like a person: one key at a time, uneven pauses
  local s="$1" i
  for ((i = 0; i < ${#s}; i++)); do
    xdotool type --delay 0 "${s:$i:1}"
    sleep "0.$((RANDOM % 2 + 1))$((RANDOM % 9))"
  done
}

bench_shot() {   # bench_shot FILE.png
  import -window root "$1" 2>/dev/null
}
