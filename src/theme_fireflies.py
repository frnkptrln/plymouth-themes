"""fireflies: a swarm of coupled oscillators (Kuramoto model) that learns to flash in unison."""
import math
import os
import random
import shutil

from PIL import Image, ImageDraw

import art
import lib

NAME = "fireflies"
BG = (3, 5, 6)
TEXT = {"hi": (226, 240, 196, 255), "lo": (104, 118, 100, 255), "err": (255, 156, 96, 255)}
GLOW_R = (1.9, 2.5, 3.4, 4.5, 6.0, 8.0)     # glow radius in px, picked by screen height
CORE = (250, 255, 215)
HALO = (170, 255, 60)
AIR = (146, 166, 60)              # the air of the meadow, lit by the swarm
AIR_MAX = 0.62                    # its alpha at the ground
MEADOW_W, MEADOW_H = 1920, 284    # the silhouette is built at this size and scaled

SCRIPT = r'''# =============================================================================
#  FIREFLIES — a swarm that learns to flash in unison.
#
#  Every firefly is an oscillator with its own rhythm and flashes when its
#  phase comes round. They pull on each other's phases (Kuramoto model, mean
#  field): with weak coupling the field twinkles at random, once the coupling
#  passes a critical value the swarm locks and flashes together. The coupling
#  ramps up during boot, so you watch the transition happen.
#  They fly over a meadow that stays dark until they light it: the air
#  glows with what flashes at the same moment, so a few flies at random
#  leave it black, and a swarm in unison brings the grass out against the
#  light for a moment, once a flash.
#  Typing knocks a few out of step, a wrong passphrase startles the whole
#  swarm, Enter pulls it into tight unison. At power-off the coupling fades
#  and the fireflies go dark one by one.
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

TWO_PI = 6.28318530718;
MODE = Plymouth.GetMode();
HALT = (MODE == "shutdown" || MODE == "reboot");

# ---- text ---------------------------------------------------------------------
IDS[0] = "hi"; IDS[1] = "lo"; IDS[2] = "err"; IDS.n = 3;
lm_load(IDS, SH / 52);
prompt_bottom(SX + SW / 2, SW * 0.9);
PR.hi = "hi"; PR.lo = "lo"; PR.err = "err";
MARGIN = Math.Int(FADV * 2);

# ---- the swarm ------------------------------------------------------------------
GR = nearest(GRL, SH / 240);
for (i = 0; i < GRL.n; i++) if (GRL[i] == GR) GI = i;
IMG_NEAR = Image("fly-" + GI + ".png");
GJ = GI - 1;
if (GJ < 0) GJ = 0;
IMG_FAR = Image("fly-" + GJ + ".png");
HN = IMG_NEAR.GetWidth() / 2;
HF = IMG_FAR.GetWidth() / 2;

N = Math.Int(SW * SH / 13000);
if (N < 60) N = 60;
if (N > 200) N = 200;
X0 = SX + SW * 0.04;
X1 = SX + SW * 0.96;
Y0 = SY + SH * 0.10;
Y1 = PR.y0 - FLH * 1.5;
STEPPX = SH / 110;            # how far a firefly moves between two flashes

# ---- the meadow: as dark as the night, until the swarm lights the air --------------
GROUND = Y1 + Math.Int(FLH * 0.8);
MH = Math.Int((GROUND - Y0) * 0.34);
GH = Math.Int((GROUND - Y0) * 0.80);
AIRSP = Sprite(Image("air.png").Scale(SW, GH));
AIRSP.SetPosition(SX, GROUND - GH, 1);
AIRSP.SetOpacity(0);
AIR_OP = 0;
MEADOW = Sprite(Image("meadow.png").Scale(SW, MH));
MEADOW.SetPosition(SX, GROUND - MH, 4);

# approximately normal: Irwin-Hall with four uniforms
fun gauss() {
    return (rnd() + rnd() + rnd() + rnd() - 2) * 1.732;
}

GSUM = 0;
for (i = 0; i < N; i++) {
    FAR[i] = (rnd() < 0.4);
    v = rnd();
    # the far ones fly behind the grass, the near ones in front of it
    if (FAR[i]) { v = v * 0.75; GAIN[i] = 0.55; SPR[i] = Sprite(IMG_FAR); H[i] = HF; ZF[i] = 3; }
    else { v = 0.3 + 0.7 * (1 - v * v); GAIN[i] = 1; SPR[i] = Sprite(IMG_NEAR); H[i] = HN; ZF[i] = 5; }
    GSUM = GSUM + GAIN[i];
    FX[i] = X0 + rnd() * (X1 - X0);
    FY[i] = Y0 + v * (Y1 - Y0);
    SPR[i].SetPosition(FX[i] - H[i], FY[i] - H[i], ZF[i]);
    SPR[i].SetOpacity(0);
    TH[i] = rnd() * TWO_PI;
    W[i] = TWO_PI * (0.92 + 0.085 * gauss());
    FL[i] = -1;               # flash age in steps, -1 = dark
    LAST[i] = 9999;           # seconds after which this one stays dark (power-off)
}

# flash envelope, one entry per two frames
OP[0] = 1; OP[1] = 0.82; OP[2] = 0.62; OP[3] = 0.44; OP[4] = 0.29;
OP[5] = 0.17; OP[6] = 0.09; OP[7] = 0.04; OP[8] = 0; OP.n = 9;

DT = 0.04;                    # simulated seconds per step (one step every two frames)
CO[0] = 0;                    # cos/sin of the phases, globals so step() writes them
SI[0] = 0;
K = 0;                        # coupling
KMAX = 2.8;
KT0 = 0;                      # time the current ramp started
RAMP = 9;                     # seconds to full coupling
TIGHT = 0;                    # Enter: pull into tight unison
R = 0;
C = 0;
S = 0;
T = 0;                        # seconds since start
FRAME = 0;

if (HALT) {
    # start in unison, let the coupling go and the fireflies go out
    for (i = 0; i < N; i++) {
        TH[i] = 0.25 * rnd();
        W[i] = TWO_PI * (0.92 + 0.16 * gauss());
        LAST[i] = 1.2 + 6 * rnd() * rnd();
    }
    K = 4;
}

fun flash(i) {
    FL[i] = 0;
    # between two flashes it has flown a little
    FX[i] = FX[i] + (rnd() - 0.5) * 2 * STEPPX;
    FY[i] = FY[i] + (rnd() - 0.55) * 1.4 * STEPPX;
    if (FX[i] < X0) FX[i] = X0 + STEPPX;
    if (FX[i] > X1) FX[i] = X1 - STEPPX;
    if (FY[i] < Y0) FY[i] = Y0 + STEPPX;
    if (FY[i] > Y1) FY[i] = Y1 - STEPPX;
    SPR[i].SetPosition(FX[i] - H[i], FY[i] - H[i], ZF[i]);
}

fun coupling() {
    local.u = 0;
    if (HALT) {
        global.K = K * 0.985;
        return;
    }
    if (TIGHT) { global.K = K + (9 - K) * 0.08; return; }
    u = (T - KT0) / RAMP;
    if (u < 0) u = 0;
    if (u > 1) u = 1;
    global.K = KMAX * u * u * (3 - 2 * u);
}

fun step() {
    local.i = 0;
    local.c = 0;
    local.s = 0;
    local.cs = 0;
    local.sn = 0;
    local.th = 0;
    for (i = 0; i < N; i++) {
        c = Math.Cos(TH[i]);
        s = Math.Sin(TH[i]);
        CO[i] = c;
        SI[i] = s;
        cs = cs + c;
        sn = sn + s;
    }
    cs = cs / N;
    sn = sn / N;
    global.C = cs;
    global.S = sn;
    global.R = Math.Sqrt(cs * cs + sn * sn);
    # K r sin(psi - th) = K (S cos th - C sin th)
    for (i = 0; i < N; i++) {
        th = TH[i] + DT * (W[i] + K * (sn * CO[i] - cs * SI[i]));
        if (th >= TWO_PI) {
            th = th - TWO_PI;
            if (T < LAST[i]) flash(i);
        }
        if (th < 0) th = th + TWO_PI;
        TH[i] = th;
    }
}

fun envelopes() {
    local.i = 0;
    local.a = 0;
    local.f = 0;
    for (i = 0; i < N; i++) {
        a = FL[i];
        if (a >= 0) {
            SPR[i].SetOpacity(OP[a] * GAIN[i]);
            f = f + OP[a] * GAIN[i];
            a++;
            if (a >= OP.n) a = -1;
            FL[i] = a;
        }
    }
    light(f / GSUM);
}

# The air glows with what flashes now. At random a firefly is lit an eighth
# of the time, so f stays near 0.13 and the meadow dark; in unison f comes
# close to 1 once a flash.
fun light(f) {
    local.o = (f - 0.15) / 0.6;
    if (o < 0) o = 0;
    if (o > 1) o = 1;
    o = o * o;
    if (Math.Abs(o - AIR_OP) < 0.05 && !(o == 0 && AIR_OP > 0)) return;
    global.AIR_OP = o;
    AIRSP.SetOpacity(o);
}

# ---- readout ----------------------------------------------------------------------
fun dec2(v) {
    local.p = Math.Int(v * 100 + 0.5);
    local.r = p %% 100;
    local.s = "" + r;
    if (r < 10) s = "0" + s;
    return Math.Int(p / 100) + "." + s;
}

SHOWN = "";
fun readout() {
    local.s = "kuramoto · N " + N + " · K " + dec2(K) + " · r " + dec2(R);
    if (s == SHOWN) return;
    global.SHOWN = s;
    global.READ_R = txt_run("lo", s, SX + MARGIN, SY + Math.Int(FLH * 0.8), 50);
}

if (HALT) {
    if (MODE == "reboot") NIGHT_R = pr_line("lo", "see you soon.", PR.y1);
    else NIGHT_R = pr_line("lo", "good night.", PR.y1);
}

# ---- passphrase hooks ---------------------------------------------------------------
fun kick(frac, amp) {
    local.i = 0;
    for (i = 0; i < N; i++)
        if (rnd() < frac) TH[i] = TH[i] + (rnd() - 0.5) * 2 * amp;
}

fun hook_prompt() { global.TIGHT = 0; }
fun hook_key(n) { kick(0.13, 1.7); }
fun hook_erase(n) { kick(0.06, 1.0); }
fun hook_enter() { global.TIGHT = 1; }
fun hook_question() { }
fun hook_wrong() {
    local.i = 0;
    # startled: everyone flashes at once, then the rhythm is gone
    global.TIGHT = 0;
    for (i = 0; i < N; i++) {
        TH[i] = rnd() * TWO_PI;
        flash(i);
    }
    global.KT0 = T;
    global.K = 0;
}

# ---- main loop ----------------------------------------------------------------------
fun refresh() {
    global.FRAME++;
    if (FRAME %% 2 == 0) {
        global.T = T + DT;
        coupling();
        step();
    } else {
        envelopes();
    }
    if (FRAME %% 25 == 1) readout();
    prompt_tick();
}

prompt_setup();
Plymouth.SetRefreshFunction(refresh);
'''

