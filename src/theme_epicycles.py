"""epicycles: circles riding on circles draw a key (a Fourier series)."""
import cmath
import math
import os
import shutil

from PIL import Image, ImageDraw

import art
import lib

NAME = "epicycles"
BG = (6, 7, 12)
TEXT = {"hi": (236, 232, 220, 255), "lo": (112, 116, 132, 255), "err": (255, 140, 100, 255)}
RING = (98, 116, 156)
JOINT = (170, 186, 222)
CORE = (255, 238, 196)
HALO = (255, 182, 92)
NTERMS = 64                     # Fourier terms, largest first
NRINGS = 14                     # how many of them are drawn as circles
M = 1024                        # samples of the outline
RING_R = [6 * 2 ** (j / 2) for j in range(16)]     # base ring radii in px
DOT_R = (1.6, 2.0, 2.6, 3.4, 4.4)

SCRIPT = r'''# =============================================================================
#  EPICYCLES — circles riding on circles draw a key.
#
#  Any closed curve is a sum of rotating vectors: a Fourier series. Here the
#  curve is the outline of a key, taken apart into its 64 largest terms and
#  drawn by a chain of circles, the largest first. With one circle you get a
#  circle, with three a drop, with sixteen something like a key, with all of
#  them the key. During boot the terms come in one by one. At the passphrase
#  prompt only three are left and every character brings two more; a wrong
#  passphrase throws them out again, the right one brings them all back and
#  the key is drawn clean in one go. At power-off the circles go, smallest
#  first.
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

PI = 3.14159265359;
MODE = Plymouth.GetMode();
HALT = (MODE == "shutdown" || MODE == "reboot");

# ---- text ---------------------------------------------------------------------
IDS[0] = "hi"; IDS[1] = "lo"; IDS[2] = "err"; IDS.n = 3;
lm_load(IDS, SH / 52);
prompt_bottom(SX + SW / 2, SW * 0.9);
PR.hi = "hi"; PR.lo = "lo"; PR.err = "err";
MARGIN = Math.Int(FADV * 2);

# ---- geometry -----------------------------------------------------------------
# the key is about 1.55 units wide and 0.6 high; the chain reaches further out
SCL = SW * 0.33;
if (SCL > (PR.y0 - SY) * 0.62) SCL = (PR.y0 - SY) * 0.62;
CX = SX + SW / 2;
CY = SY + (PR.y0 - FLH - SY) / 2 + SCL * 0.04;

NT = %(nterms)d;
for (j = 0; j < NT; j++) {
    AR[j] = TR_[j] * SCL;
    AI[j] = TI_[j] * SCL;
    W[j] = 0;
    WT[j] = 0;
}

# ---- rings and joints ----------------------------------------------------------
NR = %(nrings)d;
fun ring_image(r) {
    local.j = 0;
    while (j < RRL.n - 1 && RRL[j] < r) j++;
    local.img = Image("ring-" + j + ".png");
    local.s = img.GetWidth() * r / RRL[j];
    return img.Scale(Math.Int(s), Math.Int(s));
}
JIMG = Image("joint.png");
JH = JIMG.GetWidth() / 2;
for (j = 0; j < NR; j++) {
    RIMG[j] = ring_image(Math.Sqrt(AR[j] * AR[j] + AI[j] * AI[j]));
    RS[j] = Sprite(RIMG[j]);
    RH[j] = RIMG[j].GetWidth() / 2;
    RS[j].SetOpacity(0);
    JS[j] = Sprite(JIMG);
    JS[j].SetOpacity(0);
}

# ---- trail ----------------------------------------------------------------------
DR = nearest(DRL, SH / 410);
for (i = 0; i < DRL.n; i++) if (DRL[i] == DR) DI = i;
DOT = Image("dot-" + DI + ".png");
DH = DOT.GetWidth() / 2;
NTR = 1100;
L = 7;
for (i = 0; i < NTR; i++) {
    TRS[i] = Sprite(DOT);
    TRS[i].SetPosition(-100, -100, 5);
    TRS[i].SetOpacity(0);
}
for (k = 1; k < L; k++) {
    AGE[k] = Math.Int((k * NTR + L - 1) / L);
    f = 1 - k / L;
    OPL[k] = 0.04 + 0.96 * f * f;
}
RING_I = 0;

fun trail_point(x, y) {
    local.k = 0;
    TRS[RING_I].SetPosition(x - DH, y - DH, 5);
    TRS[RING_I].SetOpacity(1);
    for (k = 1; k < L; k++) TRS[(RING_I - AGE[k] + NTR) %% NTR].SetOpacity(OPL[k]);
    global.RING_I = (RING_I + 1) %% NTR;
}

# ---- the series -------------------------------------------------------------------
TFIG = 9;                      # seconds for one pass round the figure
SUB = 2;                       # tip positions per frame
DT = 2 * PI / (TFIG * 50 * SUB);
TT = 0;                        # parameter, 0 .. 2 pi
for (j = 0; j < NT; j++) {
    CR[j] = Math.Cos(FK[j] * DT);
    CI[j] = Math.Sin(FK[j] * DT);
    QR[j] = 1;
    QI[j] = 0;
}
FASTN = 0;                     # sub-steps left at double speed (after Enter)
X = CX;
Y = CY;
JX[0] = 0;                     # chain positions for the rings (globals)
JY[0] = 0;

fun resync() {
    local.j = 0;
    for (j = 0; j < NT; j++) {
        QR[j] = Math.Cos(FK[j] * TT);
        QI[j] = Math.Sin(FK[j] * TT);
    }
}

# move every term one sub-step and return the tip; with joints = 1 also
# remember the chain for the rings
fun substep(joints) {
    local.j = 0;
    local.x = 0;
    local.y = 0;
    local.w = 0;
    local.qr = 0;
    for (j = 0; j < NT; j++) {
        qr = QR[j];
        QR[j] = qr * CR[j] - QI[j] * CI[j];
        QI[j] = qr * CI[j] + QI[j] * CR[j];
        w = W[j];
        if (joints && j < NR) { JX[j] = x; JY[j] = y; }
        if (w > 0) {
            x = x + w * (AR[j] * QR[j] - AI[j] * QI[j]);
            y = y + w * (AR[j] * QI[j] + AI[j] * QR[j]);
        }
    }
    global.TT = TT + DT;
    if (TT > 2 * PI) global.TT = TT - 2 * PI;
    global.X = CX + x;
    global.Y = CY - y;
}

fun weights() {
    local.j = 0;
    local.w = 0;
    for (j = 0; j < NT; j++) {
        w = W[j];
        if (w != WT[j]) {
            w = w + (WT[j] - w) * 0.12;
            if (Math.Abs(w - WT[j]) < 0.01) w = WT[j];
            W[j] = w;
        }
    }
}

fun rings(half) {
    local.j = 0;
    local.o = 0;
    for (j = half; j < NR; j = j + 2) {
        o = W[j];
        if (o > 0.02) {
            RS[j].SetPosition(CX + JX[j] - RH[j], CY - JY[j] - RH[j], 2);
            RS[j].SetOpacity(0.5 * o);
            JS[j].SetPosition(CX + JX[j] - JH, CY - JY[j] - JH, 3);
            JS[j].SetOpacity(0.8 * o);
        } else {
            RS[j].SetOpacity(0);
            JS[j].SetOpacity(0);
        }
    }
}

# ---- how many terms -----------------------------------------------------------------
NA = 0;                        # terms switched on
fun set_terms(n) {
    local.j = 0;
    if (n < 0) n = 0;
    if (n > NT) n = NT;
    global.NA = n;
    for (j = 0; j < NT; j++) WT[j] = (j < n);
}

# ---- readout --------------------------------------------------------------------------
SHOWN = "";
fun readout() {
    local.s = "fourier series · " + NA + " of " + NT + " terms";
    if (s == SHOWN) return;
    global.SHOWN = s;
    global.READ_R = txt_run("lo", s, SX + MARGIN, SY + Math.Int(FLH * 0.8), 50);
}

# ---- passphrase hooks -------------------------------------------------------------------
MODE_T = "boot";               # boot, prompt, open, night
fun hook_prompt() { global.MODE_T = "prompt"; set_terms(3); }
fun hook_key(n) { set_terms(3 + 2 * n); }
fun hook_erase(n) { set_terms(3 + 2 * n); }
fun hook_wrong() { global.MODE_T = "prompt"; set_terms(3); }
fun hook_enter() {
    local.i = 0;
    local.j = 0;
    # the old trail goes out, every term is there at once, and the key is
    # drawn clean in one pass at double speed
    global.MODE_T = "open";
    set_terms(NT);
    for (j = 0; j < NT; j++) W[j] = 1;
    for (i = 0; i < NTR; i++) TRS[i].SetOpacity(0);
    global.FASTN = Math.Int(TFIG * 50 * SUB * 1.04);
}
fun hook_question() { }

# ---- main loop ----------------------------------------------------------------------------
FRAME = 0;
if (HALT) {
    MODE_T = "night";
    set_terms(NT);
    for (j = 0; j < NT; j++) W[j] = 1;
    if (MODE == "reboot") NIGHT_R = pr_line("lo", "see you soon.", PR.y1);
    else NIGHT_R = pr_line("lo", "good night.", PR.y1);
}

fun refresh() {
    local.u = 0;
    local.s = 0;
    global.FRAME++;
    if (MODE_T == "boot" && FRAME %% 8 == 0 && NA < NT) set_terms(NA + 1);
    if (MODE_T == "night" && FRAME > 60 && FRAME %% 4 == 0 && NA > 0) set_terms(NA - 1);
    weights();
    substep(0);
    trail_point(X, Y);
    if (FASTN > 0) {
        substep(0);
        trail_point(X, Y);
        substep(0);
        trail_point(X, Y);
        global.FASTN = FASTN - 3;
    }
    substep(1);
    trail_point(X, Y);
    rings(FRAME %% 2);
    if (FRAME %% 200 == 0) resync();
    if (FRAME %% 10 == 0) readout();
    prompt_tick();
}

# three circles are there from the start, so the pen never sets out from the centre
if (!HALT) { set_terms(3); W[0] = 1; W[1] = 1; W[2] = 1; }
readout();
prompt_setup();
Plymouth.SetRefreshFunction(refresh);
'''

