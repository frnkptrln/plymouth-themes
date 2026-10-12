#!/usr/bin/env bash
# Install and activate a Plymouth theme from this repository.
#
#   sudo ./install.sh fireflies              install, activate, rebuild the initramfs
#   sudo ./install.sh eca --no-rebuild       install and activate only
#   sudo ./install.sh readback --name t14    the name readback spells (default: the hostname)
#   sudo ./install.sh --use spinner          switch to another, already installed theme
#   ./install.sh --check                     only check hooks and kernel parameters
#   ./install.sh --list                      themes in this repository
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/themes"
DEST=/usr/share/plymouth/themes
PEDRO_ORIG="$DEST/pedro-raccoon"     # frames of pedro-raccoon-luks come from here

THEMES=()
for d in "$SRC"/*/; do
  [ -d "$d" ] || continue
  n="$(basename "$d")"
  [ -f "$d/$n.plymouth" ] && THEMES+=("$n")
done

say()  { printf '%s\n' "$*"; }
ok()   { printf '  ok  %s\n' "$*"; }
warn() { printf '  !!  %s\n' "$*"; }

check() {
  say "== Check"
  if command -v plymouthd >/dev/null 2>&1; then
    local v
    v="$(pacman -Q plymouth 2>/dev/null | awk '{print $2}' ||
         dpkg-query -W -f '${Version}' plymouth 2>/dev/null ||
         rpm -q --qf '%{VERSION}' plymouth 2>/dev/null || true)"
    ok "plymouth installed${v:+ ($v)}"
  else
    warn "plymouth is missing (Arch: sudo pacman -S plymouth)"
  fi
  say "  current theme: $(plymouth-set-default-theme 2>/dev/null || echo '?')"

  if grep -qw splash /proc/cmdline; then
    ok "kernel parameter 'splash' is set"
  else
    warn "'splash' is missing from the kernel command line (/proc/cmdline); without it Plymouth shows text only"
  fi

  # mkinitcpio: the last HOOKS= wins (mkinitcpio.conf, then mkinitcpio.conf.d/*.conf)
  local hooks="" f h
  for f in /etc/mkinitcpio.conf /etc/mkinitcpio.conf.d/*.conf; do
    [ -f "$f" ] || continue
    h="$(grep -E '^[[:space:]]*HOOKS=' "$f" | tail -1 || true)"
    [ -n "$h" ] && hooks="$h"
  done
  if [ -n "$hooks" ]; then
    say "  mkinitcpio: $hooks"
    local list i=0 p_ply=-1 p_enc=-1 enc=""
    list="$(printf '%s' "$hooks" | sed -E 's/^[^=]*=\(?//; s/\).*//; s/"//g')"
    for h in $list; do
      [ "$h" = plymouth ] && p_ply=$i
      if [ "$h" = encrypt ] || [ "$h" = sd-encrypt ]; then p_enc=$i; enc=$h; fi
      i=$((i + 1))
    done
    if [ $p_ply -lt 0 ]; then
      warn "hook 'plymouth' is missing from HOOKS; without it there is no splash at boot"
    else
      ok "hook 'plymouth' is present"
    fi
    if [ $p_enc -ge 0 ]; then
      if [ $p_ply -ge 0 ] && [ $p_ply -lt $p_enc ]; then
        ok "'plymouth' comes before '$enc': the passphrase prompt goes through the theme"
      else
        warn "'plymouth' must come before '$enc' in HOOKS, or the prompt appears as text"
      fi
    else
      say "  (no encrypt/sd-encrypt in HOOKS: the root disk is not unlocked in the initramfs)"
    fi
  elif command -v dracut >/dev/null 2>&1; then
    say "  dracut found: its plymouth module is normally included automatically"
  fi
}

rebuild_cmd() {   # the command that rebuilds the initramfs here, if there is a known one
  if command -v limine-mkinitcpio >/dev/null 2>&1; then
    echo "limine-mkinitcpio"
  elif command -v mkinitcpio >/dev/null 2>&1 && compgen -G "/etc/mkinitcpio.d/*.preset" >/dev/null; then
    echo "mkinitcpio -P"
  elif command -v update-initramfs >/dev/null 2>&1; then
    echo "update-initramfs -u"
  fi
}

rebuild() {
  local cmd
  cmd="$(rebuild_cmd)"
  if [ -n "$cmd" ]; then
    say ">> $cmd"; $cmd
  elif command -v dracut >/dev/null 2>&1; then
    warn "dracut found: rebuild the initramfs with your usual command"
    warn "(for example dracut-rebuild or kernel-install); this script does not guess."
    return 0
  else
    warn "no known initramfs generator found; rebuild the initramfs yourself"
    return 1
  fi
}

