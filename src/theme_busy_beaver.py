"""busy-beaver: the 5-state champion runs live; it would halt after 47,176,870 steps."""
import os
import shutil

from PIL import Image, ImageDraw

import lib

NAME = "busy-beaver"
BG = (10, 10, 12)
FULL = (236, 232, 220)
DIAG = (200, 194, 182)            # the ones in the space-time diagram
EMPTY_CELL = (34, 34, 38)
COMB_MAX = 16                     # comb textures for 1..16 px per cell
HEAD = (255, 176, 64)
TEXT = {"hi": (236, 232, 220, 255), "lo": (112, 110, 106, 255), "err": (255, 120, 84, 255),
        "am": (255, 176, 64, 255)}
MACHINE = "1RB1LC_1RC1RB_1RD0LE_1LA1LD_1RZ0LA"

SCRIPT = r'''# =============================================================================
#  BUSY BEAVER — the 5-state champion, running live.
#
#  A Turing machine with five states and two symbols, found by Marxen and
#  Buntrock in 1989: 1RB1LC_1RC1RB_1RD0LE_1LA1LD_1RZ0LA. Started on an empty
#  tape it halts after 47,176,870 steps with 4,098 ones, and since 2024 it
#  is proven that no 5-state machine that halts runs longer. Here it runs a
#  few thousand steps a second, so it will not halt before your login.
#  At the top: the tape around the head and the state. Below: the tape over
#  time, from step 0 down to now, one row every so many steps. The machine
#  lays down long runs of ones and stretches of 100100…, drawn as a comb;
#  the domes are the sweeps in which it fills a stretch up again. When the
#  rows reach the bottom, every second one goes and the rest close up, so
#  the whole run stays on the screen; when the tape outgrows the width, the
#  cells get narrower.
#  It ignores your typing, it is busy. A wrong passphrase sends it back to
#  step 0. At power-off it stops and says how far it got.
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
IDS[0] = "hi"; IDS[1] = "lo"; IDS[2] = "err"; IDS[3] = "am"; IDS.n = 4;
lm_load(IDS, SH / 52);
prompt_bottom(SX + SW / 2, SW * 0.9);
PR.hi = "hi"; PR.lo = "lo"; PR.err = "err";
MARGIN = Math.Int(FADV * 2);

# ---- the machine -------------------------------------------------------------------
# states A..E = 0..4, halt = 5; index state * 2 + symbol
WR[0] = 1; MV[0] = 1;  NX[0] = 1;     # A0 1RB
WR[1] = 1; MV[1] = -1; NX[1] = 2;     # A1 1LC
WR[2] = 1; MV[2] = 1;  NX[2] = 2;     # B0 1RC
WR[3] = 1; MV[3] = 1;  NX[3] = 1;     # B1 1RB
WR[4] = 1; MV[4] = 1;  NX[4] = 3;     # C0 1RD
WR[5] = 0; MV[5] = -1; NX[5] = 4;     # C1 0LE
WR[6] = 1; MV[6] = -1; NX[6] = 0;     # D0 1LA
WR[7] = 1; MV[7] = -1; NX[7] = 3;     # D1 1LD
WR[8] = 1; MV[8] = 1;  NX[8] = 5;     # E0 1RZ  (halt)
WR[9] = 0; MV[9] = -1; NX[9] = 0;     # E1 0LA
LETTER[0] = "A"; LETTER[1] = "B"; LETTER[2] = "C"; LETTER[3] = "D"; LETTER[4] = "E"; LETTER[5] = "H";

OFF = 100000;                 # keeps tape positions positive
TAPE[0] = 0;                  # global hash the functions write into

fun reset() {
    global.TAPE = NULL;
    global.TAPE[0] = 0;
    global.POS = OFF;
    global.ST = 0;
    global.STEPS = 0;
    global.ONES = 0;
    global.LO = OFF;
    global.HI = OFF;
}
reset();

# run n steps; returns early only if the machine halts
fun run(n) {
    local.k = 0;
    local.p = POS;
    local.s = ST;
    local.c = 0;
    local.i = 0;
    local.w = 0;
    local.lo = LO;
    local.hi = HI;
    for (k = 0; k < n && s < 5; k++) {
        c = TAPE[p];
        if (!c) c = 0;
        i = s * 2 + c;
        w = WR[i];
        if (w != c) {
            TAPE[p] = w;
            global.ONES = ONES + w - c;
        }
        p = p + MV[i];
        if (p < lo) lo = p;
        else if (p > hi) hi = p;
        s = NX[i];
    }
    global.STEPS = STEPS + k;
    global.POS = p;
    global.ST = s;
    global.LO = lo;
    global.HI = hi;
}

# ---- tape window ---------------------------------------------------------------------
NWIN = 61;
CW = Math.Int(SW * 0.8 / NWIN);
if (CW > Math.Int(SH / 40)) CW = Math.Int(SH / 40);
if (CW < 6) CW = 6;
WX = SX + Math.Int((SW - NWIN * CW) / 2);
WY = SY + Math.Int(FLH * 3.4);
IMG1 = Image("one.png").Scale(CW - 2, CW - 2);
IMG0 = Image("zero.png").Scale(CW - 2, CW - 2);
for (i = 0; i < NWIN; i++) {
    WIN[i] = Sprite(IMG0);
    WIN[i].SetPosition(WX + i * CW + 1, WY, 5);
    WV[i] = 0;
}
HEADS = Sprite(Image("head.png").Scale(CW, Math.Int(CW / 2)));
HEADS.SetPosition(WX + Math.Int(NWIN / 2) * CW, WY + CW + 2, 6);
SHOWN_ST = -1;

fun draw_window() {
    local.i = 0;
    local.v = 0;
    local.p0 = POS - Math.Int(NWIN / 2);
    for (i = 0; i < NWIN; i++) {
        v = TAPE[p0 + i];
        if (!v) v = 0;
        if (v != WV[i]) {
            if (v) WIN[i].SetImage(IMG1); else WIN[i].SetImage(IMG0);
            WV[i] = v;
        }
    }
    if (ST != SHOWN_ST) {
        global.SHOWN_ST = ST;
        global.STATE_R = txt_run("am", LETTER[ST], WX + Math.Int(NWIN / 2) * CW + Math.Int((CW - FADV) / 2),
                                 WY - FLH - 2, 50);
    }
}

# ---- the space-time diagram -----------------------------------------------------------
DX0 = SX + Math.Int(SW * 0.06);
DX1 = SX + Math.Int(SW * 0.94);
WD = DX1 - DX0;
DY0 = WY + CW + Math.Int(FLH * 2.4);
DY1 = PR.y0 - Math.Int(FLH * 1.0);
RH_ = Math.Int(SH / 360 + 0.5);                 # row height in px
if (RH_ < 2) RH_ = 2;
NROWS = Math.Int((DY1 - DY0) / RH_);
PXC0 = Math.Int(WD / 300);                      # px per cell at the start: ~300 cells wide
if (PXC0 < 1) PXC0 = 1;
if (PXC0 > %(comb_max)d) PXC0 = %(comb_max)d;
RSTEP0 = 100;
IMG_ONE = Image("diag.png");
IMG_DIM = Image("dim.png");                     # a comb, when a pixel holds several cells
HAVE_TILE = Image.Tile;                         # not in Plymouth 22.02.122 and older
for (i = 1; i <= %(comb_max)d; i++) COMB[i] = Image("comb-" + i + ".png");
WHEAD = Sprite(Image("head.png").Scale(WD, 1));
WHEAD.SetOpacity(0.5);
RO[0].n = 0;              # the rows, by id: n segments a[k]..b[k], t[k] 0 run 1 comb, sp[k]
ORD[0] = 0;               # the ids of the rows on the screen, top to bottom

fun diag_clear() {
    global.RO = NULL;
    global.RO[0].n = 0;
    global.NR = 0;
    global.NEXTID = 1;
    global.RSTEP = RSTEP0;
    global.NEXTROW = RSTEP0;
    global.PXC = PXC0;                          # px per cell, or
    global.CPX = 1;                             # cells per px
    global.RIGHT = OFF + 28;                    # the tape hardly grows to the right
    global.L0 = RIGHT - Math.Int(WD * CPX / PXC);
    WHEAD.SetPosition(DX0, DY0, 7);
}
diag_clear();

fun cx(c) {
    return DX0 + Math.Int((c - L0) * PXC / CPX);
}

fun draw_row(id, r) {
    local.k = 0;
    local.x0 = 0;
    local.x1 = 0;
    local.img = NULL;
    local.y = DY0 + r * RH_;
    for (k = 0; k < RO[id].n; k++) {
        x0 = cx(RO[id].a[k]);
        x1 = cx(RO[id].b[k]);
        if (x1 <= x0) x1 = x0 + 1;
        if (RO[id].t[k] == 0) img = IMG_ONE.Scale(x1 - x0, RH_);
        else if (CPX == 1 && HAVE_TILE) img = COMB[PXC].Tile(x1 - x0, RH_);
        else img = IMG_DIM.Scale(x1 - x0, RH_);
        RO[id].sp[k] = Sprite(img);
        RO[id].sp[k].SetPosition(x0, y, 4);
    }
}

# narrower cells once the tape reaches the left edge (or the right one)
fun fit_width() {
    local.r = 0;
    local.changed = 0;
    if (HI + 4 > RIGHT) {
        global.RIGHT = HI + 28;
        global.L0 = RIGHT - Math.Int(WD * CPX / PXC);
        changed = 1;
    }
    while (LO < L0 + 4) {
        if (PXC > 1) global.PXC = PXC - 1;
        else global.CPX = CPX + 1;
        global.L0 = RIGHT - Math.Int(WD * CPX / PXC);
        changed = 1;
    }
    if (!changed) return;
    for (r = 0; r < NR; r++) {
        RO[ORD[r]].sp = NULL;
        draw_row(ORD[r], r);
    }
}

# the rows have reached the bottom: every second one goes, the rest close up
fun compress() {
    local.r = 0;
    local.k = 0;
    local.n2 = 0;
    local.id = 0;
    for (r = 0; r < NR; r++) {
        id = ORD[r];
        if (r %% 2) {
            RO[id] = NULL;
            continue;
        }
        for (k = 0; k < RO[id].n; k++) RO[id].sp[k].SetY(DY0 + n2 * RH_);
        ORD[n2] = id;
        n2++;
    }
    global.NR = n2;
    global.RSTEP = RSTEP * 2;
}

# one row: the whole tape, as runs of ones and combs of 100100…
fun write_row() {
    local.id = NEXTID;
    local.i = LO;
    local.j = 0;
    local.n = 0;
    global.NEXTID = NEXTID + 1;
    fit_width();
    while (i <= HI) {
        if (!TAPE[i]) {
            i++;
        } else if (TAPE[i + 1]) {
            j = i + 1;
            while (TAPE[j + 1]) j++;
            RO[id].a[n] = i; RO[id].b[n] = j + 1; RO[id].t[n] = 0; n++;
            i = j + 1;
        } else if (!TAPE[i + 2] && TAPE[i + 3]) {
            j = i;
            while (!TAPE[j + 1] && !TAPE[j + 2] && TAPE[j + 3]) j = j + 3;
            RO[id].a[n] = i; RO[id].b[n] = j + 1; RO[id].t[n] = 1; n++;
            i = j + 1;
        } else {
            RO[id].a[n] = i; RO[id].b[n] = i + 1; RO[id].t[n] = 0; n++;
            i++;
        }
    }
    RO[id].n = n;
    ORD[NR] = id;
    draw_row(id, NR);
    global.NR = NR + 1;
    if (NR >= NROWS) compress();
    WHEAD.SetPosition(DX0, DY0 + NR * RH_, 7);
}

# ---- readout -------------------------------------------------------------------------
fun commas(n) {
    local.s = "";
    if (n < 1000) return "" + n;
    s = "" + (n %% 1000);
    while (s.Length() < 3) s = "0" + s;
    return commas(Math.Int(n / 1000)) + "," + s;
}

TITLE_R = txt_run("lo", "busy beaver · 5 states · %(machine)s", SX + MARGIN, SY + Math.Int(FLH * 0.8), 50);
SHOWN = "";
fun readout() {
    local.s = "step " + commas(STEPS) + " of 47,176,870 · ones " + commas(ONES);
    local.x = SX + Math.Int((SW - txt_len(s) * FADV) / 2);
    if (s == SHOWN) return;
    global.SHOWN = s;
    global.COUNT_R = txt_run("hi", s, x, WY + CW + Math.Int(FLH * 0.9), 50);
    if (HALT) {
        s = "stopped " + commas(47176870 - STEPS) + " steps before its halt.";
        global.NIGHT_R = pr_line("lo", s, PR.y1);
    }
}

# ---- passphrase hooks --------------------------------------------------------------------
SPEED = 120;                  # steps per frame
fun hook_prompt() { }
fun hook_key(n) { }           # it is busy
fun hook_erase(n) { }
fun hook_wrong() {
    # back to step 0
    reset();
    diag_clear();
}
fun hook_enter() { global.SPEED = 160; }
fun hook_question() { }

# ---- main loop -----------------------------------------------------------------------------
FRAME = 0;
fun refresh() {
    local.left = SPEED;
    local.n = 0;
    global.FRAME++;
    # run up to each row's step, so every row shows the tape at its own step
    while (left > 0 && ST < 5) {
        n = NEXTROW - STEPS;
        if (n > left) n = left;
        run(n);
        left = left - n;
        if (STEPS >= NEXTROW) {
            write_row();
            global.NEXTROW = NEXTROW + RSTEP;
        }
    }
    draw_window();
    if (FRAME %% 5 == 0) readout();
    prompt_tick();
}

draw_window();
readout();
prompt_setup();
Plymouth.SetRefreshFunction(refresh);
'''

