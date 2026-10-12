"""hilbert: a pen plotter fills a sheet with a Hilbert curve as the boot progresses."""
import os
import shutil

from PIL import Image, ImageDraw

import art
import lib

NAME = "hilbert"
ORDER = 6                                  # 64 x 64 cells, 4095 segments
BG = (20, 20, 22)
PAPER = (234, 230, 220)
INK = (30, 30, 34)
RED = (200, 40, 36)
TEXT = {"hi": (226, 226, 226, 255), "lo": (122, 122, 128, 255), "err": (232, 84, 66, 255)}

SCRIPT = r'''# =============================================================================
#  HILBERT — a pen plotter draws a space-filling curve.
#
#  The Hilbert curve of order 6 visits all 4096 cells of a 64 x 64 grid in
#  one continuous line without crossing itself. Here it is the progress bar:
#  the pen draws as the boot goes on, and the sheet fills up quadrant by
#  quadrant. Your passphrase is plotted in red, a few segments per character;
#  a wrong one is wiped back, the right one dries to black. At power-off the
#  plotter retraces the curve and lifts it off the paper.
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

# ---- the sheet ----------------------------------------------------------------
NC = %(ncells)d;                     # cells per side
NSEG = NC * NC - 1;
TOP = SY + Math.Int(SH * 0.06);
AVAIL = PR.y0 - Math.Int(FLH * 2.6) - TOP;
if (AVAIL > SW * 0.86) AVAIL = Math.Int(SW * 0.86);
C = Math.Int(AVAIL / (NC + 3));      # cell size in px, integer so the joints meet
if (C < 3) C = 3;
MG = Math.Int(C * 1.5);              # margin of the drawing on the sheet
PS = NC * C + 2 * MG;
PX = SX + Math.Int((SW - PS) / 2);
PY = TOP + Math.Int((AVAIL - PS) / 2);
LW = Math.Int(C / 5);                # line width
if (LW < 2) LW = 2;

SOLID = Image("solid.png");
SHADOW = Sprite(Image("shadow.png").Scale(PS, PS));
SHADOW.SetPosition(PX + Math.Int(C / 2), PY + Math.Int(C / 2), 1);
SHEET = Sprite(Image("paper.png").Scale(PS, PS));
SHEET.SetPosition(PX, PY, 2);

# crop marks just outside the corners of the drawing area (the L in mark.png
# has its corner at the image centre and points right and down)
MARK = Image("mark.png").Scale(2 * C, 2 * C);
MK.n = 4;                            # global, so mark() stores the sprites here
fun mark(i, x, y) {
    MK[i] = Sprite(MARK.Rotate(i * 1.5707963));
    MK[i].SetPosition(x - C, y - C, 3);
}
MX0 = PX + MG - Math.Int(C / 2);
MX1 = PX + PS - MG + Math.Int(C / 2);
MY0 = PY + MG - Math.Int(C / 2);
MY1 = PY + PS - MG + Math.Int(C / 2);
mark(0, MX1, MY1);
mark(1, MX0, MY1);
mark(2, MX0, MY0);
mark(3, MX1, MY0);

# segment images: horizontal and vertical, ink and red
INKH = Image("ink.png").Scale(C + LW, LW);
INKV = Image("ink.png").Scale(LW, C + LW);
REDH = Image("red.png").Scale(C + LW, LW);
REDV = Image("red.png").Scale(LW, C + LW);

# ---- the curve: start at the lower left, one move per character ------------------
MOVES = "%(moves)s";
GX[0] = 0;
GY[0] = NC - 1;
for (i = 0; i < NSEG; i++) {
    m = MOVES.CharAt(i);
    GX[i + 1] = GX[i];
    GY[i + 1] = GY[i];
    if (m == "r") GX[i + 1] = GX[i] + 1;
    else if (m == "l") GX[i + 1] = GX[i] - 1;
    else if (m == "u") GY[i + 1] = GY[i] - 1;
    else GY[i + 1] = GY[i] + 1;
}

fun px(i) { return PX + MG + GX[i] * C + Math.Int(C / 2); }
fun py(i) { return PY + MG + GY[i] * C + Math.Int(C / 2); }

# ---- the plotter ---------------------------------------------------------------
ARM = Sprite(Image("arm.png").Scale(PS + 6 * C, Math.Max(4, Math.Int(C * 0.55))));
ARMH = Math.Int(Math.Max(4, Math.Int(C * 0.55)) / 2);
CAR_IMG = Image("carriage.png").Scale(Math.Int(C * 1.7), Math.Int(C * 2.3));
CAR = Sprite(CAR_IMG);
CARW = CAR_IMG.GetWidth() / 2;
CARH = CAR_IMG.GetHeight() / 2;
TIP_IMG = Image("tip.png").Scale(LW * 3, LW * 3);
TIP = Sprite(TIP_IMG);
TIPH = TIP_IMG.GetWidth() / 2;

NS = 0;                       # segments on the paper
NRED = 0;                     # how many of them are red (the passphrase)
RED0 = 0;                     # first red segment
WIPE = 0;                     # segments still to wipe back
TARGET = 0;                   # where the pen is headed
PENDOWN = 1;
FRAME = 0;
T = 0;
PROGRESS = 0;
PACE = 220;                   # segments per second: the whole curve in under 19 s
SEGS[0] = 0;                  # sprites of the segments (global)

fun put_seg(i, red) {
    local.x0 = px(i);
    local.y0 = py(i);
    local.x1 = px(i + 1);
    local.y1 = py(i + 1);
    local.h = (y0 == y1);
    local.img = 0;
    if (h) { if (red) img = REDH; else img = INKH; }
    else { if (red) img = REDV; else img = INKV; }
    SEGS[i] = Sprite(img);
    SEGS[i].SetPosition(Math.Min(x0, x1) - Math.Int(LW / 2), Math.Min(y0, y1) - Math.Int(LW / 2), 5);
}

fun recolor(i) {
    if (py(i) == py(i + 1)) SEGS[i].SetImage(INKH);
    else SEGS[i].SetImage(INKV);
}

fun place_pen(i) {
    local.x = px(i);
    local.y = py(i);
    ARM.SetPosition(PX - 3 * C, y - ARMH, 7);
    CAR.SetPosition(x - CARW, y - CARH, 8);
    TIP.SetPosition(x - TIPH, y - TIPH, 9);
    if (PENDOWN) TIP.SetOpacity(1); else TIP.SetOpacity(0.25);
}

# ---- readout --------------------------------------------------------------------
RY = PY + PS + Math.Int(FLH * 0.7);
SHOWN = "";
fun readout() {
    local.ux = 400 + GX[NS] * 160;
    local.uy = 400 + (NC - 1 - GY[NS]) * 160;
    local.cmd = "PD";
    local.s = "";
    if (!PENDOWN) cmd = "PU";
    s = "HP-GL  " + cmd + " " + ux + "," + uy + ";";
    if (s == SHOWN) return;
    global.SHOWN = s;
    global.READ_L = txt_run("lo", s, PX, RY, 50);
    s = "" + NS + "/" + NSEG;
    global.READ_R = txt_run("lo", s, PX + PS - txt_len(s) * FADV, RY, 50);
}

# ---- progress -------------------------------------------------------------------
fun on_progress(duration, progress) {
    global.PROGRESS = progress;
}

fun advance() {
    local.k = 0;
    local.t = 0;
    if (WIPE > 0) {
        # the wrong passphrase is wiped back, three segments a frame
        for (k = 0; k < 3 && WIPE > 0; k++) {
            global.NS--;
            SEGS[NS] = NULL;
            global.WIPE--;
            global.NRED--;
        }
        global.TARGET = NS;
        place_pen(NS);
        return;
    }
    if (P.active == 1) {
        # waiting for the passphrase: the pen only moves when you type
        t = RED0 + NRED;
    } else {
        # the boot: whichever is further, a steady pace or plymouth's estimate
        t = Math.Int(T * PACE);
        if (PROGRESS * NSEG > t) t = Math.Int(PROGRESS * NSEG);
        if (t < TARGET) t = TARGET;
    }
    if (t > NSEG) t = NSEG;
    global.TARGET = t;
    global.PENDOWN = (NS < TARGET || P.active != 1);
    for (k = 0; k < 7 && NS < TARGET; k++) {
        put_seg(NS, (P.active == 1));
        global.NS++;
    }
    place_pen(NS);
}

# ---- passphrase hooks -------------------------------------------------------------
PER_CHAR = 12;
fun hook_prompt() {
    global.RED0 = NS;
    global.NRED = 0;
}
fun hook_key(n) {
    global.NRED = n * PER_CHAR;
    if (RED0 + NRED > NSEG) global.NRED = NSEG - RED0;
}
fun hook_erase(n) {
    # deleting a character wipes its segments
    local.want = RED0 + n * PER_CHAR;
    if (want < NS) {
        global.WIPE = NS - want;
        global.NRED = NS - RED0;
    } else {
        global.NRED = n * PER_CHAR;
    }
}
fun hook_wrong() {
    # the previous attempt is wiped off the paper, back to where it began
    global.WIPE = NS - RED0;
    global.NRED = NS - RED0;
}
fun hook_enter() {
    local.i = 0;
    # the ink dries: red turns black, the pen goes on with the boot
    for (i = RED0; i < NS; i++) recolor(i);
    global.TARGET = NS;
    global.NRED = 0;
    global.T = NS / PACE;
}
fun hook_question() { }

# ---- power-off: the curve is retraced and lifted off ---------------------------------
fun undraw() {
    local.k = 0;
    for (k = 0; k < 10 && NS > 0; k++) {
        global.NS--;
        SEGS[NS] = NULL;
    }
    place_pen(NS);
}

if (HALT) {
    for (i = 0; i < NSEG; i++) put_seg(i, 0);
    NS = NSEG;
    TARGET = NSEG;
    if (MODE == "reboot") NIGHT_R = pr_line("lo", "see you soon.", PR.y1);
    else NIGHT_R = pr_line("lo", "good night.", PR.y1);
}
place_pen(NS);

# ---- main loop ------------------------------------------------------------------
fun refresh() {
    global.FRAME++;
    global.T = T + 0.02;
    if (HALT) { if (FRAME > 40) undraw(); }
    else advance();
    if (FRAME %% 6 == 0) readout();
    prompt_tick();
}

prompt_setup();
Plymouth.SetBootProgressFunction(on_progress);
Plymouth.SetRefreshFunction(refresh);
'''

