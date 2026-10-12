"""trisolaris: three suns, a live three-body simulation."""
import math, os, shutil
from PIL import Image
import fontkit, lib

NAME = "trisolaris"

BG = (4, 5, 10, 255)
SUNS = [  # core, halo
    ((255, 246, 222), (255, 214, 140)),   # gold-white
    ((255, 228, 190), (255, 150, 64)),    # amber
    ((255, 214, 200), (255, 96, 76)),     # coral
]
TRAIL = [(255, 214, 140), (255, 160, 70), (255, 110, 86)]
SUN_R = (10, 14, 18, 24, 32, 44)          # core radius in px, picked by screen height
TRAIL_R = (2, 3, 4, 5, 6, 8)
FONT_SIZES = (14, 17, 20, 24, 28, 34, 40)
TEXT = {"hi": (236, 218, 184, 255), "lo": (130, 116, 98, 255), "err": (255, 120, 92, 255)}

# Periodic three-body orbits (Šuvakov & Dmitrašinović 2013, plus the figure-eight):
# positions (-1,0), (1,0), (0,0); velocities v1 = v2 = (p1, p2), v3 = -2 v1; G = m = 1.
ORBITS = [
    ("figure-eight",   0.347111, 0.532728),
    ("butterfly I",    0.306893, 0.125507),
    ("butterfly II",   0.392955, 0.097579),
    ("moth I",         0.464445, 0.396060),
    ("yin-yang I",     0.513938, 0.304736),
    ("goggles",        0.083300, 0.127889),
    ("dragonfly",      0.080584, 0.588836),
    ("figure-eight",   0.347111, 0.532728),
]


def glow(r, core_col, halo_col, reach=6.0, core=0.35, halo_gain=0.9, fade_edge=False):
    size = int(math.ceil(r * reach)) * 2 + 1
    ss = 3
    S = size * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    px = im.load()
    c = (S - 1) / 2
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - c, y - c) / ss / r
            if d <= core:
                px[x, y] = core_col + (255,)
                continue
            # bright limb + long soft corona
            a = math.exp(-((d - core) / 0.55) ** 2) * 0.95 + halo_gain * 0.35 / (1 + (d * 1.3) ** 2.2)
            a = min(1.0, a)
            if fade_edge:
                # bring the faint outer corona to exactly zero before the image edge
                t = min(1.0, max(0.0, (d / reach - 0.62) / 0.38))
                a *= 1 - t * t * (3 - 2 * t)
            t = min(1.0, (d - core) / 0.8)
            col = tuple(int(core_col[i] * (1 - t) + halo_col[i] * t) for i in range(3))
            if a > 0.003:
                px[x, y] = col + (int(a * 255),)
    return im.resize((size, size), Image.LANCZOS)


def star(r, col):
    return glow(r, col, col, reach=3.0, core=0.25, halo_gain=0.3)