PLYMOUTH = """[Plymouth Theme]
Name=Busy Beaver
Description=The 5-state busy beaver champion runs live; it would halt after 47,176,870 steps
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/{name}
ScriptFile=/usr/share/plymouth/themes/{name}/{name}.script
"""


def head_image():
    im = Image.new("RGBA", (16, 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(8, 0), (15, 7), (1, 7)], fill=HEAD + (255,))
    return im


def build(dist):
    out = os.path.join(dist, NAME)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    Image.new("RGBA", (8, 8), FULL + (255,)).save(os.path.join(out, "one.png"))
    Image.new("RGBA", (8, 8), EMPTY_CELL + (255,)).save(os.path.join(out, "zero.png"))
    Image.new("RGBA", (8, 8), DIAG + (255,)).save(os.path.join(out, "diag.png"))
    # a comb below one pixel per cell: a third of the cells are ones
    dim = tuple((d + 2 * b) // 3 for d, b in zip(DIAG, BG))
    Image.new("RGBA", (8, 8), dim + (255,)).save(os.path.join(out, "dim.png"))
    # 100 at c px per cell, tiled along a comb
    for c in range(1, COMB_MAX + 1):
        im = Image.new("RGBA", (3 * c, 1), (0, 0, 0, 0))
        im.paste(DIAG + (255,), (0, 0, c, 1))
        im.save(os.path.join(out, "comb-%d.png" % c))
    head_image().save(os.path.join(out, "head.png"))
    t = [lib.lm_fonts(out, TEXT, BG + (255,))]
    bg = ["%.6f" % ((c + 0.5) / 255) for c in BG]
    script = SCRIPT % {"lib": lib.lib_script(), "prompt": lib.prompt_script(), "tables": "\n".join(t),
                       "bgr": bg[0], "bgg": bg[1], "bgb": bg[2], "machine": MACHINE,
                       "comb_max": COMB_MAX}
    open(os.path.join(out, NAME + ".script"), "w").write(script)
    open(os.path.join(out, NAME + ".plymouth"), "w").write(PLYMOUTH.format(name=NAME))
    return out