PLYMOUTH = """[Plymouth Theme]
Name=Fireflies
Description=Coupled oscillators (Kuramoto model) that learn to flash in unison
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/{name}
ScriptFile=/usr/share/plymouth/themes/{name}/{name}.script
"""


def meadow(w, h, seed=7, ss=3):
    """Grass and foxtails as a silhouette in the colour of the night: the
    alpha channel carries the shapes."""
    rnd = random.Random(seed)
    W, H = w * ss, h * ss
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    ground = int(H * 0.86)

    def gy(x):                    # the ground line, gently rolling
        return ground - (math.sin(x / W * 5.1) * 0.025 + math.sin(x / W * 13.7 + 1) * 0.012) * H

    pts = [(0, H)] + [(x, gy(x)) for x in range(0, W + 1, 8 * ss)] + [(W, H)]
    d.polygon(pts, fill=255)

    def blade(x0, y0, hgt, lean, width):
        left, right = [], []
        n = 18
        for k in range(n + 1):
            t = k / n
            x = x0 + lean * hgt * t * t
            y = y0 - hgt * t
            wd = width * (1 - t) ** 0.9 + 0.4 * ss
            left.append((x - wd / 2, y))
            right.append((x + wd / 2, y))
        d.polygon(left + right[::-1], fill=255)
        return x0 + lean * hgt, y0 - hgt

    # every stem starts below the ground line, so no light shows between them
    for _ in range(int(w * 1.1)):
        x0 = rnd.uniform(-10, W + 10)
        hgt = H * (0.10 + 0.32 * rnd.random() ** 1.8)
        blade(x0, gy(x0) + 6 * ss, hgt, rnd.uniform(-0.35, 0.35), rnd.uniform(1.6, 3.2) * ss)
    for _ in range(int(w / 60)):
        x0 = rnd.uniform(0, W)
        hgt = H * rnd.uniform(0.45, 0.78)
        lean = rnd.uniform(-0.12, 0.12)
        tx, ty = blade(x0, gy(x0) + 6 * ss, hgt, lean, 1.4 * ss)
        L = H * rnd.uniform(0.06, 0.10)
        ang = math.atan2(-hgt, lean * hgt)
        for k in range(14):
            t = k / 13
            cx = tx + math.cos(ang) * L * t * 0.95
            cy = ty + math.sin(ang) * L * t * 0.95
            r = (1.2 + 2.2 * math.sin(math.pi * min(1, t * 1.1))) * ss
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    # sixteen steps of alpha are plenty for an edge, and halve the file
    m = m.resize((w, h), Image.LANCZOS).point(lambda v: round(v / 17) * 17)
    im = Image.new("RGBA", (w, h), BG + (0,))
    im.putalpha(m)
    return im


