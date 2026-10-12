"""waterfall: the 433 MHz band on a software radio, spectrum and waterfall."""
import math
import os
import random
import shutil

from PIL import Image, ImageDraw, ImageFilter

import lib

NAME = "waterfall"
BG = (4, 6, 12)
TEXT = {"hi": (226, 236, 240, 255), "lo": (96, 116, 128, 255), "err": (255, 120, 90, 255),
        "ax": (120, 150, 170, 255)}
NOISE_N = 32
HOT_N = 12
SPAN = (433.05, 434.79)          # MHz, the LPD/ISM band

# waterfall palette: intensity 0..1 -> colour
STOPS = [(0.00, (4, 6, 14)), (0.18, (8, 18, 52)), (0.35, (16, 48, 110)), (0.55, (24, 120, 168)),
         (0.72, (110, 210, 190)), (0.86, (250, 236, 120)), (1.00, (255, 255, 236))]


def pal(v):
    v = max(0.0, min(1.0, v))
    for (a, ca), (b, cb) in zip(STOPS, STOPS[1:]):
        if v <= b:
            u = (v - a) / (b - a)
            return tuple(int(ca[i] + (cb[i] - ca[i]) * u) for i in range(3))
    return STOPS[-1][1]


SCRIPT = r'''# =============================================================================
#  WATERFALL — the 433 MHz band on a software radio.
#
#  Above: the spectrum, below: the waterfall, frequency across, time going
#  down (here as a sweep: the write line runs down and older rows dim).
#  On the band: a beacon carrier, a cheap transmitter drifting with its
#  temperature, a Morse beacon sending VVV, a weather station that sends a
#  short FSK burst now and then, and a LoRa channel at 433.920 MHz.
#  Every keystroke you type goes out as a LoRa packet: eight up-chirps of
#  preamble, then data, diagonal lines across the channel. The right
#  passphrase is answered by the gateway with down-chirps, a wrong one by a
#  jammer across the whole band. At power-off the stations go quiet and the
#  receiver switches off.
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
IDS[0] = "hi"; IDS[1] = "lo"; IDS[2] = "err"; IDS[3] = "ax"; IDS.n = 4;
lm_load(IDS, SH / 52);
prompt_bottom(SX + SW / 2, SW * 0.9);
PR.hi = "hi"; PR.lo = "lo"; PR.err = "err";
MARGIN = Math.Int(FADV * 2);

# ---- layout ---------------------------------------------------------------------
F0 = %(f0)s;
F1 = %(f1)s;
WX0 = SX + Math.Int(SW * 0.05);
WX1 = SX + Math.Int(SW * 0.95);
WW = WX1 - WX0;
SPY0 = SY + Math.Int(FLH * 2.4);             # spectrum
SPY1 = SPY0 + Math.Int(SH * 0.16);
AXY = SPY1 + Math.Int(FLH * 0.35);            # frequency axis
WY0 = AXY + Math.Int(FLH * 1.6);              # waterfall
WY1 = PR.y0 - FLH;
RH = Math.Max(2, Math.Int(SH / 540));         # row height
NROWS = Math.Int((WY1 - WY0) / RH);
WY1 = WY0 + NROWS * RH;

fun fx(f) { return WX0 + (f - F0) / (F1 - F0) * WW; }

# ---- images ---------------------------------------------------------------------------
for (i = 0; i < NOISE_N; i++) NOISE[i] = Image("noise-" + i + ".png").Scale(WW, RH);
for (i = 0; i < HOT_N; i++) HOTN[i] = Image("hot-" + i + ".png").Scale(WW, RH);
CW = Math.Max(3, Math.Int(SW / 400));
CARRIER = Image("carrier.png").Scale(CW * 3, RH);
CARRIER_W = Image("carrier-weak.png").Scale(CW * 3, RH);
LORA_BW = fx(F0 + 0.25) - fx(F0);             # 250 kHz in px
SYM = 12;                                      # rows per chirp
CHIRP = Image("chirp.png").Scale(Math.Int(LORA_BW / SYM) + CW * 2, RH);
CHW = CHIRP.GetWidth();
FSK = Image("carrier.png").Scale(CW * 2, RH);

# ---- frame: axis, ticks, passband marker -------------------------------------------------
fun axis() {
    local.f = 433.1;
    local.s = "";
    local.x = 0;
    local.k = 0;
    while (f < F1) {
        x = fx(f);
        TICK[k] = Sprite(Image("tick.png").Scale(1, Math.Int(FLH * 0.3)));
        TICK[k].SetPosition(x, SPY1, 6);
        s = "" + f;
        if (s.Length() < 7) s = s + "0";
        if (s.Length() < 7) s = s + "0";
        AXL[k] = txt_run("ax", s, x - Math.Int(txt_len(s) * FADV / 2), AXY, 50);
        k++;
        f = f + 0.2;
    }
}
TICK.n = 0;
AXL.n = 0;
axis();
UNIT_R = txt_run("ax", "MHz", WX1 - 3 * FADV, AXY, 50);

LORA_F = 433.92;
LX0 = fx(LORA_F - 0.125);
PASS = Sprite(Image("pass.png").Scale(Math.Int(LORA_BW), WY1 - SPY0));
PASS.SetPosition(LX0, SPY0, 6);
PASS_L = txt_run("ax", "433.920 · LoRa 250 kHz", LX0, SPY0 - FLH, 50);

# ---- spectrum: bars of 16 heights ---------------------------------------------------------
NB = 128;
BW_ = WW / NB;
BAR_IMG = Image("bar.png");
for (i = 0; i < 16; i++) BARS[i] = BAR_IMG.Scale(Math.Max(1, Math.Int(BW_) - 1), Math.Max(1, Math.Int((SPY1 - SPY0) * (i + 1) / 16)));
for (i = 0; i < NB; i++) {
    BS_[i] = Sprite(BARS[0]);
    BL[i] = 0;
    BS_[i].SetPosition(WX0 + Math.Int(i * BW_), SPY1 - BARS[0].GetHeight(), 4);
}
fun bar(i, lev) {
    if (lev < 0) lev = 0;
    if (lev > 15) lev = 15;
    lev = Math.Int(lev);
    if (lev == BL[i]) return;
    BL[i] = lev;
    BS_[i].SetImage(BARS[lev]);
    BS_[i].SetPosition(WX0 + Math.Int(i * BW_), SPY1 - BARS[lev].GetHeight(), 4);
}
PK.n = 0;                     # peaks for the spectrum this row: x, level

# ---- the stations ---------------------------------------------------------------------
T = 0;                        # seconds
ROWN = 0;                     # rows written
HEAD = 0;
QUIET = 0;                    # power-off: how far the stations have gone quiet
JAM = 0;                      # rows of jamming left
# Morse VVV: 1 on, 0 off, one entry per unit (a unit is 3 rows)
MORSE = "1010101110001010101110001010101110000000";
# LoRa packets: a queue of chirps; dir 1 up, -1 down; shift 0..1 (data)
LQ.n = 0;
LQI = 0;
LROW = 0;                     # row within the current chirp
fun lora_packet(dir, nd) {
    local.k = 0;
    for (k = 0; k < 8; k++) { LQ[LQ.n].dir = dir; LQ[LQ.n].sh = 0; LQ.n++; }
    for (k = 0; k < nd; k++) { LQ[LQ.n].dir = dir; LQ[LQ.n].sh = rnd(); LQ.n++; }
}
WX_NEXT = 3;                  # weather station: next burst (s)
BG_LORA = 9;                  # some other LoRa device: next packet (s)

ROWSP.n = 0;                  # sprites of each waterfall row

fun seg(r, img, x, w) {
    local.n = ROWSP[r].n;
    ROWSP[r].sp[n] = Sprite(img);
    ROWSP[r].sp[n].SetPosition(x - w / 2, WY0 + r * RH, 5);
    ROWSP[r].n = n + 1;
}

fun peak(x, lev) {
    PKX[PK.n] = x;
    PKL[PK.n] = lev;
    PK.n++;
}

fun write_row() {
    local.r = HEAD;
    local.x = 0;
    local.u = 0;
    local.c = NULL;
    local.k = 0;
    local.on = 1;
    ROWSP[r] = NULL;
    ROWSP[r].n = 0;
    PK.n = 0;
    if (JAM > 0) {
        seg(r, HOTN[Math.Int(rnd() * HOT_N)], WX0 + WW / 2, WW);
        global.JAM--;
    } else {
        seg(r, NOISE[Math.Int(rnd() * NOISE_N)], WX0 + WW / 2, WW);
    }
    # beacon carrier
    if (QUIET < 1) { x = fx(433.40); seg(r, CARRIER, x, CW * 3); peak(x, 13); }
    # drifting transmitter, on most of the time
    if (QUIET < 2 && (T %% 23) < 17) {
        x = fx(434.20 + 0.035 * Math.Sin(T / 6));
        seg(r, CARRIER_W, x, CW * 3);
        peak(x, 9);
    }
    # Morse beacon
    if (QUIET < 3) {
        u = Math.Int(ROWN / 3) %% MORSE.Length();
        if (MORSE.CharAt(u) == "1") { x = fx(433.65); seg(r, CARRIER, x, CW * 3); peak(x, 12); }
    }
    # weather station: two-tone FSK burst
    if (T >= WX_NEXT && QUIET < 2) {
        if (T < WX_NEXT + 1.3) {
            if (rnd() < 0.5) x = fx(434.43); else x = fx(434.47);
            seg(r, FSK, x, CW * 2);
            peak(x, 11);
        } else {
            global.WX_NEXT = T + 5 + rnd() * 6;
        }
    }
    # another LoRa device on a different channel
    if (T >= BG_LORA && QUIET < 2) {
        global.BG_LORA = T + 14 + rnd() * 10;
        global.BG_ROWS = SYM * 6;
        global.BG_X = fx(434.62 - 0.0625);
    }
    if (BG_ROWS > 0) {
        u = ((SYM * 6 - BG_ROWS) %% SYM) / SYM;
        x = BG_X + u * LORA_BW / 2;
        seg(r, CHIRP, x, CHW);
        peak(x, 8);
        global.BG_ROWS--;
    }
    # our LoRa channel
    if (LQI < LQ.n) {
        c = LQ[LQI];
        u = LROW / SYM + c.sh;
        u = u - Math.Int(u);
        if (c.dir < 0) u = 1 - u;
        x = LX0 + u * (LORA_BW - CHW) + CHW / 2;
        seg(r, CHIRP, x, CHW);
        peak(x, 14);
        global.LROW++;
        if (LROW >= SYM) {
            global.LROW = 0;
            global.LQI++;
            if (LQI >= LQ.n) { global.LQ = NULL; global.LQ.n = 0; global.LQI = 0; }
        }
    }
    global.HEAD = (HEAD + 1) %% NROWS;
    global.ROWN++;
    WLINE.SetPosition(WX0, WY0 + HEAD * RH, 7);
    fade();
}

# older rows dim: a few opacity levels by age
L = 5;
for (k = 1; k < L; k++) {
    AGE[k] = Math.Int(k * NROWS / L);
    f = 1 - k / L;
    OPL[k] = 0.25 + 0.75 * f;
}
fun fade() {
    local.k = 0;
    local.r = 0;
    local.j = 0;
    for (k = 1; k < L; k++) {
        r = (HEAD - 1 - AGE[k] + 2 * NROWS) %% NROWS;
        for (j = 0; j < ROWSP[r].n; j++) ROWSP[r].sp[j].SetOpacity(OPL[k]);
    }
    # the row the head is about to overwrite is cleared, so the sweep shows
    ROWSP[HEAD] = NULL;
    ROWSP[HEAD].n = 0;
}

WLINE = Sprite(Image("tick.png").Scale(WW, 1));
WLINE.SetOpacity(0.6);

fun spectrum() {
    local.i = 0;
    local.k = 0;
    local.lev = 0;
    local.d = 0;
    local.base = 2;
    if (JAM > 0) base = 9;
    if (QUIET >= 3) base = 1;
    for (i = 0; i < NB; i++) LEV[i] = base + rnd() * 2.2;
    for (k = 0; k < PK.n; k++) {
        i = Math.Int((PKX[k] - WX0) / BW_);
        for (d = -2; d <= 2; d++) {
            if (i + d >= 0 && i + d < NB) {
                lev = PKL[k] - Math.Abs(d) * 4 + rnd();
                if (lev > LEV[i + d]) LEV[i + d] = lev;
            }
        }
    }
    for (i = 0; i < NB; i++) bar(i, LEV[i]);
}
LEV[0] = 0;
PKX[0] = 0;
PKL[0] = 0;

# ---- readout -------------------------------------------------------------------------------
SHOWN = "";
fun readout() {
    local.s = "sdr · 433.050 - 434.790 MHz · rbw 1 kHz · rows " + ROWN;
    if (QUIET >= 4) s = "sdr · receiver off";
    if (s == SHOWN) return;
    global.SHOWN = s;
    global.READ_R = txt_run("lo", s, SX + MARGIN, SY + Math.Int(FLH * 0.8), 50);
}

# ---- passphrase hooks ------------------------------------------------------------------------
fun hook_prompt() { }
fun hook_key(n) {
    # one packet per keystroke; while one is on the air, the next one waits in line
    if (LQ.n - LQI < 40) lora_packet(1, 3);
}
fun hook_erase(n) { if (LQ.n - LQI < 40) lora_packet(1, 1); }
fun hook_wrong() {
    global.JAM = 55;
    global.LQ = NULL;
    global.LQ.n = 0;
    global.LQI = 0;
    global.LROW = 0;
}
fun hook_enter() {
    # the gateway answers: down-chirps
    global.LQ = NULL;
    global.LQ.n = 0;
    global.LQI = 0;
    global.LROW = 0;
    lora_packet(-1, 6);
}
fun hook_question() { }

if (HALT) {
    if (MODE == "reboot") NIGHT_R = pr_line("lo", "see you soon.", PR.y1);
    else NIGHT_R = pr_line("lo", "good night.", PR.y1);
}

# ---- main loop ------------------------------------------------------------------------------
FRAME = 0;
BG_ROWS = 0;
BG_X = 0;
fun refresh() {
    global.FRAME++;
    global.T = T + 0.02;
    if (HALT) global.QUIET = Math.Int(T / 1.2);
    if (FRAME %% 2 == 0 && QUIET < 5) write_row();
    if (FRAME %% 3 == 0) spectrum();
    if (FRAME %% 10 == 0) readout();
    prompt_tick();
}

# the radio has been running for a while: fill the waterfall with history
T = 0 - NROWS * 0.04;
WX_NEXT = T + 2;
BG_LORA = T + 5;
for (i = 0; i < NROWS; i++) {
    write_row();
    T = T + 0.04;
}
T = 0;
WX_NEXT = 3;
BG_LORA = 9;
readout();
prompt_setup();
Plymouth.SetRefreshFunction(refresh);
'''