PLYMOUTH = """[Plymouth Theme]
Name=Epicycles
Description=Circles riding on circles draw a key: a Fourier series that sharpens as you type
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/{name}
ScriptFile=/usr/share/plymouth/themes/{name}/{name}.script
"""


# ---------------------------------------------------------------------------
# the key and its Fourier series
# ---------------------------------------------------------------------------
def arc(cx, cy, r, a0, a1, step=0.02):
    n = max(2, int(abs(a1 - a0) / step))
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n))
            for i in range(n + 1)]


def key_outline():
    """A key (bow left, bit right, teeth down), y up. The hole in the bow is
    joined to the outline through a thin slit on the left, so one closed
    path draws both."""
    B = (-0.55, 0.0)
    Ro, Ri = 0.30, 0.13
    hs = 0.045
    t0 = math.asin(hs / Ro)
    xb = B[0] + Ro * math.cos(t0)
    sl = 0.012
    do = math.asin(sl / Ro)
    di = math.asin(sl / Ri)
    P = [(xb, hs), (-0.24, hs), (-0.24, 0.08), (-0.18, 0.08), (-0.18, hs), (0.70, hs)]
    P += [(0.70, -0.30), (0.64, -0.30), (0.64, -0.22), (0.60, -0.22), (0.60, -0.30),
          (0.55, -0.30), (0.55, -0.18), (0.50, -0.18), (0.50, -0.30), (0.42, -0.30), (0.42, -hs)]
    P += [(-0.18, -hs), (-0.18, -0.08), (-0.24, -0.08), (-0.24, -hs), (xb, -hs)]
    P += arc(B[0], B[1], Ro, -t0, -math.pi + do)
    P += arc(B[0], B[1], Ri, -math.pi + di, math.pi - di)
    P += arc(B[0], B[1], Ro, math.pi - do, t0)
    return P