PLYMOUTH = """[Plymouth Theme]
Name=Hilbert
Description=A pen plotter fills a sheet with a Hilbert curve as the boot progresses
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/{name}
ScriptFile=/usr/share/plymouth/themes/{name}/{name}.script
"""


def d2xy(n, d):
    """Position of step d on the Hilbert curve filling an n x n grid (n a power of 2)."""
    x = y = 0
    s = 1
    t = d
    while s < n:
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        if ry == 0:
            if rx == 1:
                x, y = s - 1 - x, s - 1 - y
            x, y = y, x
        x += s * rx
        y += s * ry
        t //= 4
        s *= 2
    return x, y


def moves(order):
    n = 2 ** order
    pts = [d2xy(n, d) for d in range(n * n)]
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        assert abs(x1 - x0) + abs(y1 - y0) == 1
        # y grows upwards here; the script counts rows downwards from the top
        out.append("r" if x1 > x0 else "l" if x1 < x0 else "u" if y1 > y0 else "d")
    assert pts[0] == (0, 0)
    return "".join(out)


def solid(col, size=8):
    return Image.new("RGBA", (size, size), col + (255,))


def mark_image():
    """Crop mark: an L in the lower right of the canvas (rotated for the other corners)."""
    S = 64
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (150, 146, 138, 255)
    d.rectangle((S // 2 - 1, S // 2 - 1, S - 1, S // 2 + 1), fill=col)
    d.rectangle((S // 2 - 1, S // 2 - 1, S // 2 + 1, S - 1), fill=col)
    return im


def arm_image():
    im = Image.new("RGBA", (64, 8), (64, 66, 72, 255))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 1, 63, 2), fill=(98, 100, 108, 255))
    d.rectangle((0, 7, 63, 7), fill=(40, 42, 46, 255))
    return im


def carriage_image():
    W, H = 34, 46
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((1, 1, W - 2, H - 2), radius=4, fill=(48, 50, 56, 235), outline=(96, 98, 106, 255), width=2)
    d.ellipse((W // 2 - 7, H // 2 - 7, W // 2 + 7, H // 2 + 7), outline=(130, 132, 140, 255), width=2)
    return im


def tip_image():
    im = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((4, 4, 19, 19), fill=RED + (255,))
    d.ellipse((8, 8, 15, 15), fill=(250, 240, 230, 255))
    return im


def build(dist):
    out = os.path.join(dist, NAME)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    solid(BG).save(os.path.join(out, "solid.png"))
    solid(PAPER).save(os.path.join(out, "paper.png"))
    solid((8, 8, 9)).save(os.path.join(out, "shadow.png"))
    solid(INK).save(os.path.join(out, "ink.png"))
    solid(RED).save(os.path.join(out, "red.png"))
    mark_image().save(os.path.join(out, "mark.png"), optimize=True)
    arm_image().save(os.path.join(out, "arm.png"), optimize=True)
    carriage_image().save(os.path.join(out, "carriage.png"), optimize=True)
    tip_image().save(os.path.join(out, "tip.png"), optimize=True)
    t = [lib.lm_fonts(out, TEXT, BG + (255,))]
    bg = ["%.6f" % ((c + 0.5) / 255) for c in BG]
    script = SCRIPT % {"lib": lib.lib_script(), "prompt": lib.prompt_script(), "tables": "\n".join(t),
                       "bgr": bg[0], "bgg": bg[1], "bgb": bg[2],
                       "ncells": 2 ** ORDER, "moves": moves(ORDER)}
    open(os.path.join(out, NAME + ".script"), "w").write(script)
    open(os.path.join(out, NAME + ".plymouth"), "w").write(PLYMOUTH.format(name=NAME))
    return out
