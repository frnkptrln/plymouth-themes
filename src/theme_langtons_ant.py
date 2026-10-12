"""langtons-ant: one ant, two rules, ten thousand steps of chaos, then a highway."""
import os
import shutil

from PIL import Image

import lib

NAME = "langtons-ant"
BG = (16, 16, 18)
CELL = (232, 228, 216)
ANT = (214, 52, 40)
TEXT = {"hi": (232, 228, 216, 255), "lo": (118, 116, 112, 255), "err": (226, 78, 60, 255)}

SCRIPT = r'''# =============================================================================
#  LANGTON'S ANT — one ant, two rules.
#
#  On a light cell the ant turns right, on a dark one left; it flips the cell
#  and steps forward. From an empty grid that gives about ten thousand steps
#  of chaos, and then, without any change in the rules, the ant starts to
#  build a "highway": the same 104 steps over and over, two cells diagonally
#  each time. The grid wraps around at the edges, so sooner or later the
#  highway runs into the old pattern and the chaos starts again.
#  Typing flips cells in front of the ant, a wrong passphrase scrambles a
#  block around it, Enter lets it run faster. The rules are reversible: at
#  power-off the ant walks its path backwards until the grid is empty.
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

# ---- the grid: a torus of cells above the text ---------------------------------
TOP = SY + Math.Int(FLH * 2.2);
BOT = PR.y0 - FLH;
CS = Math.Int((BOT - TOP) / 118);          # cell size in px
if (CS < 3) CS = 3;
GW = Math.Int(SW / CS);
GH = Math.Int((BOT - TOP) / CS);
OX = SX + Math.Int((SW - GW * CS) / 2);
OY = TOP + Math.Int((BOT - TOP - GH * CS) / 2);
GAP = 1;
if (CS < 5) GAP = 0;
CELLIMG = Image("cell.png").Scale(CS - GAP, CS - GAP);
ANTIMG = Image("ant.png").Scale(CS - GAP, CS - GAP);

G[0] = 0;                     # cell states, index y * GW + x (missing = empty)
SP.n = 0;                     # sprites of cells that have been flipped at least once

# directions: 0 up, 1 right, 2 down, 3 left
DX[0] = 0; DX[1] = 1; DX[2] = 0; DX[3] = -1;
DY[0] = -1; DY[1] = 0; DY[2] = 1; DY[3] = 0;
AX = Math.Int(GW / 2);
AY = Math.Int(GH / 2);
AD = 0;
STEP = 0;
SPEED = 20;                   # steps per frame

ANTS = Sprite(ANTIMG);

fun show(i, on) {
    if (!SP[i]) {
        if (!on) return;
        SP[i] = Sprite(CELLIMG);
        SP[i].SetPosition(OX + (i %% GW) * CS, OY + Math.Int(i / GW) * CS, 5);
    }
    SP[i].SetOpacity(on);
}

fun place_ant() {
    ANTS.SetPosition(OX + AX * CS, OY + AY * CS, 10);
}

# one step forward; draw = 0 only updates the grid (used before power-off)
fun step(draw) {
    local.i = AY * GW + AX;
    local.c = 0;
    if (G[i]) { global.AD = (AD + 3) %% 4; G[i] = 0; c = 0; }
    else { global.AD = (AD + 1) %% 4; G[i] = 1; c = 1; }
    if (draw) show(i, c);
    global.AX = (AX + DX[AD] + GW) %% GW;
    global.AY = (AY + DY[AD] + GH) %% GH;
    global.STEP++;
}

# one step backwards: the rules run in reverse
fun unstep() {
    local.i = 0;
    local.c = 0;
    global.AX = (AX - DX[AD] + GW) %% GW;
    global.AY = (AY - DY[AD] + GH) %% GH;
    i = AY * GW + AX;
    c = 1 - G[i];             # the colour before the ant flipped it
    G[i] = c;
    show(i, c);
    if (c) global.AD = (AD + 1) %% 4;
    else global.AD = (AD + 3) %% 4;
    global.STEP--;
}

fun flip(x, y) {
    local.i = ((y + GH) %% GH) * GW + ((x + GW) %% GW);
    local.v = 1;
    if (G[i]) v = 0;          # (a cell never touched is empty)
    G[i] = v;
    show(i, v);
}

# ---- highway detection: the same displacement every 104 steps --------------------
HX = AX;
HY = AY;
HIGH = 0;
HCOUNT = 0;
fun watch() {
    local.dx = 0;
    local.dy = 0;
    if (STEP %% 104 != 0) return;
    dx = AX - HX;
    dy = AY - HY;
    if (dx > GW / 2) dx = dx - GW;
    if (dx < 0 - GW / 2) dx = dx + GW;
    if (dy > GH / 2) dy = dy - GH;
    if (dy < 0 - GH / 2) dy = dy + GH;
    if (Math.Abs(dx) == 2 && Math.Abs(dy) == 2) global.HCOUNT++;
    else global.HCOUNT = 0;
    global.HIGH = (HCOUNT >= 3);
    global.HX = AX;
    global.HY = AY;
}

# ---- readout ----------------------------------------------------------------------
fun commas(n) {
    local.s = "";
    if (n < 1000) return "" + n;
    s = "" + (n %% 1000);
    while (s.Length() < 3) s = "0" + s;
    return commas(Math.Int(n / 1000)) + "," + s;
}

SHOWN = "";
fun readout() {
    local.s = "langton's ant · step " + commas(STEP);
    if (HIGH) s = s + " · highway";
    if (s == SHOWN) return;
    global.SHOWN = s;
    global.READ_R = txt_run("lo", s, SX + MARGIN, SY + Math.Int(FLH * 0.8), 50);
}

# ---- passphrase hooks ---------------------------------------------------------------
fun hook_prompt() { global.SPEED = 20; }
fun hook_key(n) {
    local.k = 0;
    # a few cells in front of the ant change colour
    for (k = 0; k < 3; k++)
        flip(AX + DX[AD] * (2 + Math.Int(rnd() * 3)) + Math.Int(rnd() * 3) - 1,
             AY + DY[AD] * (2 + Math.Int(rnd() * 3)) + Math.Int(rnd() * 3) - 1);
}
fun hook_erase(n) { flip(AX + DX[AD] * 2, AY + DY[AD] * 2); }
fun hook_wrong() {
    local.x = 0;
    local.y = 0;
    # a block of noise around the ant
    for (y = -10; y <= 10; y++)
        for (x = -10; x <= 10; x++)
            if (rnd() < 0.5) flip(AX + x, AY + y);
    global.SPEED = 20;
}
fun hook_enter() { global.SPEED = 60; }
fun hook_question() { }

# ---- power-off: run ahead without drawing, then walk back to the empty grid -----------
if (HALT) {
    for (i = 0; i < 11200; i++) step(0);
    for (i = 0; i < GW * GH; i++) if (G[i]) show(i, 1);
    SPEED = 0 - 46;
    if (MODE == "reboot") NIGHT_R = pr_line("lo", "see you soon.", PR.y1);
    else NIGHT_R = pr_line("lo", "good night.", PR.y1);
}

# ---- main loop -------------------------------------------------------------------------
FRAME = 0;
fun refresh() {
    local.k = 0;
    global.FRAME++;
    if (SPEED > 0) {
        for (k = 0; k < SPEED; k++) { step(1); watch(); }
    } else if (FRAME > 25) {
        for (k = 0; k < 0 - SPEED && STEP > 0; k++) unstep();
    }
    place_ant();
    if (FRAME %% 10 == 0) readout();
    prompt_tick();
}

place_ant();
readout();
prompt_setup();
Plymouth.SetRefreshFunction(refresh);
'''

PLYMOUTH = """[Plymouth Theme]
Name=Langton's Ant
Description=Langton's ant: ten thousand steps of chaos, then a highway; reversed at power-off
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/{name}
ScriptFile=/usr/share/plymouth/themes/{name}/{name}.script
"""


def build(dist):
    out = os.path.join(dist, NAME)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    Image.new("RGBA", (8, 8), CELL + (255,)).save(os.path.join(out, "cell.png"))
    Image.new("RGBA", (8, 8), ANT + (255,)).save(os.path.join(out, "ant.png"))
    t = [lib.lm_fonts(out, TEXT, BG + (255,))]
    bg = ["%.6f" % ((c + 0.5) / 255) for c in BG]
    script = SCRIPT % {"lib": lib.lib_script(), "prompt": lib.prompt_script(), "tables": "\n".join(t),
                       "bgr": bg[0], "bgg": bg[1], "bgb": bg[2]}
    open(os.path.join(out, NAME + ".script"), "w").write(script)
    open(os.path.join(out, NAME + ".plymouth"), "w").write(PLYMOUTH.format(name=NAME))
    return out