def resample(P, n):
    seg = [math.dist(P[i], P[(i + 1) % len(P)]) for i in range(len(P))]
    L = sum(seg)
    out = []
    i = 0
    acc = 0.0
    for m in range(n):
        s = L * m / n
        while acc + seg[i] < s:
            acc += seg[i]
            i += 1
        u = (s - acc) / seg[i] if seg[i] else 0
        a, b = P[i], P[(i + 1) % len(P)]
        out.append(complex(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u))
    c = sum(out) / n
    return [z - c for z in out]


def series(nterms):
    z = resample(key_outline(), M)
    terms = []
    K = 3 * nterms
    for k in range(-K, K + 1):
        if k == 0:
            continue
        c = sum(z[n] * cmath.exp(-2j * math.pi * k * n / M) for n in range(M)) / M
        terms.append((k, c))
    terms.sort(key=lambda t: (-abs(t[1]), t[0]))
    return terms[:nterms]


def ring_image(r):
    """A thin circle of radius r px, antialiased (drawn 4x and reduced)."""
    S = 4
    size = int(math.ceil(2 * r + 6)) | 1
    big = Image.new("L", (size * S, size * S), 0)
    d = ImageDraw.Draw(big)
    c = size * S / 2
    w = 1.3 * S
    d.ellipse((c - r * S - w / 2, c - r * S - w / 2, c + r * S + w / 2, c + r * S + w / 2), outline=255,
              width=int(round(w)))
    a = big.resize((size, size), Image.LANCZOS)
    im = Image.new("RGBA", (size, size), RING + (0,))
    im.putalpha(a)
    return im