def air(h):
    """A band of light, nothing at the top, AIR_MAX at the ground."""
    im = Image.new("RGBA", (1, h), AIR + (0,))
    for y in range(h):
        t = y / (h - 1)
        a = AIR_MAX * (t * t * (3 - 2 * t)) ** 1.6
        im.putpixel((0, y), AIR + (int(round(255 * a)),))
    return im


def build(dist):
    out = os.path.join(dist, NAME)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    meadow(MEADOW_W, MEADOW_H).save(os.path.join(out, "meadow.png"), optimize=True)
    air(256).save(os.path.join(out, "air.png"), optimize=True)
    t = []
    for i, r in enumerate(GLOW_R):
        t.append("GRL[%d] = %s;" % (i, r))
        art.glow(r, CORE, HALO, reach=9, core=0.35, halo_gain=2.2).save(
            os.path.join(out, "fly-%d.png" % i), optimize=True)
    t.append("GRL.n = %d;" % len(GLOW_R))
    t.append(lib.lm_fonts(out, TEXT, BG + (255,)))
    bg = ["%.6f" % ((c + 0.5) / 255) for c in BG]
    script = SCRIPT % {"lib": lib.lib_script(), "prompt": lib.prompt_script(), "tables": "\n".join(t),
                       "bgr": bg[0], "bgg": bg[1], "bgb": bg[2]}
    open(os.path.join(out, NAME + ".script"), "w").write(script)
    open(os.path.join(out, NAME + ".plymouth"), "w").write(PLYMOUTH.format(name=NAME))
    return out
