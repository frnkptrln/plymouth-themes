"""cloud-chamber: particle tracks condensing in supersaturated vapour."""
import math
import os
import random
import shutil

from PIL import Image, ImageDraw, ImageFilter

import art
import lib

NAME = "cloud-chamber"
BG = (4, 5, 7)
TEXT = {"hi": (230, 234, 238, 255), "lo": (108, 114, 122, 255), "err": (255, 150, 112, 255)}
KS = (0.55, 0.75, 1.0, 1.35, 2.0)        # image scale classes, picked by screen height / 1080
MIST = (236, 240, 244)
SS = 4                                   # supersampling of the track images

SCRIPT = r'''# =============================================================================
#  CLOUD CHAMBER — particle tracks condensing in supersaturated vapour.
#
#  Charged particles leave a trail of ions; vapour condenses on them and the
#  path shows up as a line of droplets, then diffuses away. Short thick tracks
#  are alpha particles (from radon in the air, or from the small source at
#  the lower left), thin winding ones are electrons, curling up as they slow
#  down in the magnetic field, long straight ones are cosmic muons.
#  Every keystroke sends a particle through, a wrong passphrase is a cosmic
#  ray shower, the right one a rare V: a neutral particle decaying into two.
#  At power-off the chamber warms up and the tracks thin out.
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

# ---- chamber and images -----------------------------------------------------------
K = nearest(KSL, SH / 1080);
for (i = 0; i < KSL.n; i++) if (KSL[i] == K) KI = i;
CX0 = SX;
CX1 = SX + SW;
CY0 = SY + Math.Int(FLH * 2.2);
CY1 = PR.y0 - FLH;
SEGL = 11 * K;               # electron path step in px

# image ids: 0 electron segment, 1 proton segment, 2 muon strip, 3..5 alpha tracks
NAMES[0] = "seg-e"; NAMES[1] = "seg-p"; NAMES[2] = "strip-mu";
NAMES[3] = "alpha-0"; NAMES[4] = "alpha-1"; NAMES[5] = "alpha-2";
for (i = 0; i < 6; i++) {
    SHARP[i] = Image(NAMES[i] + "-" + KI + ".png");
    SOFTI[i] = Image(NAMES[i] + "-soft-" + KI + ".png");
    HALF[i] = SHARP[i].GetWidth() / 2;
}
MU_STEP = MUL[KI];           # spacing of the muon strips along the line
ALPHA_LEN[0] = AL0[KI]; ALPHA_LEN[1] = AL1[KI]; ALPHA_LEN[2] = AL2[KI];

# the source: a small needle at the lower left, alphas fan out from its tip
SRC = Sprite(Image("source-" + KI + ".png"));
SRC_X = CX0 + Math.Int(SW * 0.07);
SRC_Y = CY1 - Math.Int((CY1 - CY0) * 0.16);
SRC.SetPosition(SRC_X - SRC.GetImage().GetWidth() / 2, SRC_Y - SRC.GetImage().GetHeight() / 2, 6);
TIP_X = SRC_X + SRCTX[KI];
TIP_Y = SRC_Y + SRCTY[KI];

# ---- drizzle: droplets that rain out of the vapour ---------------------------------
DROP = Image("drop-" + KI + ".png");
DH = DROP.GetWidth() / 2;
ND = Math.Int(SW * SH / 80000);
if (ND > 40) ND = 40;
for (i = 0; i < ND; i++) {
    DZ[i].s = Sprite(DROP);
    DZ[i].x = CX0 + rnd() * SW;
    DZ[i].y = CY0 + rnd() * (CY1 - CY0);
    DZ[i].v = (0.25 + 0.35 * rnd()) * K;
    DZ[i].o = 0.15 + 0.35 * rnd();
    DZ[i].s.SetOpacity(DZ[i].o);
    DZ[i].s.SetPosition(DZ[i].x - DH, DZ[i].y - DH, 3);
}

fun drizzle() {
    local.i = 0;
    for (i = 0; i < ND; i++) {
        DZ[i].y = DZ[i].y + DZ[i].v * 3;
        DZ[i].x = DZ[i].x + (rnd() - 0.5) * K;
        if (DZ[i].y > CY1) {
            DZ[i].y = CY0;
            DZ[i].x = CX0 + rnd() * SW;
            if (HALT && T > 4) DZ[i].o = DZ[i].o * 0.5;
            DZ[i].s.SetOpacity(DZ[i].o);
        }
        DZ[i].s.SetPosition(DZ[i].x - DH, DZ[i].y - DH, 3);
    }
}

# ---- tracks -----------------------------------------------------------------------
MAXT = 72;
for (k = 0; k < MAXT; k++) ON[k] = 0;
TR[0].n = 0;                 # globals, so the functions below write into them
FADE[1] = 0.5; FADE[2] = 0.3; FADE[3] = 0.16; FADE[4] = 0.07; FADE[5] = 0;
NA = 0; NB = 0; NM = 0;
T = 0;
FRAME = 0;

fun slot() {
    local.k = 0;
    for (k = 0; k < MAXT; k++) if (!ON[k]) return k;
    return -1;
}

fun inside(x, y) {
    return (x > CX0 && x < CX1 && y > CY0 && y < CY1);
}

# light comes from the left: tracks on the right are a little dimmer
fun light(x) {
    local.g = 0.74 + 0.26 * (1 - (x - SX) / SW);
    if (HALT) g = g * (0.35 + 0.65 * Math.Max(0, 1 - T / 7));
    return g;
}

fun track_begin(k, kind, img, hold, g) {
    TR[k] = NULL;
    TR[k].n = 0;
    TR[k].kind = kind;
    TR[k].img = img;
    TR[k].age = 0;
    TR[k].hold = hold;
    TR[k].g = g;
    ON[k] = 1;
}

# a winding track made of short segments (electrons, the V's daughters)
fun path_track(x, y, a, len, curv, noise, img, g) {
    local.k = slot();
    local.s = 0;
    local.e = 0;
    local.nx = 0;
    local.ny = 0;
    local.n = 0;
    if (k < 0) return;
    track_begin(k, "seg", img, 32 + Math.Int(rnd() * 12), g);
    while (s < len) {
        e = 1 - s / len;
        a = a + curv * SEGL / (e + 0.12) + (rnd() - 0.5) * noise / (e + 0.35);
        nx = x + Math.Cos(a) * SEGL;
        ny = y + Math.Sin(a) * SEGL;
        if (!inside(nx, ny)) break;
        TR[k].sp[n] = Sprite(SHARP[img].Rotate(a));
        TR[k].sp[n].SetPosition((x + nx) / 2 - HALF[img], (y + ny) / 2 - HALF[img], 10);
        TR[k].sp[n].SetOpacity(0.45 * g);
        TR[k].ang[n] = a;
        n++;
        x = nx;
        y = ny;
        s = s + SEGL;
    }
    TR[k].n = n;
    if (n == 0) { TR[k] = NULL; ON[k] = 0; }
}

fun electron(x, y, a, len) {
    local.c = (0.0012 + 0.0022 * rnd()) / K;
    if (rnd() < 0.5) c = 0 - c;
    path_track(x, y, a, len, c, 0.10, 0, light(x));
    global.NB++;
}

fun alpha(x, y, a) {
    local.k = slot();
    local.v = Math.Int(rnd() * 3);
    local.len = ALPHA_LEN[v];
    local.mx = x + Math.Cos(a) * len / 2;
    local.my = y + Math.Sin(a) * len / 2;
    if (k < 0) return;
    if (!inside(x + Math.Cos(a) * len, y + Math.Sin(a) * len)) {
        a = a + PI;
        mx = x + Math.Cos(a) * len / 2;
        my = y + Math.Sin(a) * len / 2;
    }
    track_begin(k, "line", 3 + v, 44 + Math.Int(rnd() * 14), light(x));
    TR[k].ang0 = a;
    TR[k].sp[0] = Sprite(SHARP[3 + v].Rotate(a));
    TR[k].sp[0].SetPosition(mx - HALF[3 + v], my - HALF[3 + v], 10);
    TR[k].sp[0].SetOpacity(0.45 * TR[k].g);
    TR[k].n = 1;
    global.NA++;
}

# Liang-Barsky: the part of the line x + t (c, s) inside the chamber
fun muon(x, y, a) {
    local.k = slot();
    local.c = Math.Cos(a);
    local.s = Math.Sin(a);
    local.t0 = -100000;
    local.t1 = 100000;
    local.t = 0;
    local.n = 0;
    local.img = 0;
    if (k < 0) return;
    if (Math.Abs(c) > 0.0001) {
        t = (CX0 - x) / c; if (c > 0) t0 = Math.Max(t0, t); else t1 = Math.Min(t1, t);
        t = (CX1 - x) / c; if (c > 0) t1 = Math.Min(t1, t); else t0 = Math.Max(t0, t);
    }
    if (Math.Abs(s) > 0.0001) {
        t = (CY0 - y) / s; if (s > 0) t0 = Math.Max(t0, t); else t1 = Math.Min(t1, t);
        t = (CY1 - y) / s; if (s > 0) t1 = Math.Min(t1, t); else t0 = Math.Max(t0, t);
    }
    if (t1 - t0 < MU_STEP) return;
    track_begin(k, "line", 2, 28 + Math.Int(rnd() * 10), 0.85 * light(x));
    TR[k].ang0 = a;
    img = SHARP[2].Rotate(a);
    t = t0 + MU_STEP / 2;
    while (t < t1 - MU_STEP / 3) {
        TR[k].sp[n] = Sprite(img);
        TR[k].sp[n].SetPosition(x + c * t - HALF[2], y + s * t - HALF[2], 10);
        TR[k].sp[n].SetOpacity(0.45 * TR[k].g);
        n++;
        t = t + MU_STEP;
    }
    TR[k].n = n;
    global.NM++;
    # now and then the muon knocks an electron loose: a short curly delta ray
    if (rnd() < 0.35) {
        t = t0 + (t1 - t0) * (0.2 + 0.6 * rnd());
        electron(x + c * t, y + s * t, a + (rnd() - 0.5) * 2.2, (60 + 90 * rnd()) * K);
    }
}

fun soften(k) {
    local.j = 0;
    local.img = 0;
    if (TR[k].kind == "line") {
        img = SOFTI[TR[k].img].Rotate(TR[k].ang0);
        for (j = 0; j < TR[k].n; j++) TR[k].sp[j].SetImage(img);
    } else {
        for (j = 0; j < TR[k].n; j++) TR[k].sp[j].SetImage(SOFTI[TR[k].img].Rotate(TR[k].ang[j]));
    }
}

fun tracks_tick() {
    local.k = 0;
    local.j = 0;
    local.a = 0;
    local.o = -1;
    local.h = 0;
    for (k = 0; k < MAXT; k++) {
        if (!ON[k]) continue;
        a = TR[k].age + 1;
        TR[k].age = a;
        h = TR[k].hold;
        o = -1;
        if (a == 3) o = 1;
        else if (a == h) { soften(k); o = 0.72; }
        else if (a > h && (a - h) %% 14 == 0) {
            o = FADE[(a - h) / 14];
            if (o <= 0) { TR[k] = NULL; ON[k] = 0; continue; }
        }
        if (o >= 0) for (j = 0; j < TR[k].n; j++) TR[k].sp[j].SetOpacity(o * TR[k].g);
    }
}

# ---- what happens -------------------------------------------------------------------
fun rand_point() {
    local.p.x = CX0 + SW * (0.08 + 0.84 * rnd());
    local.p.y = CY0 + (CY1 - CY0) * (0.08 + 0.84 * rnd());
    return p;
}

fun spawn_alpha() {
    local.p = rand_point();
    if (rnd() < 0.5) alpha(TIP_X, TIP_Y, SRCA - 1.1 + 2.2 * rnd());
    else alpha(p.x, p.y, rnd() * 2 * PI);
}

fun spawn_electron() {
    local.p = rand_point();
    electron(p.x, p.y, rnd() * 2 * PI, (180 + 380 * rnd()) * K);
}

fun spawn_muon() {
    local.p = rand_point();
    muon(p.x, p.y, rnd() * PI);
}

fun spawn_any() {
    local.u = rnd();
    if (u < 0.3) spawn_alpha();
    else if (u < 0.68) spawn_electron();
    else spawn_muon();
}

# a cosmic ray shower: many nearly parallel tracks at once
fun shower() {
    local.a = rnd() * PI;
    local.i = 0;
    local.n = 9 + Math.Int(rnd() * 7);
    local.d = 0;
    local.cx = CX0 + SW / 2;
    local.cy = (CY0 + CY1) / 2;
    local.nx = 0 - Math.Sin(a);
    local.ny = Math.Cos(a);
    for (i = 0; i < n; i++) {
        d = (rnd() - 0.5) * Math.Min(SW, CY1 - CY0) * 1.1;
        if (rnd() < 0.72) muon(cx + nx * d, cy + ny * d, a + (rnd() - 0.5) * 0.06);
        else electron(cx + nx * d, cy + ny * d, a + (rnd() - 0.5) * 0.3, (220 + 300 * rnd()) * K);
    }
}

# the right passphrase: a V, a neutral particle (no track) decays into two
fun vee() {
    local.x = CX0 + SW * (0.3 + 0.4 * rnd());
    local.y = CY0 + (CY1 - CY0) * (0.3 + 0.4 * rnd());
    local.a = rnd() * 2 * PI;
    local.g = light(x);
    # opposite charges: the two daughters curve away from each other
    path_track(x, y, a - 0.32, (260 + 80 * rnd()) * K, -0.0007 / K, 0.03, 1, g);
    path_track(x, y, a + 0.38, (300 + 120 * rnd()) * K, 0.0032 / K, 0.06, 0, g);
    global.NB++;
    global.NA++;
}

RATE = 1.1;                  # tracks per second
if (HALT) RATE = 1.4;

fun events() {
    local.r = RATE;
    if (P.active == 1) r = 0.7;
    if (HALT) r = RATE * Math.Max(0, 1 - T / 6);
    if (rnd() < r / 50) spawn_any();
}

# ---- readout ------------------------------------------------------------------------
SHOWN = "";
fun readout() {
    local.s = "cloud chamber · B 0.4 T · alpha " + NA + " · electron " + NB + " · muon " + NM;
    if (s == SHOWN) return;
    global.SHOWN = s;
    global.READ_R = txt_run("lo", s, SX + MARGIN, SY + Math.Int(FLH * 0.8), 50);
}

if (HALT) {
    if (MODE == "reboot") NIGHT_R = pr_line("lo", "see you soon.", PR.y1);
    else NIGHT_R = pr_line("lo", "good night.", PR.y1);
}

# ---- passphrase hooks -----------------------------------------------------------------
fun hook_prompt() { }
fun hook_key(n) {
    local.u = rnd();
    if (u < 0.45) spawn_electron();
    else if (u < 0.75) spawn_alpha();
    else spawn_muon();
}
fun hook_erase(n) {
    local.p = rand_point();
    electron(p.x, p.y, rnd() * 2 * PI, (90 + 90 * rnd()) * K);
}
fun hook_wrong() { shower(); }
fun hook_enter() { vee(); }
fun hook_question() { }

# ---- main loop ------------------------------------------------------------------------
fun refresh() {
    global.FRAME++;
    global.T = T + 0.02;
    events();
    tracks_tick();
    if (FRAME %% 3 == 0) drizzle();
    if (FRAME %% 10 == 0) readout();
    prompt_tick();
}

# the chamber is already running when the picture appears
spawn_muon();
spawn_alpha();
spawn_electron();
readout();
prompt_setup();
Plymouth.SetRefreshFunction(refresh);
'''