PLYMOUTH = """[Plymouth Theme]
Name=Waterfall
Description=The 433 MHz band on a software radio; your keystrokes go out as LoRa chirps
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/{name}
ScriptFile=/usr/share/plymouth/themes/{name}/{name}.script
"""


def noise_row(rng, hot=False):
    W = 1024
    vals = []
    v = 0.0
    for x in range(W):
        # correlated noise, with occasional faint specks
        v = 0.6 * v + 0.4 * rng.gauss(0, 1)
        base = 0.22 + 0.07 * v
        if hot:
            base = 0.62 + 0.16 * v + 0.12 * rng.random()
        elif rng.random() < 0.012:
            base += rng.uniform(0.08, 0.2)
        vals.append(base)
    im = Image.new("RGBA", (W, 1))
    im.putdata([pal(b) + (255,) for b in vals])
    return im


def segment(w, core, edge, alpha=1.0):
    """A short horizontal glow: bright core, soft edges, 1 px high."""
    im = Image.new("RGBA", (w, 1))
    px = []
    c = (w - 1) / 2
    for x in range(w):
        d = abs(x - c) / (w / 2)
        a = max(0.0, 1 - d ** 1.6)
        v = core if d < 0.3 else edge
        px.append(pal(v) + (int(255 * a * alpha),))
    im.putdata(px)
    return im