def build(dist):
    out = os.path.join(dist, NAME)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    t = []
    for j, (k, c) in enumerate(series(NTERMS)):
        t.append("FK[%d] = %d; TR_[%d] = %.6f; TI_[%d] = %.6f;" % (j, k, j, c.real, j, c.imag))
    for j, r in enumerate(RING_R):
        ring_image(r).save(os.path.join(out, "ring-%d.png" % j), optimize=True)
        t.append("RRL[%d] = %.3f;" % (j, r))
    t.append("RRL.n = %d;" % len(RING_R))
    for i, r in enumerate(DOT_R):
        art.glow(r, CORE, HALO, reach=4.5, core=0.4, halo_gain=0.9).save(
            os.path.join(out, "dot-%d.png" % i), optimize=True)
        t.append("DRL[%d] = %s;" % (i, r))
    t.append("DRL.n = %d;" % len(DOT_R))
    art.glow(2.2, JOINT, JOINT, reach=2.5, core=0.6, halo_gain=0.3).save(os.path.join(out, "joint.png"), optimize=True)
    t.append(lib.lm_fonts(out, TEXT, BG + (255,)))
    bg = ["%.6f" % ((c + 0.5) / 255) for c in BG]
    script = SCRIPT % {"lib": lib.lib_script(), "prompt": lib.prompt_script(), "tables": "\n".join(t),
                       "bgr": bg[0], "bgg": bg[1], "bgb": bg[2], "nterms": NTERMS, "nrings": NRINGS}
    open(os.path.join(out, NAME + ".script"), "w").write(script)
    open(os.path.join(out, NAME + ".plymouth"), "w").write(PLYMOUTH.format(name=NAME))
    return out