PLYMOUTH = """[Plymouth Theme]
Name=Cloud Chamber
Description=Particle tracks condensing in a cloud chamber: alphas, electrons and cosmic muons
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/{name}
ScriptFile=/usr/share/plymouth/themes/{name}/{name}.script
"""


# ---------------------------------------------------------------------------
# track images: droplets drawn along a horizontal line, supersampled
# ---------------------------------------------------------------------------
def droplets(size, x0, x1, thick, spacing, rng, alpha_fn=lambda u: 1.0, jitter=0.32, gap=0.0):
    """size: canvas px (output). Draws a droplet trail from x0 to x1 at mid height.
    thick(u) gives the trail thickness at u in [0,1] (u from x0 to x1)."""
    S = size * SS
    im = Image.new("RGBA", (S, S), MIST + (0,))
    lay = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(lay)
    cy = S / 2
    x = x0
    while x < x1:
        u = (x - x0) / max(1e-6, (x1 - x0))
        t = thick(u)
        if rng.random() >= gap:
            # a few droplets spread across the trail
            for _ in range(max(1, int(t / 1.2))):
                yy = cy + rng.gauss(0, t * jitter) * SS
                xx = x * SS + rng.uniform(-0.5, 0.5) * spacing * SS
                r = max(0.45, t * rng.uniform(0.18, 0.34)) * SS
                a = int(255 * alpha_fn(u) * rng.uniform(0.55, 1.0))
                d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=a)
        x += spacing * rng.uniform(0.7, 1.3)
    lay = lay.filter(ImageFilter.GaussianBlur(0.35 * SS))
    im.putalpha(lay)
    return im.resize((size, size), Image.LANCZOS)


