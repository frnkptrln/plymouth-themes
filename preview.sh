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
# After the passphrase (or straight away, without one) the preview sends the
# units of the running system in the order they started at this boot, as
# systemd did then: readback writes them, the other themes ignore them.
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

# the active services, mounts and swaps of this boot, oldest first
boot_units() {
  local units
  units="$(systemctl list-units --type=service,mount,swap --state=active --no-legend --plain 2>/dev/null |
           awk '{print $1}')"
  [ -n "$units" ] || return 0
  # shellcheck disable=SC2086
  systemctl show -p Id -p ActiveEnterTimestampMonotonic $units 2>/dev/null |
    awk 'BEGIN { RS = ""; FS = "\n" }
         { id = ""; t = 0
           for (i = 1; i <= NF; i++) {
             if ($i ~ /^Id=/) id = substr($i, 4)
             else if ($i ~ /^ActiveEnterTimestampMonotonic=/) t = substr($i, 31) + 0
           }
           if (id != "" && t > 0) print t, id }' |
    sort -n | cut -d' ' -f2-
}

send_units() {
  local u
  boot_units | while IFS= read -r u; do
    plymouth update --status="$u" || true
    sleep 0.04
  done
}

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
  send_units || true
  sleep 6
else
  [ "$MODE" = plain ] && { send_units || true; }
  sleep 8
fi
