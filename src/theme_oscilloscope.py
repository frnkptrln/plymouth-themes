"""oscilloscope: a phosphor-green XY scope drawing Lissajous figures."""
import math, os, shutil
from PIL import Image, ImageDraw, ImageFilter
import fontkit, lib

NAME = "oscilloscope"

P31 = (110, 255, 140)            # phosphor green
HOT = (225, 255, 230)            # beam spot
GRID = (34, 86, 50)              # graticule
AXIS = (52, 128, 72)
GRAT_H = (320, 400, 480, 560, 640, 720, 800, 960, 1120, 1280, 1600)
DOT_R = (3, 4, 5, 6, 7, 8, 10, 12)
TEXT_SCALES = (1, 2, 3, 4)

# frequency ratios the beam wanders through (x:y)
RATIOS = [(3, 2), (1, 2), (4, 3), (2, 3), (5, 4), (3, 1), (5, 3), (1, 1), (3, 4), (2, 1)]


def graticule(h):
    w = h * 5 // 4
    ss = 3
    W, H = w * ss, h * ss
    im = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(im)
    lw = max(1, round(h / 400)) * ss
    dx, dy = W / 10, H / 8
    # dotted division lines
    step = 4 * ss
    for i in range(1, 10):
        x = round(i * dx)
        if i == 5:
            continue
        for y in range(0, H, step):
            d.rectangle((x - lw // 2, y, x + lw // 2, y + lw), fill=GRID)
    for j in range(1, 8):
        y = round(j * dy)
        if j == 4:
            continue
        for x in range(0, W, step):
            d.rectangle((x, y - lw // 2, x + lw, y + lw // 2), fill=GRID)
    # centre axes with minor ticks
    cx, cy = W // 2, H // 2
    d.rectangle((cx - lw // 2, 0, cx + lw // 2, H), fill=AXIS)
    d.rectangle((0, cy - lw // 2, W, cy + lw // 2), fill=AXIS)
    tick = dx * 0.06
    for i in range(0, 51):
        x = round(i * dx / 5)
        d.rectangle((x - lw // 2, cy - tick, x + lw // 2, cy + tick), fill=AXIS)
    for j in range(0, 41):
        y = round(j * dy / 5)
        d.rectangle((cx - tick, y - lw // 2, cx + tick, y + lw // 2), fill=AXIS)
    # frame
    d.rectangle((0, 0, W - 1, H - 1), outline=AXIS, width=lw)
    im = im.resize((w, h), Image.LANCZOS)
    # faint glow on the lines
    glow = im.filter(ImageFilter.GaussianBlur(h / 300))
    out = Image.blend(im, glow, 0.35)
    out = Image.composite(im, out, im.convert("L").point(lambda v: 255 if v > 60 else 0))
    return out


def spot(r, core_col, halo_col, core=0.55, reach=3.2, gain=1.0):
    """Radial phosphor dot: bright core, soft halo. Loaded directly (no Crop),
    so translucency is fine here."""
    size = int(math.ceil(r * reach)) * 2 + 1
    ss = 4
    S = size * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    px = im.load()
    c = (S - 1) / 2
    for y in range(S):
        for x in range(S):
            dd = math.hypot(x - c, y - c) / ss / r
            if dd <= core:
                a = 1.0
                col = core_col
            else:
                a = math.exp(-((dd - core) / 0.75) ** 2) * 0.85 + math.exp(-(dd - core) * 1.6) * 0.25
                col = halo_col
            a = min(1.0, a * gain)
            if a > 0.004:
                px[x, y] = col + (int(a * 255),)
    return im.resize((size, size), Image.LANCZOS)


def ps(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


SCRIPT = r'''# =============================================================================
#  OSCILLOSCOPE — Lissajous figures on green phosphor.
#
#  The beam runs through frequency ratios (3:2, 4:3, 5:4 ...), the phase
#  drifts, and the trace fades like on a P31 tube. Every keystroke disturbs
#  the signal; after Enter the figure locks to 1:1, a circle. If the prompt
#  comes back (wrong passphrase), the circle is torn apart. At power-off the
#  picture collapses like on an old tube.
#
#  Claude, October 2026 — for Frank
# =============================================================================

Window.SetBackgroundTopColor(0, 0, 0);
Window.SetBackgroundBottomColor(0, 0, 0);

SW = Window.GetWidth();
SH = Window.GetHeight();
SX = Window.GetX();
SY = Window.GetY();
PI = 3.14159265358979;
%(lib)s

# ---- geometry ---------------------------------------------------------------
%(grat)s
GH = GRL[0];
best = 99999;
for (i = 0; i < GRL.n; i++) {
    d = Math.Abs(GRL[i] - SH * 0.68);
    if (d < best) { best = d; GH = GRL[i]; }
}
GW = Math.Int(GH * 5 / 4);
if (GW > SW * 0.92) {
    # very narrow screens: shrink to fit the width
    for (i = 0; i < GRL.n; i++) if (Math.Int(GRL[i] * 5 / 4) <= SW * 0.92) GH = GRL[i];
    GW = Math.Int(GH * 5 / 4);
}
GX = SX + Math.Int((SW - GW) / 2);
GY = SY + Math.Int((SH - GH) / 2) - Math.Int(SH * 0.015);
GRAT = Sprite(Image("graticule-" + GH + ".png"));
GRAT.SetPosition(GX, GY, 0);
CX = GX + GW / 2;
CY = GY + GH / 2;
AX = GH * 0.42;          # same deflection on both channels: 1:1 is a true circle
AY = GH * 0.42;

TS = 1;
if (SH >= 1500) TS = 2;
if (SH >= 2600) TS = 3;
font_load("g", "vga-g-" + TS + ".png", 9 * TS, 16 * TS, 9 * TS, 16 * TS, 0);
font_load("d", "vga-d-" + TS + ".png", 9 * TS, 16 * TS, 9 * TS, 16 * TS, 0);
ADV = 9 * TS;
LH = 16 * TS;
Y_TOP = GY - Math.Int(LH * 1.7);
Y_B1 = GY + GH + Math.Int(LH * 0.9);
Y_B2 = Y_B1 + Math.Int(LH * 1.4);

# ---- beam -------------------------------------------------------------------
%(dots)s
DR = DRL[0];
best = 99999;
for (i = 0; i < DRL.n; i++) {
    d = Math.Abs(DRL[i] - SH / 190);
    if (d < best) { best = d; DR = DRL[i]; }
}
DOT = Image("dot-" + DR + ".png");
DH = DOT.GetWidth() / 2;
HEAD = Image("head-" + DR + ".png");
HH = HEAD.GetWidth() / 2;

N = 900;           # trail length (sprites)
K = 6;             # new points per frame
L = 10;            # fade levels
for (i = 0; i < N; i++) {
    TR[i] = Sprite(DOT);
    TR[i].SetPosition(-200, -200, 2);
    TR[i].SetOpacity(0);
}
for (k = 1; k < L; k++) {
    AGE[k] = Math.Int((k * N + L - 1) / L);
    f = 1 - k / L;
    OPL[k] = 0.02 + 0.98 * f * f * f;
}
RING = 0;
HS = Sprite(HEAD);
HS.SetPosition(-200, -200, 3);

%(ratios)s
RI = 0;
TA = RA[0];
TB = RB[0];
FA = TA;
FB = TB;
QX = 0;            # phase accumulators
QY = 0;
PHI = 0;
DPHI = 2 * PI / 1400;          # slow drift: the figure seems to turn in space
DQ = 2 * PI / 150 / K;         # one period of the base frequency every 3 s
NZ = 0;            # noise amplitude (fraction of the deflection), wrong passphrase
NW = 0;            # interference from typing: a fast wiggle on both channels
WQ = 0;
W1 = 0;
W2 = 0;
LOCK = 0;          # 1: forced to 1:1 -> circle
FRAME = 0;
NEXTSW = 700;

MODE = Plymouth.GetMode();
SHUT = 0;
if (MODE == "shutdown" || MODE == "reboot") SHUT = 1;
SHT = 0;
SXF = 1;
SYF = 1;

fun beam_point(x, y) {
    local.k = 0;
    TR[RING].SetPosition(CX + AX * x * SXF - DH, CY - AY * y * SYF - DH, 2);
    TR[RING].SetOpacity(1);
    for (k = 1; k < L; k++) TR[(RING - AGE[k] + N) %% N].SetOpacity(OPL[k]);
    global.RING = (RING + 1) %% N;
}

# ---- readouts ---------------------------------------------------------------
fun dec2(v) {
    local.p = Math.Int(v * 100 + 0.5);
    local.r = p %% 100;
    local.s = "" + r;
    if (r < 10) s = "0" + s;
    return Math.Int(p / 100) + "." + s;
}

TOP_L = txt_run("d", "CH1 0.5V/div  CH2 0.5V/div  X-Y", GX, Y_TOP, 5);
SHOWN_R = "";
fun draw_ratio() {
    local.v = (PHI / PI) %% 2;
    if (v < 0) v = v + 2;
    local.s = TA + ":" + TB + "   φ" + dec2(v) + "π";
    if (LOCK) s = "1:1   LOCK";
    if (SHUT) s = "OFF";
    if (s == SHOWN_R) return;
    global.SHOWN_R = s;
    global.TOP_R = txt_run("g", s, GX + GW - txt_len(s) * ADV, Y_TOP, 5);
}

# ---- password / question ----------------------------------------------------
P.active = 0;
P.bullets = -1;
P.prompt = "";
P.last = "";
P.answered = 0;
P.err = 0;
P.blink = 0;
P.caps = 0;
P.grace = 0;
MSG.t = 0;

# a keystroke couples into the probes: the trace wiggles, but stays one line
fun interfere() {
    global.NW = Math.Min(0.075, NW + 0.04);
    global.W1 = rnd() * 6.28;
    global.W2 = rnd() * 6.28;
}

fun draw_entry(s) {
    local.t = txt_fit(s, Math.Int(GW / ADV) - 3);
    global.ENTRY_R = txt_run("g", "> " + t, GX, Y_B2, 6);
    global.CURSOR_R = txt_run("g", "_", GX + (txt_len(t) + 2) * ADV, Y_B2, 6);
}

fun on_password(prompt, bullets) {
    local.s = "";
    local.i = 0;
    local.n = 0;
    if (P.active != 1) {
        if (P.answered && prompt == P.last) {
            # the passphrase was wrong: tear the circle apart
            P.err = 200;
            global.NZ = 1.3;
            global.LOCK = 0;
            global.RI = Math.Int(rnd() * RN);
            global.TA = RA[RI];
            global.TB = RB[RI];
        }
        P.active = 1;
        P.prompt = prompt;
        P.bullets = -1;
        P.grace = 0;
        if (prompt == "") prompt = "Passphrase:";
        global.PROMPT_R = txt_run("d", txt_fit(prompt, Math.Int(GW / ADV)), GX, Y_B1, 6);
        global.MSG_R = NULL;
    }
    if (bullets > P.bullets && P.bullets >= 0) interfere();
    if (bullets != P.bullets) {
        P.bullets = bullets;
        n = bullets;
        if (n > 32) n = 32;
        for (i = 0; i < n; i++) s = s + "•";
        draw_entry(s);
    }
}

fun on_question(prompt, entry) {
    if (P.active != 2) {
        P.active = 2;
        P.err = 0;
        global.ERR_R = NULL;
        global.PROMPT_R = txt_run("d", txt_fit(prompt, Math.Int(GW / ADV)), GX, Y_B1, 6);
    }
    draw_entry(entry);
    interfere();
}

fun on_normal() {
    if (P.active == 1) {
        P.answered = 1;
        P.last = P.prompt;
        global.LOCK = 1;          # optimistic: lock to a circle
        P.grace = 250;
    }
    P.active = 0;
    P.bullets = -1;
    global.PROMPT_R = NULL;
    global.ENTRY_R = NULL;
    global.CURSOR_R = NULL;
    global.CAPS_R = NULL;
    P.caps = 0;
}

fun on_message(text) {
    if (P.active) return;
    global.MSG_R = txt_run("d", txt_fit(text, Math.Int(GW / ADV)), GX, Y_B1, 6);
    MSG.t = 250;
}

fun on_hide_message(text) {
    global.MSG_R = NULL;
}

# ---- main loop --------------------------------------------------------------
fun refresh() {
    local.k = 0;
    local.x = 0;
    local.y = 0;
    local.dd = 0;
    local.tgt = 0;
    global.FRAME++;

    # which figure
    if (!LOCK && !SHUT && FRAME >= NEXTSW) {
        global.RI = (RI + 1) %% RN;
        global.TA = RA[RI];
        global.TB = RB[RI];
        global.NEXTSW = FRAME + 700;
    }
    if (LOCK) { global.TA = 1; global.TB = 1; }
    global.FA = FA + (TA - FA) * 0.025;
    global.FB = FB + (TB - FB) * 0.025;

    # phase: drift, or pull the relative phase to pi/2 for a clean circle
    if (LOCK) {
        dd = QX + PHI - QY;
        tgt = PI / 2 + 2 * PI * Math.Int((dd - PI / 2) / (2 * PI) + 0.5);
        global.PHI = PHI + (tgt - dd) * 0.06;
    } else {
        global.PHI = PHI + DPHI;
    }

    # power off: collapse to a line, then to a dot, then fade
    if (SHUT) {
        global.SHT++;
        if (SHT > 60) global.SYF = Math.Max(0, 1 - (SHT - 60) / 45);
        if (SHT > 105) global.SXF = Math.Max(0, 1 - (SHT - 105) / 35);
        if (SHT > 140) HS.SetOpacity(Math.Max(0, 1 - (SHT - 140) / 60));
    }

    for (k = 0; k < K; k++) {
        global.QX = QX + FA * DQ;
        global.QY = QY + FB * DQ;
        x = Math.Sin(QX + PHI);
        y = Math.Sin(QY);
        if (NW > 0.002) {
            # small phase steps per sample, so neighbouring dots stay touching
            global.WQ = WQ + 0.18;
            x = x + NW * Math.Sin(WQ + W1);
            y = y + NW * Math.Sin(WQ * 1.37 + W2);
        }
        if (NZ > 0.002) {
            x = x + NZ * (rnd() - 0.5);
            y = y + NZ * (rnd() - 0.5);
        }
        beam_point(x, y);
    }
    HS.SetPosition(CX + AX * x * SXF - HH, CY - AY * y * SYF - HH, 3);
    global.NZ = NZ * 0.94;
    global.NW = NW * 0.95;

    if (FRAME %% 20 == 0) draw_ratio();

    if (P.grace > 0) P.grace--;
    if (LOCK && P.grace == 0 && !P.active && FRAME %% 600 == 0) global.LOCK = 0;

    if (P.active) {
        P.blink = (P.blink + 1) %% 50;
        if (CURSOR_R) run_opacity(CURSOR_R, P.blink < 25);
        if (P.active == 1 && P.blink %% 10 == 0) {
            if (Plymouth.GetCapslockState()) {
                if (!P.caps) global.CAPS_R = txt_run("g", "CAPS", GX + GW - 4 * ADV, Y_B2, 6);
                P.caps = 1;
            } else {
                P.caps = 0;
                global.CAPS_R = NULL;
            }
        }
    }
    if (P.err > 0) {
        # on the entry line, left of the CAPS indicator: the prompt line above can be full
        if (!ERR_R) global.ERR_R = txt_run("g", "wrong. try again.", GX + GW - 23 * ADV, Y_B2, 6);
        P.err--;
        run_opacity(ERR_R, (P.err %% 30) < 20);
        if (P.err == 0) global.ERR_R = NULL;
    }
    if (MSG.t > 0) {
        MSG.t--;
        if (MSG.t == 0) global.MSG_R = NULL;
    }
}

draw_ratio();
Plymouth.SetRefreshFunction(refresh);
Plymouth.SetDisplayPasswordFunction(on_password);
Plymouth.SetDisplayQuestionFunction(on_question);
Plymouth.SetDisplayNormalFunction(on_normal);
Plymouth.SetDisplayMessageFunction(on_message);
Plymouth.SetHideMessageFunction(on_hide_message);
'''

PLYMOUTH = """[Plymouth Theme]
Name=Oscilloscope
Description=Lissajous figures on green phosphor; the beam locks to a circle when you unlock
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
    g = ["GRL[%d] = %d;" % (i, h) for i, h in enumerate(GRAT_H)] + ["GRL.n = %d;" % len(GRAT_H)]
    for h in GRAT_H:
        graticule(h).save(os.path.join(out, "graticule-%d.png" % h), optimize=True)
    dl = ["DRL[%d] = %d;" % (i, r) for i, r in enumerate(DOT_R)] + ["DRL.n = %d;" % len(DOT_R)]
    for r in DOT_R:
        spot(r, P31, P31, core=0.42, reach=3.0, gain=0.9).save(os.path.join(out, "dot-%d.png" % r), optimize=True)
        spot(r * 1.5, HOT, P31, core=0.5, reach=3.4, gain=1.0).save(os.path.join(out, "head-%d.png" % r), optimize=True)
    for s in TEXT_SCALES:
        im, cw, ch = fontkit.opaque_glow_atlas((120, 255, 150, 255), s, glow=(0.9, 0.8))
        im.save(os.path.join(out, "vga-g-%d.png" % s), optimize=True)
        im, cw, ch = fontkit.opaque_glow_atlas((56, 150, 84, 255), s, glow=(0.9, 0.6))
        im.save(os.path.join(out, "vga-d-%d.png" % s), optimize=True)
    rl = ["RA[%d] = %d; RB[%d] = %d;" % (i, a, i, b) for i, (a, b) in enumerate(RATIOS)] + ["RN = %d;" % len(RATIOS)]
    script = SCRIPT % {"lib": lib.lib_script(), "grat": "\n".join(g), "dots": "\n".join(dl), "ratios": "\n".join(rl)}
    open(os.path.join(out, NAME + ".script"), "w").write(script)
    open(os.path.join(out, NAME + ".plymouth"), "w").write(PLYMOUTH.format(name=NAME))
    return out