usage() {
  say "usage:  sudo $0 <theme> [--no-rebuild] [--name NAME]  |  sudo $0 --use <installed-theme>  |  $0 --check | --list"
  say "themes: ${THEMES[*]}"
}

case "${1:-}" in
  ""|-h|--help) usage; exit 0 ;;
  --list) printf '%s\n' "${THEMES[@]}"; exit 0 ;;
  --check) check; exit 0 ;;
  --use)
    [ -n "${2:-}" ] || { usage; exit 1; }
    [ "$(id -u)" -eq 0 ] || { say "Run with sudo."; exit 1; }
    [ -f "$DEST/$2/$2.plymouth" ] || { say "Not installed: $2"; exit 1; }
    plymouth-set-default-theme "$2"
    ok "theme set: $2"
    rebuild
    exit 0 ;;
esac

THEME="$1"; shift
NOREBUILD=0
MACHINE_NAME=""
while [ $# -gt 0 ]; do
  case "$1" in
    --no-rebuild) NOREBUILD=1 ;;
    --name)
      [ $# -ge 2 ] || { say "--name needs a value"; exit 1; }
      MACHINE_NAME="$2"; shift ;;
    *) say "Unknown option: $1"; usage; exit 1 ;;
  esac
  shift
done

if [ ! -f "$SRC/$THEME/$THEME.plymouth" ]; then
  say "Unknown theme: $THEME"; usage; exit 1
fi
if [ "$(id -u)" -ne 0 ]; then
  say "Run with sudo."; exit 1
fi

# pedro-raccoon-luks: the animation frames are not in this repository
FRAMES=""
if [ "$THEME" = pedro-raccoon-luks ] && [ ! -f "$SRC/$THEME/animation-1.png" ]; then
  if [ -f "$PEDRO_ORIG/animation-198.png" ]; then
    FRAMES="$PEDRO_ORIG"
  else
    say "pedro-raccoon-luks needs the original theme 'Pedro Raccoon Plymouth'"
    say "(opendesktop.org/p/2148515) installed in $PEDRO_ORIG for its frames."
    exit 1
  fi
fi

say "== Installing $THEME to $DEST/$THEME"
install -d -m 0755 "$DEST/$THEME"
find "$SRC/$THEME" -maxdepth 1 -type f -print0 | while IFS= read -r -d '' f; do
  install -m 0644 "$f" "$DEST/$THEME/"
done
if [ -n "$FRAMES" ]; then
  for i in $(seq 1 198); do install -m 0644 "$FRAMES/animation-$i.png" "$DEST/$THEME/"; done
  ok "198 animation frames taken from $FRAMES"
fi
# leftovers of an older version would otherwise end up in the initramfs too
find "$DEST/$THEME" -maxdepth 1 -type f -print0 | while IFS= read -r -d '' f; do
  b="$(basename "$f")"
  [ -e "$SRC/$THEME/$b" ] && continue
  [ -n "$FRAMES" ] && [ -e "$FRAMES/$b" ] && continue
  rm -f "$f"; say "  removed (old): $b"
done
ok "$(find "$DEST/$THEME" -type f | wc -l) files"

# readback spells this machine's name; the copy in themes/ says "localhost"
if [ "$THEME" = readback ]; then
  if [ -z "$MACHINE_NAME" ]; then
    MACHINE_NAME="$(hostnamectl --static 2>/dev/null || cat /etc/hostname 2>/dev/null || uname -n)"
  fi
  MACHINE_NAME="$(printf '%s\n' "$MACHINE_NAME" | head -n1 | cut -d. -f1 | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9-' | cut -c1-32)"
  [ -n "$MACHINE_NAME" ] || MACHINE_NAME=localhost
  sed -i "s/^MACHINE = \"[^\"]*\";/MACHINE = \"$MACHINE_NAME\";/" "$DEST/$THEME/$THEME.script"
  ok "the name on the screen: $MACHINE_NAME"
fi

PREV="$(plymouth-set-default-theme 2>/dev/null || true)"
plymouth-set-default-theme "$THEME"
ok "theme set (was: ${PREV:-?})"

check

if [ $NOREBUILD -eq 0 ]; then
  say "== Rebuilding the initramfs (the theme has to be in it to show up before the passphrase)"
  rebuild
else
  cmd="$(rebuild_cmd)"
  say "== initramfs not rebuilt (--no-rebuild). Before the next boot: sudo ${cmd:-<rebuild the initramfs>}"
fi

say ""
say "Done. Preview without rebooting:  sudo ./preview.sh $THEME   (from a text console, Ctrl+Alt+F3)"
say "Back to the previous theme:       sudo ./install.sh --use ${PREV:-<name>}"