SCRIPT = r'''# =============================================================================
#  TRISOLARIS — three suns, computed live.
#
#  Every boot starts on a known periodic orbit of the three-body problem
#  (figure-eight, butterfly, moth, yin-yang, goggles, dragonfly). Almost all
#  of them are unstable: rounding errors are enough, and after a few periods
#  the stable era tips into a chaotic one. Every keystroke nudges a sun, a
#  wrong passphrase all three. When a sun is flung out, the era ends and a new
#  one begins. At power-off gravity fades away.
#
#  Integration: velocity Verlet with adaptive substeps, G = m = 1.
#
#  Claude, October 2026 — for Frank
# =============================================================================

# exactly (4, 5, 10) — baked into the font images
Window.SetBackgroundTopColor(4.5 / 255, 5.5 / 255, 10.5 / 255);
Window.SetBackgroundBottomColor(4.5 / 255, 5.5 / 255, 10.5 / 255);

SW = Window.GetWidth();
SH = Window.GetHeight();
SX = Window.GetX();
SY = Window.GetY();
%(lib)s

fun nearest(list, v) {
    local.best = 99999;
    local.r = list[0];
    local.i = 0;
    for (i = 0; i < list.n; i++)
        if (Math.Abs(list[i] - v) < best) { best = Math.Abs(list[i] - v); r = list[i]; }
    return r;
}

# ---- assets -----------------------------------------------------------------
%(tables)s
M = SH;
if (SW < M) M = SW;
SR = nearest(SRL, M / 46);
TRR = nearest(TRL, M / 230);
FS = nearest(FSL, SH / 50);
for (i = 0; i < FSL.n; i++) if (FSL[i] == FS) { FADV = FSA[i]; FLH = FSH[i]; }
font_load("hi",  "font-hi-"  + FS + ".png", FADV, FLH, FADV, FLH, 0);
font_load("lo",  "font-lo-"  + FS + ".png", FADV, FLH, FADV, FLH, 0);
font_load("err", "font-err-" + FS + ".png", FADV, FLH, FADV, FLH, 0);

# ---- sky --------------------------------------------------------------------
NSTARS = Math.Int(SW * SH / 9000);
if (NSTARS > 320) NSTARS = 320;
for (i = 0; i < 3; i++) STARIMG[i] = Image("star-" + i + ".png");
for (i = 0; i < NSTARS; i++) {
    k = Math.Int(rnd() * rnd() * 3);
    STAR[i].s = Sprite(STARIMG[k]);
    STAR[i].s.SetPosition(SX + rnd() * SW, SY + rnd() * SH, 0);
    STAR[i].base = 0.25 + 0.75 * rnd() * rnd();
    STAR[i].ph = rnd() * 6.28;
    STAR[i].sp = 0.02 + 0.05 * rnd();
    STAR[i].s.SetOpacity(STAR[i].base);
}
TW = 0;

# ---- bodies -----------------------------------------------------------------
SCALE = M * 0.30;              # pixels per unit
CX = SX + SW / 2;
CY = SY + SH / 2 - M * 0.03;
for (b = 0; b < 3; b++) {
    SUNIMG[b] = Image("sun-" + b + "-" + SR + ".png");
    B[b].s = Sprite(SUNIMG[b]);
    B[b].h = SUNIMG[b].GetWidth() / 2;
    B[b].s.SetZ(10 + b);
    TIMG[b] = Image("trail-" + b + "-" + TRR + ".png");
}
TH = TIMG[0].GetWidth() / 2;

NT = 260;          # trail sprites per sun
L = 6;             # fade levels
TGAP2 = (TRR * 1.6) * (TRR * 1.6);   # beyond this step (px^2) a midpoint closes the gap
for (b = 0; b < 3; b++) {
    for (i = 0; i < NT; i++) {
        T[b][i] = Sprite(TIMG[b]);
        T[b][i].SetPosition(-100, -100, 2);
        T[b][i].SetOpacity(0);
    }
    TRING[b] = 0;
}
for (k = 1; k < L; k++) {
    AGE[k] = Math.Int((k * NT + L - 1) / L);
    f = 1 - k / L;
    OPL[k] = 0.03 + 0.97 * f * f;
}

%(orbits)s

ERA = 0;
G = 1;
SIMT = 0;
EPS2 = 0.0004;
CHAOS = 0;
FADE = 0;          # >0: era is ending, suns fading out
FADEIN = 0;

fun era_begin() {
    local.k = 0;
    local.p1 = 0;
    local.p2 = 0;
    global.ERA++;
    global.CHAOS = 0;
    global.SIMT = 0;
    if (ERA == 1) k = Math.Int(rnd() * ON);
    else k = Math.Int(rnd() * ON);
    global.ONAME = OB[k].name;
    p1 = OB[k].p1;
    p2 = OB[k].p2;
    B[0].x = -1; B[0].y = 0; B[0].vx = p1;      B[0].vy = p2;
    B[1].x = 1;  B[1].y = 0; B[1].vx = p1;      B[1].vy = p2;
    B[2].x = 0;  B[2].y = 0; B[2].vx = -2 * p1; B[2].vy = -2 * p2;
    # a whisper of noise so that unstable orbits do what they do
    for (k = 0; k < 3; k++) {
        B[k].vx = B[k].vx + (rnd() - 0.5) * 0.000002;
        B[k].vy = B[k].vy + (rnd() - 0.5) * 0.000002;
        B[k].m = 1;
    }
    accel();
    global.FADEIN = 60;
    draw_label();
}

fun accel() {
    local.i = 0;
    local.j = 0;
    local.dx = 0;
    local.dy = 0;
    local.r2 = 0;
    local.f = 0;
    local.rmin = 99;
    for (i = 0; i < 3; i++) { B[i].ax = 0; B[i].ay = 0; }
    for (i = 0; i < 3; i++) {
        for (j = i + 1; j < 3; j++) {
            dx = B[j].x - B[i].x;
            dy = B[j].y - B[i].y;
            r2 = dx * dx + dy * dy;
            if (r2 < rmin) rmin = r2;
            r2 = r2 + EPS2;
            f = G / (r2 * Math.Sqrt(r2));
            B[i].ax = B[i].ax + f * B[j].m * dx;
            B[i].ay = B[i].ay + f * B[j].m * dy;
            B[j].ax = B[j].ax - f * B[i].m * dx;
            B[j].ay = B[j].ay - f * B[i].m * dy;
        }
    }
    global.RMIN2 = rmin;
}

DTF = 0.017;       # simulated time per frame
# Velocity Verlet on local copies, with the three pair forces written out
# (all masses are 1; accel() above is the readable version). Plymouth's
# interpreter looks every name up in a hash, so B[i].x costs three lookups
# and x0 one.
fun advance() {
    local.n = 8;
    local.i = 0;
    local.g = G;
    local.e2 = EPS2;
    local.x0 = B[0].x; local.y0 = B[0].y; local.u0 = B[0].vx; local.v0 = B[0].vy; local.ax0 = B[0].ax; local.ay0 = B[0].ay;
    local.x1 = B[1].x; local.y1 = B[1].y; local.u1 = B[1].vx; local.v1 = B[1].vy; local.ax1 = B[1].ax; local.ay1 = B[1].ay;
    local.x2 = B[2].x; local.y2 = B[2].y; local.u2 = B[2].vx; local.v2 = B[2].vy; local.ax2 = B[2].ax; local.ay2 = B[2].ay;
    local.dx = 0;
    local.dy = 0;
    local.r2 = 0;
    local.f = 0;
    local.rmin = RMIN2;
    if (RMIN2 < 0.09) n = 24;
    if (RMIN2 < 0.01) n = 64;
    local.dt = DTF / n;
    local.h = 0.5 * dt;
    for (i = 0; i < n; i++) {
        u0 = u0 + h * ax0; v0 = v0 + h * ay0;
        u1 = u1 + h * ax1; v1 = v1 + h * ay1;
        u2 = u2 + h * ax2; v2 = v2 + h * ay2;
        x0 = x0 + dt * u0; y0 = y0 + dt * v0;
        x1 = x1 + dt * u1; y1 = y1 + dt * v1;
        x2 = x2 + dt * u2; y2 = y2 + dt * v2;
        dx = x1 - x0; dy = y1 - y0; r2 = dx * dx + dy * dy; rmin = r2;
        r2 = r2 + e2; f = g / (r2 * Math.Sqrt(r2));
        ax0 = f * dx; ay0 = f * dy; ax1 = 0 - ax0; ay1 = 0 - ay0;
        dx = x2 - x0; dy = y2 - y0; r2 = dx * dx + dy * dy; if (r2 < rmin) rmin = r2;
        r2 = r2 + e2; f = g / (r2 * Math.Sqrt(r2));
        ax0 = ax0 + f * dx; ay0 = ay0 + f * dy; ax2 = 0 - f * dx; ay2 = 0 - f * dy;
        dx = x2 - x1; dy = y2 - y1; r2 = dx * dx + dy * dy; if (r2 < rmin) rmin = r2;
        r2 = r2 + e2; f = g / (r2 * Math.Sqrt(r2));
        ax1 = ax1 + f * dx; ay1 = ay1 + f * dy; ax2 = ax2 - f * dx; ay2 = ay2 - f * dy;
        u0 = u0 + h * ax0; v0 = v0 + h * ay0;
        u1 = u1 + h * ax1; v1 = v1 + h * ay1;
        u2 = u2 + h * ax2; v2 = v2 + h * ay2;
    }
    B[0].x = x0; B[0].y = y0; B[0].vx = u0; B[0].vy = v0; B[0].ax = ax0; B[0].ay = ay0;
    B[1].x = x1; B[1].y = y1; B[1].vx = u1; B[1].vy = v1; B[1].ax = ax1; B[1].ay = ay1;
    B[2].x = x2; B[2].y = y2; B[2].vx = u2; B[2].vy = v2; B[2].ax = ax2; B[2].ay = ay2;
    global.RMIN2 = rmin;
    global.SIMT = SIMT + DTF;
}

fun kick(b, s) {
    B[b].vx = B[b].vx + (rnd() - 0.5) * s;
    B[b].vy = B[b].vy + (rnd() - 0.5) * s;
    if (!CHAOS) { global.CHAOS = 1; draw_label(); }
}

# ---- drawing ----------------------------------------------------------------
fun trail_point(b, px, py) {
    local.k = 0;
    local.r = TRING[b];
    T[b][r].SetPosition(px - TH, py - TH, 2);
    T[b][r].SetOpacity(1);
    for (k = 1; k < L; k++) T[b][(r - AGE[k] + NT) %% NT].SetOpacity(OPL[k]);
    global.TRING[b] = (r + 1) %% NT;
}

fun draw_bodies() {
    local.b = 0;
    local.px = 0;
    local.py = 0;
    local.o = 1;
    if (FADEIN > 0) o = 1 - FADEIN / 60;
    if (FADE > 0) o = FADE / 90;
    for (b = 0; b < 3; b++) {
        px = CX + B[b].x * SCALE;
        py = CY - B[b].y * SCALE;
        # one trail point per frame; a fast sun gets the midpoint as well
        if ((px - B[b].px) * (px - B[b].px) + (py - B[b].py) * (py - B[b].py) > TGAP2)
            trail_point(b, (px + B[b].px) / 2, (py + B[b].py) / 2);
        trail_point(b, px, py);
        B[b].px = px;
        B[b].py = py;
        B[b].s.SetPosition(px - B[b].h, py - B[b].h, 10 + b);
        B[b].s.SetOpacity(o);
    }
}

# ---- footer -----------------------------------------------------------------
MARGIN = Math.Int(FADV * 2);
LY0 = SY + SH - Math.Int(FLH * 3.6);
LY1 = LY0 + FLH;
LY2 = LY1 + Math.Int(FLH * 1.15);
MODE = Plymouth.GetMode();
HALT = (MODE == "shutdown" || MODE == "reboot");

fun pad4(n) {
    local.s = "" + n;
    while (s.Length() < 4) s = "0" + s;
    return s;
}

fun draw_label() {
    local.s = "era " + pad4(ERA) + " · " + ONAME;
    if (CHAOS) s = s + " · chaotic";
    if (HALT) s = "halt · era " + pad4(ERA);
    global.LABEL_R = txt_run("lo", s, SX + MARGIN, LY0, 1);
}

TSHOWN = -1;
fun draw_time() {
    local.t = Math.Int(SIMT * 10);
    local.s = "";
    if (t == TSHOWN) return;
    global.TSHOWN = t;
    s = "t " + Math.Int(t / 10) + "." + (t %% 10);
    global.TIME_R = txt_run("lo", s, SX + SW - MARGIN - txt_len(s) * FADV, LY0, 1);
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
MSG.t = 0;

fun draw_entry(s) {
    local.t = txt_fit(s, Math.Int((SW - 2 * MARGIN) / FADV) - 3);
    global.ENTRY_R = txt_run("hi", "> " + t, SX + MARGIN, LY2, 1);
    global.CURSOR_R = txt_run("hi", "_", SX + MARGIN + (txt_len(t) + 2) * FADV, LY2, 1);
}

fun on_password(prompt, bullets) {
    local.s = "";
    local.i = 0;
    local.n = 0;
    if (P.active != 1) {
        if (P.answered && prompt == P.last) {
            P.err = 220;
            for (i = 0; i < 3; i++) kick(i, 0.6);
        }
        P.active = 1;
        P.prompt = prompt;
        P.bullets = -1;
        if (prompt == "") prompt = "passphrase:";
        global.PROMPT_R = txt_run("lo", txt_fit(prompt, Math.Int((SW - 2 * MARGIN) / FADV)), SX + MARGIN, LY1, 1);
        global.MSG_R = NULL;
    }
    if (bullets > P.bullets && P.bullets >= 0) kick(Math.Int(rnd() * 3), 0.06);
    if (bullets != P.bullets) {
        P.bullets = bullets;
        n = bullets;
        if (n > 40) n = 40;
        for (i = 0; i < n; i++) s = s + "• ";
        draw_entry(s);
    }
}

fun on_question(prompt, entry) {
    if (P.active != 2) {
        P.active = 2;
        P.err = 0;
        global.ERR_R = NULL;
        global.PROMPT_R = txt_run("lo", txt_fit(prompt, Math.Int((SW - 2 * MARGIN) / FADV)), SX + MARGIN, LY1, 1);
    }
    draw_entry(entry);
}

fun on_normal() {
    if (P.active == 1) {
        P.answered = 1;
        P.last = P.prompt;
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
    global.MSG_R = txt_run("lo", txt_fit(text, Math.Int((SW - 2 * MARGIN) / FADV)), SX + MARGIN, LY1, 1);
    MSG.t = 250;
}

fun on_hide_message(text) {
    global.MSG_R = NULL;
}

# ---- main loop --------------------------------------------------------------
FRAME = 0;
fun twinkle() {
    local.i = 0;
    local.k = 0;
    for (k = 0; k < 6; k++) {
        i = (TW + k * 37) %% NSTARS;
        STAR[i].ph = STAR[i].ph + STAR[i].sp * 6;
        STAR[i].s.SetOpacity(STAR[i].base * (0.7 + 0.3 * Math.Sin(STAR[i].ph)));
    }
    global.TW = (TW + 1) %% NSTARS;
}

fun escaped() {
    local.i = 0;
    local.cx = (B[0].x + B[1].x + B[2].x) / 3;
    local.cy = (B[0].y + B[1].y + B[2].y) / 3;
    for (i = 0; i < 3; i++)
        if ((B[i].x - cx) * (B[i].x - cx) + (B[i].y - cy) * (B[i].y - cy) > 20) return 1;
    return 0;
}

fun refresh() {
    global.FRAME++;
    if (HALT && G > 0) {
        global.G = Math.Max(0, G - 0.012);
        if (FRAME == 1) draw_label();
    }
    advance();
    draw_bodies();
    if (FADEIN > 0) global.FADEIN--;
    if (FADE > 0) {
        global.FADE--;
        if (FADE == 0) era_begin();
    } else if (!HALT && escaped()) {
        global.FADE = 90;
    }
    twinkle();
    if (FRAME %% 5 == 0) draw_time();

    if (P.active) {
        P.blink = (P.blink + 1) %% 50;
        if (CURSOR_R) run_opacity(CURSOR_R, P.blink < 25);
        if (P.active == 1 && P.blink %% 10 == 0) {
            if (Plymouth.GetCapslockState()) {
                if (!P.caps) global.CAPS_R = txt_run("err", "caps lock", SX + SW - MARGIN - 9 * FADV, LY2, 1);
                P.caps = 1;
            } else {
                P.caps = 0;
                global.CAPS_R = NULL;
            }
        }
    }
    if (P.err > 0) {
        if (!ERR_R) global.ERR_R = txt_run("err", "wrong. try again.", SX + Math.Int((SW - 17 * FADV) / 2), LY0, 1);
        P.err--;
        if (P.err < 30) run_opacity(ERR_R, P.err / 30);
        if (P.err == 0) global.ERR_R = NULL;
    }
    if (MSG.t > 0) {
        MSG.t--;
        if (MSG.t == 0) global.MSG_R = NULL;
    }
}

RMIN2 = 1;
era_begin();
for (b = 0; b < 3; b++) { B[b].px = CX + B[b].x * SCALE; B[b].py = CY - B[b].y * SCALE; }
Plymouth.SetRefreshFunction(refresh);
Plymouth.SetDisplayPasswordFunction(on_password);
Plymouth.SetDisplayQuestionFunction(on_question);
Plymouth.SetDisplayNormalFunction(on_normal);
Plymouth.SetDisplayMessageFunction(on_message);
Plymouth.SetHideMessageFunction(on_hide_message);
'''