def soft_of(im, k):
    """Diffused version: wider, fainter, same canvas."""
    a = im.split()[3].filter(ImageFilter.GaussianBlur(1.6 * k + 0.6))
    a = a.point(lambda v: min(255, int(v * 1.35)))
    out = Image.new("RGBA", im.size, MIST + (0,))
    out.putalpha(a)
    return out


def odd(v):
    v = int(math.ceil(v))
    return v | 1


def source_image(k):
    """A small metal needle pointing up-right; returns image and tip offset."""
    size = odd(56 * k)
    S = size * SS
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ang = math.radians(-32)
    c = S / 2
    L = 22 * k * SS
    w = 2.6 * k * SS
    ux, uy = math.cos(ang), math.sin(ang)
    nx, ny = -uy, ux
    p0 = (c - ux * L, c - uy * L)
    p1 = (c + ux * L, c + uy * L)
    poly = [(p0[0] + nx * w, p0[1] + ny * w), (p1[0] + nx * w * 0.6, p1[1] + ny * w * 0.6),
            (p1[0] - nx * w * 0.6, p1[1] - ny * w * 0.6), (p0[0] - nx * w, p0[1] - ny * w)]
    d.polygon(poly, fill=(92, 96, 104, 255))
    d.line([(p0[0] + nx * w * 0.4, p0[1] + ny * w * 0.4), (p1[0] + nx * w * 0.25, p1[1] + ny * w * 0.25)],
           fill=(150, 156, 166, 255), width=max(1, int(0.8 * k * SS)))
    # holder at the back end
    d.ellipse((p0[0] - 4 * k * SS, p0[1] - 4 * k * SS, p0[0] + 4 * k * SS, p0[1] + 4 * k * SS), fill=(54, 56, 62, 255))
    im = im.resize((size, size), Image.LANCZOS)
    tip = ((p1[0] - c) / SS, (p1[1] - c) / SS)
    return im, tip, ang


