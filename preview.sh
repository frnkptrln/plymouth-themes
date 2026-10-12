#!/usr/bin/env bash
# Preview an installed theme without rebooting.
# Run it from a text console (Ctrl+Alt+F3, log in), not from a terminal
# window: Plymouth needs the display for itself.
#
#   sudo ./preview.sh fireflies              boot with passphrase prompt: first try counts as wrong
#   sudo ./preview.sh eca plain              boot without a prompt
#   sudo ./preview.sh trisolaris shutdown    power-off (or: reboot)
#
# Typed passphrases are discarded. Ctrl+Alt+F1/F2 takes you back afterwards.
set -euo pipefail

THEME="${1:-}"
MODE="${2:-luks}"
if [ -z "$THEME" ]; then
  echo "usage: sudo $0 <theme> [luks|plain|shutdown|reboot]"; exit 1
fi
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }
if [ ! -f "/usr/share/plymouth/themes/$THEME/$THEME.plymouth" ]; then
  echo "Install it first:  sudo ./install.sh $THEME --no-rebuild"; exit 1
fi
TTY="$(tty 2>/dev/null || true)"
if [[ "$TTY" != /dev/tty[0-9]* ]] && [ "${FORCE:-0}" != 1 ]; then
  echo "Start this from a text console (Ctrl+Alt+F3), not from a terminal window."
  echo "(FORCE=1 tries anyway.)"
  exit 1
fi
if pgrep -x plymouthd >/dev/null; then
  echo "plymouthd is already running."; exit 1
fi

PREV="$(plymouth-set-default-theme)"
cleanup() {
  plymouth quit 2>/dev/null || true
  plymouth-set-default-theme "$PREV"
}
trap cleanup EXIT

# only the configuration changes; the initramfs stays as it is
plymouth-set-default-theme "$THEME"

ARGS=()
case "$MODE" in
  shutdown) ARGS+=(--mode=shutdown) ;;
  reboot)   ARGS+=(--mode=reboot) ;;
esac
[[ "$TTY" == /dev/tty[0-9]* ]] && ARGS+=(--tty="$TTY")

plymouthd "${ARGS[@]}"
plymouth show-splash
sleep 2

if [ "$MODE" = luks ]; then
  P="Please enter passphrase for disk preview (luks-0000):"
  plymouth ask-for-password --prompt="$P" >/dev/null || true   # first try: treated as wrong
  sleep 1.5
  plymouth ask-for-password --prompt="$P" >/dev/null || true   # second try
  sleep 9
else
  sleep 10
fi
