"""busy-beaver: the 5-state champion runs live; it would halt after 47,176,870 steps."""
import os
import shutil

from PIL import Image, ImageDraw

import lib

NAME = "busy-beaver"
BG = (10, 10, 12)
FULL = (236, 232, 220)
HALF = (118, 114, 108)
EMPTY_CELL = (34, 34, 38)
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
#  time, one row every few hundred steps: a pair of cells with two ones is
#  drawn light, a pair with one grey.
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
TAPE[0] = 0;                  # global hashes the functions write into
BS[0] = 0;                    # ones per block of two cells

fun reset() {
    global.TAPE = NULL;
    global.TAPE[0] = 0;
    global.BS = NULL;
    global.BS[0] = 0;
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
    local.b = 0;
    for (k = 0; k < n && s < 5; k++) {
        c = TAPE[p];
        if (!c) c = 0;
        i = s * 2 + c;
        w = WR[i];
        if (w != c) {
            TAPE[p] = w;
            b = Math.Int(p / 2);
            if (!BS[b]) BS[b] = 0;
            BS[b] = BS[b] + w - c;
            global.ONES = ONES + w - c;
        }
        p = p + MV[i];
        s = NX[i];
    }
    global.STEPS = STEPS + k;
    global.POS = p;
    global.ST = s;
    if (p < LO) global.LO = p;
    if (p > HI) global.HI = p;
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

# ---- the space-time diagram: one row every RSTEP steps, written top to bottom -------
DX0 = SX + Math.Int(SW * 0.08);
DX1 = SX + Math.Int(SW * 0.92);
DY0 = WY + CW + Math.Int(FLH * 2.6);
DY1 = PR.y0 - Math.Int(FLH * 1.2);
RH_ = Math.Max(1, Math.Int(SH / 540));          # row height in px
NROWS = Math.Int((DY1 - DY0) / RH_);
LEFT_CELL = OFF - 860;                          # the tape grows to the left: ~860 cells
NCELLS = 900;                                   # after half a minute, ~1050 after a minute
BPX = (DX1 - DX0) / (NCELLS / 2);               # px per block of two cells
BAR1 = Image("one.png");
BAR2 = Image("half.png");
ROW = 0;
RSTEP = 600;
NEXTROW = RSTEP;
RW[0].n = 0;                                    # sprites of each row
WHEAD = Sprite(Image("head.png").Scale(DX1 - DX0, 1));
WHEAD.SetOpacity(0.5);

fun bar(r, n, img, b0, b1) {
    local.x0 = DX0 + Math.Int((b0 - LEFT_CELL / 2) * BPX);
    local.x1 = DX0 + Math.Int((b1 - LEFT_CELL / 2) * BPX);
    if (x1 <= x0) x1 = x0 + 1;
    RW[r].sp[n] = Sprite(img.Scale(x1 - x0, RH_));
    RW[r].sp[n].SetPosition(x0, DY0 + r * RH_, 4);
}

fun write_row() {
    local.r = ROW;
    local.b = 0;
    local.b0 = Math.Int(LO / 2) - 1;
    local.b1 = Math.Int(HI / 2) + 1;
    local.lev = 0;
    local.cur = -1;
    local.start = 0;
    local.n = 0;
    if (b0 < Math.Int(LEFT_CELL / 2)) b0 = Math.Int(LEFT_CELL / 2);
    if (b1 > Math.Int((LEFT_CELL + NCELLS) / 2)) b1 = Math.Int((LEFT_CELL + NCELLS) / 2);
    RW[r] = NULL;
    RW[r].n = 0;
    for (b = b0; b <= b1 + 1; b++) {
        lev = BS[b];
        if (!lev || b > b1) lev = 0;
        if (lev != cur) {
            if (cur == 2) { bar(r, n, BAR1, start, b); n++; }
            else if (cur == 1) { bar(r, n, BAR2, start, b); n++; }
            cur = lev;
            start = b;
        }
    }
    RW[r].n = n;
    global.ROW = (ROW + 1) %% NROWS;
    WHEAD.SetPosition(DX0, DY0 + ROW * RH_, 7);
    # the row just ahead of the write head is cleared, so the sweep is visible
    RW[ROW] = NULL;
    RW[ROW].n = 0;
}

fun clear_rows() {
    local.r = 0;
    for (r = 0; r < NROWS; r++) { RW[r] = NULL; RW[r].n = 0; }
    global.ROW = 0;
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
    clear_rows();
    global.NEXTROW = RSTEP;
}
fun hook_enter() { global.SPEED = 160; }
fun hook_question() { }

# ---- main loop -----------------------------------------------------------------------------
FRAME = 0;
fun refresh() {
    global.FRAME++;
    run(SPEED);
    while (STEPS >= NEXTROW) {
        write_row();
        global.NEXTROW = NEXTROW + RSTEP;
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
    Image.new("RGBA", (8, 8), HALF + (255,)).save(os.path.join(out, "half.png"))
    Image.new("RGBA", (8, 8), EMPTY_CELL + (255,)).save(os.path.join(out, "zero.png"))
    head_image().save(os.path.join(out, "head.png"))
    t = [lib.lm_fonts(out, TEXT, BG + (255,))]
    bg = ["%.6f" % ((c + 0.5) / 255) for c in BG]
    script = SCRIPT % {"lib": lib.lib_script(), "prompt": lib.prompt_script(), "tables": "\n".join(t),
                       "bgr": bg[0], "bgg": bg[1], "bgb": bg[2], "machine": MACHINE}
    open(os.path.join(out, NAME + ".script"), "w").write(script)
    open(os.path.join(out, NAME + ".plymouth"), "w").write(PLYMOUTH.format(name=NAME))
    return out
