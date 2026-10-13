"""sandpile: grains fall on a grid, avalanches of every size, a fractal mandala."""
import os
import shutil

from PIL import Image

import lib

NAME = "sandpile"
GRID = 111                        # cells per side, the pile in the middle
CSZ_MIN, CSZ_MAX = 3, 16          # cell sizes the picture of the pile is built in
START = 16384                     # grains in the pile the theme starts from
BG = (12, 11, 10)
SAND = [(74, 44, 22), (168, 100, 40), (232, 184, 108)]     # heights 1, 2, 3
HOT = (255, 251, 240)             # a cell while it topples
BUDGET = 30                       # topplings a frame at most
COST = 15000                      # topplings a frame times squares on the screen
TEXT = {"hi": (236, 210, 160, 255), "lo": (122, 108, 92, 255), "err": (240, 120, 84, 255)}

SCRIPT = r'''# =============================================================================
#  SANDPILE — self-organised criticality.
#
#  Grains fall onto the middle of a grid. A cell holding four grains topples
#  and passes one to each neighbour, which may topple in turn (Bak, Tang and
#  Wiesenfeld, 1987). Most grains change nothing, a few start avalanches of
#  every size.
#  The pile starts from %(start_c)s grains. Dropped one by one they need
#  %(topples_c)s topplings, %(minutes)d minutes at the %(budget)d a frame this theme
#  can spare at most, so the build of this theme did them; since the sandpile is
#  abelian, the order does not matter, and this is exactly the pile the
#  grains would have built. It comes as one picture of the pile at the
#  cell size of this screen; a cell that differs from it gets a square of
#  its own. From there it runs live: the grains keep falling, and every
#  cell lights up while it topples, so an avalanche shows as a wave running
#  through the mandala, in slow motion. Every square costs time on every
#  frame, so the more cells differ from the picture, the fewer topplings a
#  frame: the avalanches slow down as the pile changes.
#  Every keystroke drops a pinch of grains onto the middle, a wrong
#  passphrase a whole sack. At power-off the wind takes the sand away.
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
D = %(diam)d;                 # cells across the pile, and a margin to grow into
CSZ = Math.Int((BOT - TOP) * 0.98 / D);
if (CSZ * D > SW * 0.9) CSZ = Math.Int(SW * 0.9 / D);
if (CSZ < %(csz_min)d) CSZ = %(csz_min)d;
if (CSZ > %(csz_max)d) CSZ = %(csz_max)d;
OX = SX + Math.Int((SW - G * CSZ) / 2);
OY = TOP + Math.Int((BOT - TOP - G * CSZ) / 2);
# what a cell shows: 0..3 its height (0 the background), 4 lit while it topples
for (h = 0; h <= 3; h++) CELLIMG[h] = Image("sand-" + h + ".png").Scale(CSZ, CSZ);
CELLIMG[4] = Image("hot.png").Scale(CSZ, CSZ);
CENTER = Math.Int(G / 2) * G + Math.Int(G / 2);
HAVE_CROP = Image.Crop;
BASEIMG = Image("pile-" + CSZ + ".png");
BASE = Sprite();
BX = OX + %(bx0)d * CSZ;
BY = OY + %(by0)d * CSZ;

HT[0] = 0;                    # heights, filled in row by row while the pile opens
DF[0] = 0;                    # dirty flags
HOTT[0] = 0;                  # frame until which a cell is lit
BH[0] = 0;                    # what the picture shows
DS[0] = 0;                    # what the screen shows now
OV.n = 0;                     # the squares of cells that differ from the picture
OVN = 0;                      # how many there are
DIRTY.n = 0;                  # cells to redraw at the end of the frame
QMAX = NCELL + 1;             # cells due to topple, first in first out: a wave
Q[0] = 0;
QH = 0;
QN = 0;
HOTF = 4;                     # frames a toppling cell stays lit
COOL[0].n = 0;                # cells to put out, by frame (mod 16)
for (i = 0; i < 16; i++) COOL[i].n = 0;
GRAINS = %(start)d;
TOPPLES = %(topples)d;
AVAL = 0;                     # topplings of the running avalanche
BIGGEST = 0;
BUDGET = %(budget)d;                  # topplings per frame
FRAME = 0;

# ---- the pile the build computed, row by row (heights 0..3) ----------------------
%(rows)s
DIG["0"] = 0; DIG["1"] = 1; DIG["2"] = 2; DIG["3"] = 3;
LOADED = 0;                   # rows read into the arrays so far
REVEAL = 0;                   # frames of the opening so far, -1 when it is done

# a few rows a frame, so the first frame does not wait for all of them
fun load_rows(n) {
    local.r = 0;
    local.x = 0;
    local.i = 0;
    local.v = 0;
    for (r = LOADED; r < LOADED + n && r < G; r++) {
        for (x = 0; x < G; x++) {
            i = r * G + x;
            v = 0;
            if (ROWS[r]) v = DIG[ROWS[r].CharAt(x)];
            HT[i] = v; BH[i] = v; DS[i] = v; DF[i] = 0; HOTT[i] = 0;
        }
    }
    global.LOADED = r;
}

fun mark(i) {
    if (!DF[i]) { DF[i] = 1; DIRTY[DIRTY.n] = i; DIRTY.n++; }
}

fun push(i) {
    Q[(QH + QN) %% QMAX] = i;
    global.QN = QN + 1;
}

fun add(i, n) {
    local.was = HT[i];
    HT[i] = was + n;
    mark(i);
    if (was < 4 && HT[i] >= 4) push(i);
}

# one toppling of the cell at the front of the queue
fun topple() {
    local.i = Q[QH];
    local.x = 0;
    local.y = 0;
    local.c = 0;
    global.QH = (QH + 1) %% QMAX;
    global.QN = QN - 1;
    if (HT[i] < 4) return 0;
    HT[i] = HT[i] - 4;
    if (HT[i] >= 4) push(i);
    HOTT[i] = FRAME + HOTF;
    c = (FRAME + HOTF) %% 16;
    COOL[c][COOL[c].n] = i;
    COOL[c].n++;
    mark(i);
    x = i %% G;
    y = Math.Int(i / G);
    # grains that go over the edge are lost
    if (x > 0) add(i - 1, 1);
    if (x < G - 1) add(i + 1, 1);
    if (y > 0) add(i - G, 1);
    if (y < G - 1) add(i + G, 1);
    return 1;
}

fun cool() {
    local.c = FRAME %% 16;
    local.k = 0;
    local.i = 0;
    for (k = 0; k < COOL[c].n; k++) {
        i = COOL[c][k];
        if (HOTT[i] <= FRAME) mark(i);
    }
    COOL[c] = NULL;
    COOL[c].n = 0;
}

fun redraw() {
    local.k = 0;
    local.i = 0;
    local.d = 0;
    for (k = 0; k < DIRTY.n; k++) {
        i = DIRTY[k];
        DF[i] = 0;
        if (HOTT[i] > FRAME) d = 4;
        else {
            d = HT[i];
            if (d > 3) d = 3;
        }
        if (d == DS[i]) continue;
        DS[i] = d;
        if (d == BH[i]) {
            if (OV[i]) global.OVN = OVN - 1;
            OV[i] = NULL;
            continue;
        }
        if (OV[i]) OV[i].SetImage(CELLIMG[d]);
        else {
            OV[i] = Sprite(CELLIMG[d]);
            OV[i].SetPosition(OX + (i %% G) * CSZ, OY + Math.Int(i / G) * CSZ, 5);
            global.OVN = OVN + 1;
        }
    }
    DIRTY.n = 0;
}

# the pile opens from the middle row outwards
fun reveal() {
    local.h = BASEIMG.GetHeight();
    local.half = Math.Int(h / 2);
    local.k = (REVEAL + 1) * 2 * CSZ;
    if (k >= half || !HAVE_CROP) {
        BASE.SetImage(BASEIMG);
        BASE.SetPosition(BX, BY, 4);
        global.REVEAL = -1;
        return;
    }
    BASE.SetImage(BASEIMG.Crop(0, half - k, BASEIMG.GetWidth(), 2 * k));
    BASE.SetPosition(BX, BY + half - k, 4);
    global.REVEAL = REVEAL + 1;
}

fun tick() {
    local.used = 0;
    local.drops = 0;
    local.budget = Math.Int(%(cost)d / (OVN + 200));
    if (budget > BUDGET) budget = BUDGET;
    if (budget < 2) budget = 2;
    while (used < budget) {
        if (QN == 0) {
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
fun hook_prompt() { }
PEND = 0;                     # grains dropped before the pile was read in
fun drop(k) {
    if (LOADED < G) global.PEND = PEND + k;
    else add(CENTER, k);
    global.GRAINS = GRAINS + k;
}
fun hook_key(n) {
    # a pinch of four grains onto the middle
    drop(4);
}
fun hook_erase(n) { }
fun hook_wrong() {
    # a whole sack onto the middle
    drop(120);
}
fun hook_enter() { }
fun hook_question() { }

# ---- power-off: the wind takes the sand, from one side ----------------------------------
fun wind() {
    local.k = 0;
    local.y = 0;
    local.x = 0;
    local.i = 0;
    for (k = 0; k < Math.Int(G / 4); k++) {
        y = Math.Int(rnd() * G);
        for (x = 0; x < G; x++) {
            i = y * G + x;
            if (HT[i] > 0) { HT[i] = HT[i] - 1; mark(i); break; }
        }
    }
}

if (HALT) {
    if (MODE == "reboot") NIGHT_R = pr_line("lo", "see you soon.", PR.y1);
    else NIGHT_R = pr_line("lo", "good night.", PR.y1);
}

# ---- main loop --------------------------------------------------------------------------
fun refresh() {
    global.FRAME++;
    if (LOADED < G) load_rows(6);
    if (REVEAL >= 0) reveal();
    else if (LOADED >= G) {
        if (PEND > 0) { add(CENTER, PEND); global.PEND = 0; }
        if (HALT) { if (FRAME > 50) wind(); }
        else tick();
    }
    cool();
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


def stable_pile(n, g):
    """The stable pile of n grains dropped on the middle of a g x g grid whose
    edge loses grains, and the number of topplings it took. A cell topples
    several times at once here; the sandpile is abelian, so the pile and the
    count are those of dropping the grains one at a time."""
    h = [0] * (g * g)
    c = (g // 2) * g + g // 2
    h[c] = n
    stack = [c]
    topples = 0
    while stack:
        i = stack.pop()
        v = h[i]
        if v < 4:
            continue
        q = v >> 2
        h[i] = v - 4 * q
        topples += q
        x, y = i % g, i // g
        for j, ok in ((i - 1, x > 0), (i + 1, x < g - 1), (i - g, y > 0), (i + g, y < g - 1)):
            if ok:
                h[j] += q
                if h[j] >= 4:
                    stack.append(j)
    return h, topples


def commas(n):
    return "{:,}".format(n)


def build(dist):
    out = os.path.join(dist, NAME)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    for h, col in enumerate([BG] + SAND):
        Image.new("RGBA", (8, 8), col + (255,)).save(os.path.join(out, "sand-%d.png" % h))
    Image.new("RGBA", (8, 8), HOT + (255,)).save(os.path.join(out, "hot.png"))
    heights, topples = stable_pile(START, GRID)
    cols = [i % GRID for i, v in enumerate(heights) if v]
    lines = [i // GRID for i, v in enumerate(heights) if v]
    x0, y0 = min(cols), min(lines)
    w, h = max(cols) - x0 + 1, max(lines) - y0 + 1
    diam = max(w, h) + 8
    # the pile as one picture per cell size, four colours
    small = Image.new("P", (w, h), 0)
    small.putpalette([v for col in [BG] + SAND for v in col])
    small.putdata([heights[(y + y0) * GRID + x + x0] for y in range(h) for x in range(w)])
    for c in range(CSZ_MIN, CSZ_MAX + 1):
        small.resize((w * c, h * c), Image.NEAREST).save(os.path.join(out, "pile-%d.png" % c), optimize=True)
    rows = []
    for r in range(GRID):
        row = heights[r * GRID:(r + 1) * GRID]
        if any(row):
            rows.append('ROWS[%d] = "%s";' % (r, "".join(str(v) for v in row)))
    t = [lib.lm_fonts(out, TEXT, BG + (255,))]
    bg = ["%.6f" % ((c + 0.5) / 255) for c in BG]
    script = SCRIPT % {"lib": lib.lib_script(), "prompt": lib.prompt_script(), "tables": "\n".join(t),
                       "bgr": bg[0], "bgg": bg[1], "bgb": bg[2], "grid": GRID,
                       "start": START, "start_c": commas(START), "topples": topples,
                       "topples_c": commas(topples), "rows": "\n".join(rows), "diam": diam,
                       "minutes": round(topples / (BUDGET * 50) / 60), "budget": BUDGET,
                       "cost": COST, "bx0": x0, "by0": y0,
                       "csz_min": CSZ_MIN, "csz_max": CSZ_MAX}
    open(os.path.join(out, NAME + ".script"), "w").write(script)
    open(os.path.join(out, NAME + ".plymouth"), "w").write(PLYMOUTH.format(name=NAME))
    return out
