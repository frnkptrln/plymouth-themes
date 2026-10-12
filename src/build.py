#!/usr/bin/env python3
"""Rebuild the themes into ../themes/<name>/.

    python3 src/build.py                    every theme
    python3 src/build.py eca fireflies      only these (theme name or module suffix)
    python3 src/build.py --list             names and generator modules

Needs Python 3 and Pillow; the themes that print in Latin Modern Mono also need
that font (Arch: otf-latin-modern, Debian/Ubuntu: fonts-lmodern). The output is
deterministic: the same sources give the same files, byte for byte.
"""
import glob
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(os.path.dirname(HERE), "themes")


def generators():
    mods = {}
    for path in sorted(glob.glob(os.path.join(HERE, "theme_*.py"))):
        suffix = os.path.basename(path)[len("theme_"):-len(".py")]
        mods[suffix] = importlib.import_module("theme_" + suffix)
    return mods


def main(args):
    mods = generators()
    by_name = {m.NAME: m for m in mods.values()}
    if args == ["--list"]:
        for suffix, m in mods.items():
            print("%-20s src/theme_%s.py" % (m.NAME, suffix))
        return 0
    wanted = []
    for a in args or [m.NAME for m in mods.values()]:
        m = by_name.get(a) or mods.get(a)
        if m is None:
            print("unknown theme: %s (try --list)" % a, file=sys.stderr)
            return 1
        wanted.append(m)
    os.makedirs(OUT, exist_ok=True)
    for m in wanted:
        path = m.build(OUT)
        print("built %-20s %4d files" % (m.NAME, len(os.listdir(path))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