PLYMOUTH = """[Plymouth Theme]
Name=Trisolaris
Description=Three suns: a live three-body simulation; typing nudges them, eras end when one is flung away
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/{name}
ScriptFile=/usr/share/plymouth/themes/{name}/{name}.script
"""


def ps(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build(dist):
    font = lib.lm_font()
    out = os.path.join(dist, NAME)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    t = []
    for i, r in enumerate(SUN_R):
        t.append("SRL[%d] = %d;" % (i, r))
        for b, (core, halo) in enumerate(SUNS):
            # reach 4.2 instead of 6: beyond that the corona is under 2/255, and the
            # moving sun images are what plymouthd spends most of its time on
            glow(r, core, halo, reach=4.2, fade_edge=True).save(
                os.path.join(out, "sun-%d-%d.png" % (b, r)), optimize=True)
    t.append("SRL.n = %d;" % len(SUN_R))
    for i, r in enumerate(TRAIL_R):
        t.append("TRL[%d] = %d;" % (i, r))
        for b, col in enumerate(TRAIL):
            glow(r, col, col, reach=2.6, core=0.45, halo_gain=0.4).save(
                os.path.join(out, "trail-%d-%d.png" % (b, r)), optimize=True)
    t.append("TRL.n = %d;" % len(TRAIL_R))
    star(1.0, (235, 238, 255)).save(os.path.join(out, "star-0.png"), optimize=True)
    star(1.6, (255, 244, 225)).save(os.path.join(out, "star-1.png"), optimize=True)
    star(2.4, (225, 232, 255)).save(os.path.join(out, "star-2.png"), optimize=True)
    for i, fs in enumerate(FONT_SIZES):
        for fid, col in TEXT.items():
            im, cw, ch, adv, lh = fontkit.ttf_atlas(font, fs, col, bg=BG)
            im.save(os.path.join(out, "font-%s-%d.png" % (fid, fs)), optimize=True)
        t.append("FSL[%d] = %d; FSA[%d] = %d; FSH[%d] = %d;" % (i, fs, i, adv, i, lh))
    t.append("FSL.n = %d;" % len(FONT_SIZES))
    ob = []
    for i, (name, p1, p2) in enumerate(ORBITS):
        ob.append('OB[%d].name = %s; OB[%d].p1 = %r; OB[%d].p2 = %r;' % (i, ps(name), i, p1, i, p2))
    ob.append("ON = %d;" % len(ORBITS))
    script = SCRIPT % {"lib": lib.lib_script(), "tables": "\n".join(t), "orbits": "\n".join(ob)}
    open(os.path.join(out, NAME + ".script"), "w").write(script)
    open(os.path.join(out, NAME + ".plymouth"), "w").write(PLYMOUTH.format(name=NAME))
    return out