def build(dist):
    out = os.path.join(dist, NAME)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    rng = random.Random(433)
    for i in range(NOISE_N):
        noise_row(rng).save(os.path.join(out, "noise-%d.png" % i), optimize=True)
    for i in range(HOT_N):
        noise_row(rng, hot=True).save(os.path.join(out, "hot-%d.png" % i), optimize=True)
    segment(15, 0.98, 0.8).save(os.path.join(out, "carrier.png"))
    segment(15, 0.78, 0.6).save(os.path.join(out, "carrier-weak.png"))
    segment(48, 0.95, 0.82).save(os.path.join(out, "chirp.png"))
    Image.new("RGBA", (4, 4), (120, 170, 200, 255)).save(os.path.join(out, "tick.png"))
    Image.new("RGBA", (4, 4), (90, 200, 220, 255)).save(os.path.join(out, "bar.png"))
    pas = Image.new("RGBA", (16, 16), (140, 200, 230, 22))
    d = ImageDraw.Draw(pas)
    d.line([(0, 0), (0, 15)], fill=(140, 200, 230, 90))
    d.line([(15, 0), (15, 15)], fill=(140, 200, 230, 90))
    pas.save(os.path.join(out, "pass.png"))
    t = [lib.lm_fonts(out, TEXT, BG + (255,)), "NOISE_N = %d;" % NOISE_N, "HOT_N = %d;" % HOT_N]
    bg = ["%.6f" % ((c + 0.5) / 255) for c in BG]
    script = SCRIPT % {"lib": lib.lib_script(), "prompt": lib.prompt_script(), "tables": "\n".join(t),
                       "bgr": bg[0], "bgg": bg[1], "bgb": bg[2], "f0": SPAN[0], "f1": SPAN[1]}
    open(os.path.join(out, NAME + ".script"), "w").write(script)
    open(os.path.join(out, NAME + ".plymouth"), "w").write(PLYMOUTH.format(name=NAME))
    return out
