"""sandpile: grains fall on a grid, avalanches of every size, a fractal mandala."""
import os
import shutil

from PIL import Image, ImageDraw

import lib

NAME = "sandpile"
GRID = 41                         # cells per side, the pile in the middle
BG = (12, 11, 10)
SAND = [(86, 66, 48), (166, 130, 88), (236, 210, 160)]     # heights 1, 2, 3
TEXT = {"hi": (236, 210, 160, 255), "lo": (122, 108, 92, 255), "err": (240, 120, 84, 255)}

SCRIPT = r'''# =============================================================================
#  SANDPILE — self-organised criticality.
#
#  Grains fall onto the middle of a grid. A cell holding four grains topples
#  and passes one to each neighbour, which may topple in turn (Bak, Tang and
#  Wiesenfeld, 1987). Most grains change nothing, a few start avalanches of
#  every size, and the pile grows into a fractal mandala. The avalanches run
#  in slow motion: forty topplings a frame is what the boot can spare.
#  Every keystroke drops a pinch of grains onto the middle, a wrong
#  passphrase a whole sack. Since the pile is abelian, the order does not
#  matter: the pattern stays symmetric. At power-off the wind takes the
#  sand away.
#
#  Claude, October 2026 — for Frank
# =============================================================================

Window.SetBackgroundTopColor(%(bgr)s, %(bgg)s, %(bgb)s);
Window.SetBackgroundBottomColor(%(bgr)s, %(bgg)s, %(bgb)s);

SW = Window.GetWidth();
SH = Window.GetHeight();
SX = Window.GetX();
SY = Window.GetY();
%(lib)s
%(prompt)s
%(tables)s

MODE = Plymouth.GetMode();
HALT = (MODE == "shutdown" || MODE == "reboot");

# ---- text ---------------------------------------------------------------------
IDS[0] = "hi"; IDS[1] = "lo"; IDS[2] = "err"; IDS.n = 3;
lm_load(IDS, SH / 52);
prompt_bottom(SX + SW / 2, SW * 0.9);
PR.hi = "hi"; PR.lo = "lo"; PR.err = "err";
MARGIN = Math.Int(FADV * 2);

# ---- the grid -----------------------------------------------------------------
G = %(grid)d;
NCELL = G * G;
TOP = SY + Math.Int(FLH * 2.2);
BOT = PR.y0 - FLH;
CSZ = Math.Int((BOT - TOP) * 0.9 / G);
if (CSZ * G > SW * 0.9) CSZ = Math.Int(SW * 0.9 / G);
if (CSZ < 4) CSZ = 4;
OX = SX + Math.Int((SW - G * CSZ) / 2);
OY = TOP + Math.Int((BOT - TOP - G * CSZ) / 2);
for (h = 1; h <= 3; h++) CELLIMG[h] = Image("sand-" + h + ".png").Scale(CSZ - 1, CSZ - 1);
CENTER = Math.Int(G / 2) * G + Math.Int(G / 2);

for (i = 0; i < NCELL; i++) { HT[i] = 0; DF[i] = 0; }
SP.n = 0;                     # cell sprites, made when a cell first holds sand
STK.n = 0;                    # cells that may need to topple
DIRTY.n = 0;                  # cells to redraw at the end of the frame
GRAINS = 0;
TOPPLES = 0;
AVAL = 0;                     # topplings of the running avalanche
BIGGEST = 0;
BUDGET = 40;                  # topplings per frame

fun mark(i) {
    if (!DF[i]) { DF[i] = 1; DIRTY[DIRTY.n] = i; DIRTY.n++; }
}

fun push(i) { STK[STK.n] = i; STK.n++; }

fun add(i, n) {
    HT[i] = HT[i] + n;
    mark(i);
    if (HT[i] >= 4) push(i);
}

# one toppling of the cell on top of the stack (if it still needs one)
fun topple() {
    local.i = 0;
    local.x = 0;
    local.y = 0;
    STK.n--;
    i = STK[STK.n];
    if (HT[i] < 4) return 0;
    HT[i] = HT[i] - 4;
    mark(i);
    if (HT[i] >= 4) push(i);
    x = i %% G;
    y = Math.Int(i / G);
    # grains that go over the edge are lost
    if (x > 0) add(i - 1, 1);
    if (x < G - 1) add(i + 1, 1);
    if (y > 0) add(i - G, 1);
    if (y < G - 1) add(i + G, 1);
    return 1;
}

fun redraw() {
    local.k = 0;
    local.i = 0;
    local.h = 0;
    for (k = 0; k < DIRTY.n; k++) {
        i = DIRTY[k];
        DF[i] = 0;
        h = HT[i];
        if (h > 3) h = 3;
        if (!SP[i]) {
            if (h == 0) continue;
            SP[i] = Sprite(CELLIMG[h]);
            SP[i].SetPosition(OX + (i %% G) * CSZ, OY + Math.Int(i / G) * CSZ, 5);
        } else if (h == 0) {
            SP[i].SetOpacity(0);
            continue;
        } else {
            SP[i].SetImage(CELLIMG[h]);
        }
        SP[i].SetOpacity(1);
    }
    DIRTY.n = 0;
}

fun tick() {
    local.used = 0;
    local.drops = 0;
    while (used < BUDGET) {
        if (STK.n == 0) {
            if (AVAL > BIGGEST) global.BIGGEST = AVAL;
            global.AVAL = 0;
            if (drops >= 2 || HALT) break;
            add(CENTER, 1);
            global.GRAINS++;
            drops++;
            continue;
        }
        if (topple()) {
            used++;
            global.TOPPLES++;
            global.AVAL++;
        }
    }
}

# ---- readout --------------------------------------------------------------------
fun commas(n) {
    local.s = "";
    if (n < 1000) return "" + n;
    s = "" + (n %% 1000);
    while (s.Length() < 3) s = "0" + s;
    return commas(Math.Int(n / 1000)) + "," + s;
}

SHOWN = "";
fun readout() {
    local.s = "sandpile · grains " + commas(GRAINS) + " · topplings " + commas(TOPPLES) +
              " · largest avalanche " + commas(BIGGEST);
    if (s == SHOWN) return;
    global.SHOWN = s;
    global.READ_R = txt_run("lo", s, SX + MARGIN, SY + Math.Int(FLH * 0.8), 50);
}

# ---- passphrase hooks -----------------------------------------------------------------
fun hook_prompt() { global.BUDGET = 40; }
fun hook_key(n) {
    # a pinch of four grains onto the middle: enough to set something off
    add(CENTER, 4);
    global.GRAINS = GRAINS + 4;
}
fun hook_erase(n) { }
fun hook_wrong() {
    # a whole sack onto the middle
    add(CENTER, 240);
    global.GRAINS = GRAINS + 240;
}
fun hook_enter() { global.BUDGET = 70; }
fun hook_question() { }

# ---- power-off: a pile is there already, and the wind takes it -----------------------
fun settle_all() {
    local.i = 0;
    local.q = 0;
    local.x = 0;
    local.y = 0;
    # several grains a toppling here (the result is the same, it is just faster)
    while (STK.n > 0) {
        STK.n--;
        i = STK[STK.n];
        if (HT[i] < 4) continue;
        q = Math.Int(HT[i] / 4);
        HT[i] = HT[i] - 4 * q;
        x = i %% G;
        y = Math.Int(i / G);
        if (x > 0) { HT[i - 1] = HT[i - 1] + q; if (HT[i - 1] >= 4) push(i - 1); }
        if (x < G - 1) { HT[i + 1] = HT[i + 1] + q; if (HT[i + 1] >= 4) push(i + 1); }
        if (y > 0) { HT[i - G] = HT[i - G] + q; if (HT[i - G] >= 4) push(i - G); }
        if (y < G - 1) { HT[i + G] = HT[i + G] + q; if (HT[i + G] >= 4) push(i + G); }
    }
}

fun wind() {
    local.k = 0;
    local.y = 0;
    local.x = 0;
    local.i = 0;
    for (k = 0; k < 5; k++) {
        y = Math.Int(rnd() * G);
        for (x = 0; x < G; x++) {
            i = y * G + x;
            if (HT[i] > 0) { HT[i] = HT[i] - 1; mark(i); break; }
        }
    }
}

if (HALT) {
    HT[CENTER] = 640;
    GRAINS = 640;
    push(CENTER);
    settle_all();
    for (i = 0; i < NCELL; i++) if (HT[i] > 0) mark(i);
    redraw();
    if (MODE == "reboot") NIGHT_R = pr_line("lo", "see you soon.", PR.y1);
    else NIGHT_R = pr_line("lo", "good night.", PR.y1);
}

# ---- main loop --------------------------------------------------------------------------
FRAME = 0;
fun refresh() {
    global.FRAME++;
    if (HALT) { if (FRAME > 30) wind(); }
    else tick();
    redraw();
    if (FRAME %% 10 == 0) readout();
    prompt_tick();
}

readout();
prompt_setup();
Plymouth.SetRefreshFunction(refresh);
'''

PLYMOUTH = """[Plymouth Theme]
Name=Sandpile
Description=The abelian sandpile: avalanches of every size in slow motion, a fractal mandala
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/{name}
ScriptFile=/usr/share/plymouth/themes/{name}/{name}.script
"""


def cell_image(col):
    S = 64
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((2, 2, S - 3, S - 3), radius=10, fill=col + (255,))
    return im


def build(dist):
    out = os.path.join(dist, NAME)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    for h, col in enumerate(SAND, start=1):
        cell_image(col).save(os.path.join(out, "sand-%d.png" % h), optimize=True)
    t = [lib.lm_fonts(out, TEXT, BG + (255,))]
    bg = ["%.6f" % ((c + 0.5) / 255) for c in BG]
    script = SCRIPT % {"lib": lib.lib_script(), "prompt": lib.prompt_script(), "tables": "\n".join(t),
                       "bgr": bg[0], "bgg": bg[1], "bgb": bg[2], "grid": GRID}
    open(os.path.join(out, NAME + ".script"), "w").write(script)
    open(os.path.join(out, NAME + ".plymouth"), "w").write(PLYMOUTH.format(name=NAME))
    return out