def build(dist):
    out = os.path.join(dist, NAME)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    t = []
    for ki, k in enumerate(KS):
        rng = random.Random(1000 + ki)
        t.append("KSL[%d] = %s;" % (ki, k))
        # electron segment: path step 11k, drawn a little longer so joints close
        size = odd(20 * k)
        L = 13.5 * k
        seg = droplets(size, size / 2 - L / 2, size / 2 + L / 2, lambda u: 2.6 * k, 1.1 * k, rng)
        # proton segment (V decay): thicker
        segp = droplets(size, size / 2 - L / 2, size / 2 + L / 2, lambda u: 3.6 * k, 1.2 * k, rng)
        # muon strip: thin, beaded, sparse droplets
        msize = odd(140 * k)
        ML = 132 * k
        strip = droplets(msize, msize / 2 - ML / 2, msize / 2 + ML / 2, lambda u: 2.2 * k, 1.9 * k, rng,
                         alpha_fn=lambda u: 0.95, gap=0.08)
        t.append("MUL[%d] = %s;" % (ki, round(124 * k, 2)))
        imgs = {"seg-e": seg, "seg-p": segp, "strip-mu": strip}
        # alpha tracks: thick, dense, swelling towards the end (Bragg peak)
        for v, la in enumerate((128, 152, 178)):
            La = la * k
            asize = odd(La + 30 * k)
            img = droplets(asize, asize / 2 - La / 2, asize / 2 + La / 2,
                           lambda u: (4.2 + 4.8 * u ** 2.2) * k, 0.9 * k, rng, jitter=0.26)
            imgs["alpha-%d" % v] = img
            t.append("AL%d[%d] = %s;" % (v, ki, round(La, 2)))
        for name, img in imgs.items():
            img.save(os.path.join(out, "%s-%d.png" % (name, ki)), optimize=True)
            soft_of(img, k).save(os.path.join(out, "%s-soft-%d.png" % (name, ki)), optimize=True)
        art.blob(1.2 * k, MIST, alpha=0.9).save(os.path.join(out, "drop-%d.png" % ki), optimize=True)
        src, tip, ang = source_image(k)
        src.save(os.path.join(out, "source-%d.png" % ki), optimize=True)
        t.append("SRCTX[%d] = %s; SRCTY[%d] = %s;" % (ki, round(tip[0], 2), ki, round(tip[1], 2)))
    t.append("KSL.n = %d;" % len(KS))
    t.append("SRCA = %s;" % round(math.radians(-32), 5))
    t.append(lib.lm_fonts(out, TEXT, BG + (255,)))
    bg = ["%.6f" % ((c + 0.5) / 255) for c in BG]
    script = SCRIPT % {"lib": lib.lib_script(), "prompt": lib.prompt_script(), "tables": "\n".join(t),
                       "bgr": bg[0], "bgg": bg[1], "bgb": bg[2]}
    open(os.path.join(out, NAME + ".script"), "w").write(script)
    open(os.path.join(out, NAME + ".plymouth"), "w").write(PLYMOUTH.format(name=NAME))
    return out
