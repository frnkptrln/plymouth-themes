"""eca: an elementary cellular automaton, computed live at every boot."""
import os, shutil
from PIL import Image, ImageFilter
import fontkit, lib

NAME = "eca"
CELL_SIZES = (8, 12, 16, 20, 24, 32)
FONT_SIZES = (14, 17, 20, 24, 28, 34, 40)

BG = (5, 4, 4, 255)            # window background, baked into every cell
GOLD = (255, 186, 82, 255)
HOT = (255, 238, 196, 255)     # the row under the write head
COLORS = {
    "hi":  (255, 198, 110, 255),   # entry / bright
    "lo":  (156, 118, 70, 255),    # labels, system prompt
    "err": (255, 120, 92, 255),    # wrong passphrase, caps lock
}

# curated rules: (rule, init)  s = single seed, r = random row
RULES = [(30, "s"), (110, "r"), (90, "s"), (150, "s"), (18, "s"), (126, "s"),
         (22, "s"), (54, "r"), (73, "r"), (137, "r"), (106, "r"), (30, "s"), (110, "r")]


def glow_pad(cs):
    return 0


def cell_atlas(cs, color=GOLD):
    """All 256 patterns of 8 cells as one 16x16 atlas. Flat, opaque, background
    baked in: plymouth's Image.Crop premultiplies alpha twice, so anything
    translucent would come out darker and leave seams between chunks."""
    cw, ch = 8 * cs, cs
    im = Image.new("RGBA", (16 * cw, 16 * ch), BG)
    px = im.load()
    for idx in range(256):
        ox, oy = (idx % 16) * cw, (idx // 16) * ch
        for k in range(8):
            if (idx >> (7 - k)) & 1:
                for y in range(cs):
                    for x in range(cs):
                        px[ox + k * cs + x, oy + y] = color
    return im, cw, ch, 0


def ps(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


SCRIPT = r'''# =============================================================================
#  ECA — an elementary cellular automaton, computed live at every boot.
#
#  Every row is a generation. Rule and first row follow from the seed shown
#  at the bottom left, so the pattern is reproducible (except for what you
#  throw in while typing: every keystroke flips a random cell, a wrong
#  passphrase scrambles a whole band). The display is a sweep: the write head
#  moves down, older generations fade like phosphor.
#
#  Claude, October 2026 — for Frank
# =============================================================================

# exactly (5, 4, 4) — the same colour is baked into the cell and font images
Window.SetBackgroundTopColor(5.5 / 255, 4.5 / 255, 4.5 / 255);
Window.SetBackgroundBottomColor(5.5 / 255, 4.5 / 255, 4.5 / 255);

SW = Window.GetWidth();
SH = Window.GetHeight();
SX = Window.GetX();
SY = Window.GetY();
%(lib)s

# ---- seeded PRNG (Park-Miller, exact in doubles) -----------------------------
SEED = Math.Int(rnd() * 65536);
PS = SEED + 1;
fun prng() {
    global.PS = (PS * 16807) %% 2147483647;
    return PS / 2147483647;
}
HEX = "0123456789abcdef";
fun hex4(n) {
    local.s = "";
    local.i = 0;
    for (i = 0; i < 4; i++) {
        s = HEX.CharAt(n %% 16) + s;
        n = Math.Int(n / 16);
    }
    return s;
}
fun pad5(n) {
    local.s = "" + n;
    while (s.Length() < 5) s = "0" + s;
    return s;
}

# ---- geometry ---------------------------------------------------------------
%(cell_sizes)s
%(font_sizes)s
CS = CSL[0];
best = 99999;
for (i = 0; i < CSL.n; i++) {
    d = Math.Abs(CSL[i] - SH / 68);
    if (d < best) { best = d; CS = CSL[i]; G = CSG[i]; }
}
FS = FSL[0];
best = 99999;
for (i = 0; i < FSL.n; i++) {
    d = Math.Abs(FSL[i] - SH / 50);
    if (d < best) { best = d; FS = FSL[i]; FADV = FSA[i]; FLH = FSH[i]; }
}
font_load("hi",  "font-hi-"  + FS + ".png", FADV, FLH, FADV, FLH, 0);
font_load("lo",  "font-lo-"  + FS + ".png", FADV, FLH, FADV, FLH, 0);
font_load("err", "font-err-" + FS + ".png", FADV, FLH, FADV, FLH, 0);

CELLS = Image("cells-" + CS + ".png");
HOTS = Image("hot-" + CS + ".png");
CCW = 8 * CS + 2 * G;
CCH = CS + 2 * G;
NCH = Math.Int((SW + 8 * CS - 1) / (8 * CS));
NCOLS = NCH * 8;
FX = SX + Math.Int((SW - NCOLS * CS) / 2);
FOOT = Math.Int(FLH * 4.2);
NROWS = Math.Int((SH - FOOT) / CS);
FY = SY;
MARGIN = Math.Int(FADV * 2);
LY0 = SY + NROWS * CS + Math.Int(FLH * 0.8);   # footer line 1
LY1 = LY0 + FLH;                               # footer line 2
LY2 = LY1 + Math.Int(FLH * 1.15);              # footer line 3

fun chunk(idx) {
    if (!CHUNK[idx])
        global.CHUNK[idx] = CELLS.Crop((idx %% 16) * CCW, Math.Int(idx / 16) * CCH, CCW, CCH);
    return CHUNK[idx];
}
fun hot(idx) {
    if (!HOTC[idx])
        global.HOTC[idx] = HOTS.Crop((idx %% 16) * CCW, Math.Int(idx / 16) * CCH, CCW, CCH);
    return HOTC[idx];
}
CHUNK.n = 0;
HOTC.n = 0;
ROW.n = 0;

# ---- rule -------------------------------------------------------------------
%(rules)s
MODE = Plymouth.GetMode();
TITLE = "";
if (MODE == "shutdown" || MODE == "reboot") {
    RULE = 128;          # erosion: every block shrinks to nothing
    INIT = "d";
    TITLE = "halt";
    if (MODE == "reboot") TITLE = "reboot";
} else {
    k = Math.Int(prng() * RL.n);
    RULE = RL[k];
    INIT = RI[k];
}
r = RULE;
for (n = 0; n < 8; n++) { RT[n] = r %% 2; r = Math.Int(r / 2); }

for (i = 0; i < NCOLS; i++) {
    DENS = 0.5;
    if (INIT == "d") DENS = 0.965;
    if (INIT == "s") CUR[i] = 0;
    else if (prng() < DENS) CUR[i] = 1;
    else CUR[i] = 0;
}
if (INIT == "s") CUR[Math.Int(NCOLS / 2)] = 1;

fun ca_step() {
    local.i = 0;
    for (i = 0; i < NCOLS; i++)
        NXT[i] = RT[CUR[(i + NCOLS - 1) %% NCOLS] * 4 + CUR[i] * 2 + CUR[(i + 1) %% NCOLS]];
    for (i = 0; i < NCOLS; i++) global.CUR[i] = NXT[i];
}

# ---- phosphor decay: L opacity levels, only rows crossing a level change ----
L = 12;
for (k = 1; k < L; k++) {
    AGE[k] = Math.Int((k * NROWS + L - 1) / L);
    f = 1 - k / L;
    OPL[k] = 0.06 + 0.94 * f * f;
}

fun row_opacity(r, o) {
    local.j = 0;
    for (j = 0; j < NCH; j++) if (ROW[r][j]) ROW[r][j].SetOpacity(o);
}

fun draw_row(r) {
    local.j = 0;
    local.k = 0;
    local.idx = 0;
    for (j = 0; j < NCH; j++) {
        idx = 0;
        for (k = 0; k < 8; k++) idx = idx * 2 + CUR[j * 8 + k];
        if (idx == 0) {
            global.ROW[r][j] = NULL;
        } else {
            if (!ROW[r][j]) {
                global.ROW[r][j] = Sprite(hot(idx));
                ROW[r][j].SetPosition(FX + j * 8 * CS - G, FY + r * CS - G, 1);
            } else {
                ROW[r][j].SetImage(hot(idx));
            }
            ROW[r][j].SetOpacity(1);
        }
        global.RIDX[r][j] = idx;
    }
}

fun cool_row(r) {
    local.j = 0;
    for (j = 0; j < NCH; j++) if (ROW[r][j]) ROW[r][j].SetImage(chunk(RIDX[r][j]));
}
RIDX.n = 0;

HEAD = -1;
GEN = 0;
fun generation() {
    local.k = 0;
    if (GEN > 0) ca_step();
    if (HEAD >= 0) cool_row(HEAD);
    global.HEAD = (HEAD + 1) %% NROWS;
    draw_row(HEAD);
    for (k = 1; k < L; k++)
        if (AGE[k] <= GEN) row_opacity((HEAD - AGE[k] + NROWS) %% NROWS, OPL[k]);
    global.GEN++;
}

# ---- footer -----------------------------------------------------------------
LINE = Image("line.png").Scale(SW - 2 * MARGIN, 1);
LINE_S = Sprite(LINE);
LINE_S.SetPosition(SX + MARGIN, SY + NROWS * CS + Math.Int(FLH * 0.35), 3);
LINE_S.SetOpacity(0.35);

LABEL = "rule " + RULE + " · seed " + hex4(SEED);
if (TITLE != "") LABEL = TITLE + " · " + LABEL;
LABEL_R = txt_run("lo", LABEL, SX + MARGIN, LY0, 5);
GEN_SHOWN = -1;
fun draw_gen() {
    local.s = "gen " + pad5(GEN);
    global.GEN_R = txt_run("lo", s, SX + SW - MARGIN - txt_len(s) * FADV, LY0, 5);
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

fun perturb_one() {
    local.i = Math.Int(prng() * NCOLS);
    global.CUR[i] = 1 - CUR[i];
}

fun perturb_band() {
    local.a = Math.Int(prng() * NCOLS);
    local.i = 0;
    for (i = 0; i < NCOLS / 3; i++)
        if (prng() < 0.5) global.CUR[(a + i) %% NCOLS] = 1 - CUR[(a + i) %% NCOLS];
}

fun draw_entry(s) {
    local.t = txt_fit(s, Math.Int((SW - 2 * MARGIN) / FADV) - 3);
    global.ENTRY_R = txt_run("hi", "> " + t, SX + MARGIN, LY2, 6);
    global.CURSOR_R = txt_run("hi", "_", SX + MARGIN + (txt_len(t) + 2) * FADV, LY2, 6);
}

fun on_password(prompt, bullets) {
    local.s = "";
    local.i = 0;
    local.n = 0;
    if (P.active != 1) {
        if (P.answered && prompt == P.last) {
            P.err = 220;
            perturb_band();
        }
        P.active = 1;
        P.prompt = prompt;
        P.bullets = -1;
        if (prompt == "") prompt = "passphrase:";
        global.PROMPT_R = txt_run("lo", txt_fit(prompt, Math.Int((SW - 2 * MARGIN) / FADV)), SX + MARGIN, LY1, 6);
        global.MSG_R = NULL;
    }
    if (bullets > P.bullets && P.bullets >= 0) for (i = P.bullets; i < bullets; i++) perturb_one();
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
        global.PROMPT_R = txt_run("lo", txt_fit(prompt, Math.Int((SW - 2 * MARGIN) / FADV)), SX + MARGIN, LY1, 6);
    }
    draw_entry(entry);
    perturb_one();
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
    global.MSG_R = txt_run("lo", txt_fit(text, Math.Int((SW - 2 * MARGIN) / FADV)), SX + MARGIN, LY1, 6);
    MSG.t = 250;
}

fun on_hide_message(text) {
    global.MSG_R = NULL;
}

# ---- main loop --------------------------------------------------------------
GF = 5;          # frames per generation (10 generations per second)
FRAME = 0;
fun refresh() {
    local.x = 0;
    if (FRAME %% GF == 0) {
        generation();
        draw_gen();
    }
    FRAME++;
    if (P.active) {
        P.blink = (P.blink + 1) %% 50;
        if (CURSOR_R) run_opacity(CURSOR_R, P.blink < 25);
        if (P.active == 1 && P.blink %% 10 == 0) {
            if (Plymouth.GetCapslockState()) {
                if (!P.caps) global.CAPS_R = txt_run("err", "caps lock", SX + SW - MARGIN - 9 * FADV, LY2, 6);
                P.caps = 1;
            } else {
                P.caps = 0;
                global.CAPS_R = NULL;
            }
        }
    }
    if (P.err > 0) {
        if (!ERR_R) global.ERR_R = txt_run("err", "wrong. try again.", SX + Math.Int((SW - 17 * FADV) / 2), LY0, 6);
        P.err--;
        if (P.err < 30) run_opacity(ERR_R, P.err / 30);
        if (P.err == 0) global.ERR_R = NULL;
    }
    if (MSG.t > 0) {
        MSG.t--;
        if (MSG.t == 0) global.MSG_R = NULL;
    }
}

Plymouth.SetRefreshFunction(refresh);
Plymouth.SetDisplayPasswordFunction(on_password);
Plymouth.SetDisplayQuestionFunction(on_question);
Plymouth.SetDisplayNormalFunction(on_normal);
Plymouth.SetDisplayMessageFunction(on_message);
Plymouth.SetHideMessageFunction(on_hide_message);
'''

PLYMOUTH = """[Plymouth Theme]
Name=ECA
Description=An elementary cellular automaton, computed live at every boot
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/{name}
ScriptFile=/usr/share/plymouth/themes/{name}/{name}.script
"""


def build(dist):
    font = lib.lm_font()
    out = os.path.join(dist, NAME)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    cs_lines, cg = [], []
    for i, cs in enumerate(CELL_SIZES):
        im, cw, ch, g = cell_atlas(cs)
        im.save(os.path.join(out, "cells-%d.png" % cs), optimize=True)
        im, cw, ch, g = cell_atlas(cs, HOT)
        im.save(os.path.join(out, "hot-%d.png" % cs), optimize=True)
        cs_lines.append("CSL[%d] = %d; CSG[%d] = %d;" % (i, cs, i, g))
    cs_lines.append("CSL.n = %d;" % len(CELL_SIZES))
    fs_lines = []
    for i, fs in enumerate(FONT_SIZES):
        for fid, col in COLORS.items():
            im, cw, ch, adv, lh = fontkit.ttf_atlas(font, fs, col, bg=BG)
            im.save(os.path.join(out, "font-%s-%d.png" % (fid, fs)), optimize=True)
        fs_lines.append("FSL[%d] = %d; FSA[%d] = %d; FSH[%d] = %d;" % (i, fs, i, adv, i, lh))
    fs_lines.append("FSL.n = %d;" % len(FONT_SIZES))
    Image.new("RGBA", (1, 1), GOLD).save(os.path.join(out, "line.png"))
    rl = []
    for i, (r, init) in enumerate(RULES):
        rl.append('RL[%d] = %d; RI[%d] = "%s";' % (i, r, i, init))
    rl.append("RL.n = %d;" % len(RULES))
    script = SCRIPT % {
        "lib": lib.lib_script(),
        "cell_sizes": "\n".join(cs_lines),
        "font_sizes": "\n".join(fs_lines),
        "rules": "\n".join(rl),
    }
    open(os.path.join(out, NAME + ".script"), "w").write(script)
    open(os.path.join(out, NAME + ".plymouth"), "w").write(PLYMOUTH.format(name=NAME))
    return out
