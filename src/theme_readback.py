"""readback: the boot written down. The unit names systemd reports are poured
into the letters of the machine's name, in a field of noise."""
import os
import shutil

from PIL import Image, ImageDraw, ImageFont

import fontkit
import lib

NAME = "readback"
BG = (12, 11, 10)
INK = (236, 230, 220, 255)
ACC = (222, 140, 104, 255)       # only for what concerns the person at the keyboard
LIT = (40, 37, 33)               # the ground of the letters of the name
LH_FACTOR = 1.3                  # line height of the character grid, in font sizes
NAME_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789-"
NAME_HEIGHTS = (6, 7, 8, 10, 12, 14, 17, 20, 24, 28, 32)   # rows the name may be tall
ASPECT = 0.41                    # width / height of a grid cell (7/18 .. 13/31)

SCRIPT = r'''# =============================================================================
#  READBACK — the boot, written down.
#
#  Nothing on this screen is made up. Before the passphrase the screen is
#  noise: that is what an encrypted disk is without its key (the noise only
#  stands in for it, Plymouth cannot read the disk). Every unit systemd has
#  started is reported to Plymouth by name, and the names are written, in
#  that order, into the letters of this machine's name, until the name stands
#  there made of the names of its own parts. What no longer fits runs on,
#  dimmer, into the noise; whatever is still noise at the end, this boot did
#  not need. Of your passphrase the theme learns only how many characters you
#  typed, and says so. At power-off nothing is reported any more, and the name
#  is only an outline in the noise.
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
%(tables)s

MACHINE = "localhost";   # install.sh writes this machine's name here
MODE = Plymouth.GetMode();
HALT = (MODE == "shutdown" || MODE == "reboot");

# ---- the character grid --------------------------------------------------------
best = 99999;
for (i = 0; i < FSL.n; i++) {
    if (Math.Abs(FSL[i] - SH / 60) < best) {
        best = Math.Abs(FSL[i] - SH / 60);
        FS = FSL[i];
        FADV = FSA[i];
        FLH = FSH[i];
    }
}
font_load("ink", "font-ink-" + FS + ".png", FADV, FLH, FADV, FLH, 0);
font_load("acc", "font-acc-" + FS + ".png", FADV, FLH, FADV, FLH, 0);
font_load("lit", "font-lit-" + FS + ".png", FADV, FLH, FADV, FLH, 0);
COLS = Math.Int(SW / FADV);
ROWS = Math.Int(SH / FLH);
OX = SX + Math.Int((SW - COLS * FADV) / 2);
OY = SY + Math.Int((SH - ROWS * FLH) / 2);
N = COLS * ROWS;
BAND = ROWS - 9;                 # the bottom rows: question, answer, messages
R_PROMPT = BAND + 1;
R_PREV = BAND + 3;
R_ENTRY = BAND + 4;
R_NOTE = BAND + 6;
R_MSG = BAND + 8;

O_NOISE = 0.085;                 # opacities (the atlases are all bright)
O_QUIET = 0.04;                  # noise right around the name
O_OUTLINE = 0.45;                # the letters at power-off: their ground, faint noise
O_NEW = 1;
O_OLD = 0.85;
O_OUT_NEW = 0.32;                # text that no longer fits into the letters
O_OUT_OLD = 0.22;
O_DIM = 0.4;

# every cell is one sprite; CODE, FID and OPA remember what it shows
NOISE = "!#$%%&()*+-/0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_abcdefghijklmnopqrstuvwxyz{|}~";
NC = txt_codes(NOISE);
for (i = 0; i < N; i++) {
    NG[i] = NC[Math.Int(rnd() * NC.n)];
    G[i] = Sprite(glyph("ink", NG[i]));
    G[i].SetPosition(OX + (i %% COLS) * FADV, OY + Math.Int(i / COLS) * FLH, 1);
    G[i].SetOpacity(O_NOISE);
    CODE[i] = NG[i];
    FID[i] = "ink";
    OPA[i] = O_NOISE;
}
MASK[0] = 0;                     # cells inside the letters of the name
BT[0] = 0;                       # band cells that hold text

fun put(i, fid, code, op) {
    if (CODE[i] != code || FID[i] != fid) {
        G[i].SetImage(glyph(fid, code));
        CODE[i] = code;
        FID[i] = fid;
    }
    if (OPA[i] != op) {
        G[i].SetOpacity(op);
        OPA[i] = op;
    }
}

fun unput(i) {
    if (HALT && MASK[i]) { put(i, "lit", NG[i], O_OUTLINE); return; }
    if (QUIET[i]) put(i, "ink", NG[i], O_QUIET);
    else put(i, "ink", NG[i], O_NOISE);
}

# ---- the name, in big letters made of cells --------------------------------------
HEXV["0"] = 0; HEXV["1"] = 1; HEXV["2"] = 2; HEXV["3"] = 3; HEXV["4"] = 4;
HEXV["5"] = 5; HEXV["6"] = 6; HEXV["7"] = 7; HEXV["8"] = 8; HEXV["9"] = 9;
HEXV["a"] = 10; HEXV["b"] = 11; HEXV["c"] = 12; HEXV["d"] = 13; HEXV["e"] = 14; HEXV["f"] = 15;
HEXV["A"] = 10; HEXV["B"] = 11; HEXV["C"] = 12; HEXV["D"] = 13; HEXV["E"] = 14; HEXV["F"] = 15;
BIT[0] = 1; BIT[1] = 2; BIT[2] = 4; BIT[3] = 8;

fun bits_of(hex, n) {
    local.s = "";
    local.k = 0;
    local.v = 0;
    local.b = 0;
    for (k = 0; k * 4 < n; k++) {
        v = HEXV[hex.CharAt(k)];
        for (b = 3; b >= 0 && k * 4 + 3 - b < n; b--) {
            if (Math.Int(v / BIT[b]) %% 2) s = s + "1";
            else s = s + "0";
        }
    }
    return s;
}

fun width_of(s, hi) {
    local.w = 0;
    local.k = 0;
    local.c = "";
    for (k = 0; k < s.Length(); k++) {
        c = s.CharAt(k);
        if (GW[hi][c]) w = w + GW[hi][c];
    }
    return w;
}

# the rows of the letter box that s actually inks (no descender, no room for one)
fun ink_of(s, hi) {
    local.k = 0;
    local.c = "";
    global.R0 = 999;
    global.R1 = -1;
    for (k = 0; k < s.Length(); k++) {
        c = s.CharAt(k);
        if (GW[hi][c]) {
            if (GT[hi][c] < R0) global.R0 = GT[hi][c];
            if (GE[hi][c] > R1) global.R1 = GE[hi][c];
        }
    }
    return R1 - R0 + 1;
}

AREA = BAND - 2;                 # rows 1 .. BAND - 2 hold the name
if (width_of(MACHINE, 0) == 0) MACHINE = "localhost";
# one line, or two split at the hyphen nearest the middle: whichever is bigger
H1 = -1;
for (i = 0; i < NHL.n; i++)
    if (ink_of(MACHINE, i) <= AREA - 2 && width_of(MACHINE, i) <= COLS - 6) H1 = i;
CUT = -1;
for (k = 1; k < MACHINE.Length() - 1; k++)
    if (MACHINE.CharAt(k) == "-" &&
        (CUT < 0 || Math.Abs(k - MACHINE.Length() / 2) < Math.Abs(CUT - MACHINE.Length() / 2))) CUT = k;
LA = MACHINE.SubString(0, CUT + 1);
LB = MACHINE.SubString(CUT + 1, MACHINE.Length());
H2 = -1;
if (CUT > 0)
    for (i = 0; i < NHL.n; i++)
        if (2 * ink_of(MACHINE, i) + 1 <= AREA - 2 &&
            width_of(LA, i) <= COLS - 6 && width_of(LB, i) <= COLS - 6) H2 = i;
if (H2 > H1) {
    LINE[0] = LA;
    LINE[1] = LB;
    LINES = 2;
    HI = H2;
} else {
    # one line; a name too long even for the smallest letters is cut short
    while (H1 < 0 && MACHINE.Length() > 1) {
        MACHINE = MACHINE.SubString(0, MACHINE.Length() - 1);
        if (width_of(MACHINE, 0) <= COLS - 6) H1 = 0;
    }
    if (H1 < 0) H1 = 0;
    LINE[0] = MACHINE;
    LINES = 1;
    HI = H1;
}
NH = NHL[HI];
UH = ink_of(MACHINE, HI);        # sets R0, R1 for all lines alike
TOP = 1 + Math.Int((AREA - (LINES * UH + LINES - 1)) / 2);
SLOT.n = 0;                      # the cells of the letters, in reading order
QUIET[0] = 0;                    # the box around the name, where the noise is fainter
for (L = 0; L < LINES; L++) {
    NK = 0;
    for (k = 0; k < LINE[L].Length(); k++) {
        c = LINE[L].CharAt(k);
        if (GW[HI][c]) {
            NWK[NK] = GW[HI][c];
            NB[NK] = bits_of(GB[HI][c], NH * GW[HI][c]);
            NK++;
        }
    }
    LW = width_of(LINE[L], HI);
    NX0 = Math.Int((COLS - LW) / 2);
    NY0 = TOP + L * (UH + 1) - R0;
    for (r = R0 - 1; r <= R1 + 1; r++)
        for (x = NX0 - 2; x < NX0 + LW + 2; x++)
            if (r + NY0 >= 0 && x >= 0 && x < COLS) QUIET[(NY0 + r) * COLS + x] = 1;
    for (r = R0; r <= R1; r++) {
        x = NX0;
        for (k = 0; k < NK; k++) {
            row = NB[k].SubString(r * NWK[k], (r + 1) * NWK[k]);
            for (c = 0; c < NWK[k]; c++)
                if (row.CharAt(c) == "1") {
                    i = (NY0 + r) * COLS + x + c;
                    MASK[i] = 1;
                    SLOT[SLOT.n] = i;
                    SLOT.n++;
                }
            x = x + NWK[k];
        }
    }
}

for (i = 0; i < N; i++) if (QUIET[i]) put(i, "ink", NG[i], O_QUIET);

# ---- writing: the names systemd reports, in that order ---------------------------
QC[0] = 0;                       # queued character codes
QN = 0;
QR = 0;
SP = 0;                          # next cell inside the letters
OVP = 0;                         # next cell outside them
LIMIT = (BAND - 1) * COLS;       # text stays above the band
RING[0] = 0;                     # the cells written last, to let them age
RINGIN[0] = 0;
RINGC[0] = 0;
RN = 0;
AGE_N = 140;
WC = 0;
WIN = 0;

SUFFIX["service"] = 1; SUFFIX["socket"] = 1; SUFFIX["target"] = 1; SUFFIX["path"] = 1;
SUFFIX["timer"] = 1; SUFFIX["device"] = 1; SUFFIX["slice"] = 1; SUFFIX["scope"] = 1;
SUFFIX["mount"] = 2; SUFFIX["automount"] = 2; SUFFIX["swap"] = 2;      # these name paths

fun unhex2(h) {
    local.v = 16 * HEXV[h.CharAt(0)] + HEXV[h.CharAt(1)];
    if (v >= 32 && v < 127) return TXT.ascii.CharAt(v - 32);
    return "?";
}

# "systemd-cryptsetup@luks\x2d3f2a.service" -> "systemd-cryptsetup@luks-3f2a",
# "dev-zram0.swap" -> "/dev/zram0"; anything that is not a unit name -> ""
fun clean(s) {
    local.n = s.Length();
    local.d = -1;
    local.k = 0;
    local.kind = 0;
    local.base = "";
    local.out = "";
    local.c = "";
    for (k = n - 1; k > 0 && d < 0; k--) if (s.CharAt(k) == ".") d = k;
    if (d <= 0) return "";
    kind = SUFFIX[s.SubString(d + 1, n)];
    if (!kind) return "";
    base = s.SubString(0, d);
    for (k = 0; k < base.Length(); k++) {
        c = base.CharAt(k);
        if (c == "\\" && base.CharAt(k + 1) == "x") {
            out = out + unhex2(base.SubString(k + 2, k + 4));
            k = k + 3;
        } else if (kind == 2 && c == "-") {
            out = out + "/";
        } else {
            out = out + c;
        }
    }
    if (kind == 2 && out != "/") out = "/" + out;
    return txt_fit(out, 40);
}

fun enqueue(word) {
    local.c = txt_codes(word);
    local.k = 0;
    if (QN > 0) {
        QC[QN] = 32;
        global.QN++;
    }
    for (k = 0; k < c.n; k++) {
        QC[QN] = c[k];
        global.QN++;
    }
}

fun next_cell() {
    if (SP < SLOT.n) {
        global.WC = SLOT[SP];
        global.SP++;
        global.WIN = 1;
        return 1;
    }
    while (OVP < LIMIT && MASK[OVP]) global.OVP++;
    if (OVP >= LIMIT) return 0;
    global.WC = OVP;
    global.OVP++;
    global.WIN = 0;
    return 1;
}

fun write_code(code) {
    local.j = 0;
    local.slot = RN %% AGE_N;
    if (!next_cell()) return;
    if (WIN) {
        if (code == 32) put(WC, "lit", 250, O_NEW);      # a dot between two names
        else put(WC, "lit", code, O_NEW);
    } else {
        if (code == 32) put(WC, "ink", 32, 1);
        else put(WC, "ink", code, O_OUT_NEW);
    }
    if (RN >= AGE_N && (RINGC[slot] != 32 || RINGIN[slot])) {
        j = RING[slot];
        if (RINGIN[slot]) put(j, FID[j], CODE[j], O_OLD);
        else put(j, FID[j], CODE[j], O_OUT_OLD);
    }
    RING[slot] = WC;
    RINGIN[slot] = WIN;
    RINGC[slot] = code;
    global.RN++;
}

fun on_status(status) {
    local.w = clean(status);
    if (w != "") enqueue(w);
}

NCUR = Sprite(glyph("ink", 95));
NCUR.SetOpacity(0);
NCUR_SHOWN = 0;
fun place_cursor() {
    local.i = -1;
    if (SP < SLOT.n) i = SLOT[SP];
    else if (OVP < LIMIT) i = OVP;
    if (i < 0) { global.NCUR_OK = 0; return; }
    global.NCUR_OK = 1;
    NCUR.SetPosition(OX + (i %% COLS) * FADV, OY + Math.Int(i / COLS) * FLH, 3);
}
NCUR_OK = 1;
place_cursor();

# ---- the band: the question, your answer as far as the theme knows it -----------
BANDON = 0;
LC = 2;                          # first column of the band lines
BCUR = Sprite(glyph("acc", 95));
BCUR.SetOpacity(0);
BCUR_ON = 0;
BCUR_SHOWN = 0;

fun band_on() {
    local.i = 0;
    if (BANDON) return;
    global.BANDON = 1;
    for (i = BAND * COLS; i < N; i++) put(i, "ink", 32, 1);
}

# write s into a band row from column LC; returns the column after it
fun line(row, s, fid, op) {
    local.c = txt_codes(s);
    local.k = 0;
    local.i = row * COLS;
    for (k = 0; k < COLS; k++) {
        if (k >= LC && k - LC < c.n && k < COLS - 1) {
            put(i + k, fid, c[k - LC], op);
            BT[i + k] = (c[k - LC] != 32);
        } else {
            put(i + k, "ink", 32, 1);
            BT[i + k] = 0;
        }
    }
    return LC + c.n;
}

fun line_opacity(row, op) {
    local.k = 0;
    local.i = row * COLS;
    for (k = 0; k < COLS; k++) if (BT[i + k]) put(i + k, FID[i + k], CODE[i + k], op);
}

fun band_cursor(row, col, fid) {
    BCUR.SetImage(glyph(fid, 95));
    BCUR.SetPosition(OX + col * FADV, OY + row * FLH, 3);
    global.BCUR_ON = 1;
}

fun repeat(s, n) {
    local.out = "";
    local.k = 0;
    if (n > Math.Int((COLS - LC - 3) / 2)) n = Math.Int((COLS - LC - 3) / 2);
    for (k = 0; k < n; k++) out = out + s;
    return out;
}

P.active = 0;                    # 1 = passphrase, 2 = question
P.prompt = "";
P.last = "";
P.answered = 0;
P.bullets = -1;
P.lastn = 0;
P.caps = -1;

fun note() {
    if (P.caps == 1) { line(R_NOTE, "caps lock is on.", "acc", 0.75); return; }
    if (P.bullets <= 0) { line(R_NOTE, "", "ink", 1); return; }
    if (P.bullets == 1) line(R_NOTE, "1 character. I see how many, never which.", "ink", O_DIM);
    else line(R_NOTE, P.bullets + " characters. I see how many, never which.", "ink", O_DIM);
}

fun set_column(prompt) {
    global.LC = Math.Max(2, Math.Int((COLS - txt_len(txt_fit(prompt, COLS - 4))) / 2));
}

fun on_password(prompt, bullets) {
    local.col = 0;
    if (P.active != 1) {
        band_on();
        if (prompt == "") prompt = "passphrase:";
        set_column(prompt);
        line(R_PROMPT, txt_fit(prompt, COLS - 4), "acc", 1);
        # the same question again right after an answer: that was not it
        if (P.answered && prompt == P.last) line(R_PREV, repeat("- ", P.lastn), "acc", 0.45);
        P.active = 1;
        P.prompt = prompt;
        P.bullets = -1;
        P.caps = -1;
    }
    if (bullets != P.bullets) {
        P.bullets = bullets;
        col = line(R_ENTRY, repeat("* ", bullets), "acc", 1);
        band_cursor(R_ENTRY, col, "acc");
        note();
    }
}

fun on_question(prompt, entry) {
    local.col = 0;
    if (P.active != 2) {
        band_on();
        set_column(prompt);
        line(R_PROMPT, txt_fit(prompt, COLS - 4), "acc", 1);
        line(R_PREV, "", "ink", 1);
        line(R_NOTE, "", "ink", 1);
        P.active = 2;
    }
    col = line(R_ENTRY, txt_fit(entry, COLS - LC - 3), "acc", 1);
    band_cursor(R_ENTRY, col, "acc");
}

fun on_normal() {
    if (P.active == 1) {
        P.answered = 1;
        P.last = P.prompt;
        P.lastn = P.bullets;
    }
    if (P.active) {
        line_opacity(R_PROMPT, O_DIM);
        line_opacity(R_PREV, 0.25);
        line_opacity(R_ENTRY, O_DIM);
        line(R_NOTE, "", "ink", 1);
        global.BCUR_ON = 0;
        P.active = 0;
    }
}

MSGT = 0;
fun msg_off() {
    local.k = 0;
    if (BANDON) line(R_MSG, "", "ink", 1);
    else for (k = R_MSG * COLS; k < (R_MSG + 1) * COLS; k++) unput(k);
    global.MSGT = 0;
}

fun on_message(text) {
    line(R_MSG, txt_fit(text, COLS - LC - 2), "ink", 0.5);
    global.MSGT = 250;
}

fun on_hide_message(text) {
    msg_off();
}

# ---- power-off: nothing is reported any more ----------------------------------------
if (HALT) {
    for (k = 0; k < SLOT.n; k++) unput(SLOT[k]);
    band_on();
    LC = Math.Max(2, Math.Int((COLS - 24) / 2));
    if (MODE == "reboot") line(R_PROMPT, "reboot", "ink", O_DIM);
    else line(R_PROMPT, "power-off", "ink", O_DIM);
    band_cursor(R_ENTRY, line(R_ENTRY, "the rest is on the disk.", "ink", 1), "ink");
}

# ---- main loop -------------------------------------------------------------------------
FRAME = 0;
BLINK = 0;
fun refresh() {
    local.k = 0;
    local.m = QN - QR;
    local.show = 0;
    global.FRAME++;
    global.BLINK = (BLINK + 1) %% 50;
    if (m > 0) {
        k = 1 + Math.Int(m / 8);
        if (k > 40) k = 40;
        while (k > 0 && QR < QN) {
            write_code(QC[QR]);
            global.QR++;
            k--;
        }
        place_cursor();
    }
    show = (NCUR_OK && !P.active && !HALT && BLINK < 25);
    if (show != NCUR_SHOWN) {
        NCUR.SetOpacity(show);
        global.NCUR_SHOWN = show;
    }
    show = (BCUR_ON && BLINK < 25);
    if (show != BCUR_SHOWN) {
        BCUR.SetOpacity(show);
        global.BCUR_SHOWN = show;
    }
    if (P.active == 1 && FRAME %% 10 == 0) {
        k = 0;
        if (Plymouth.GetCapslockState()) k = 1;
        if (k != P.caps) {
            P.caps = k;
            note();
        }
    }
    if (MSGT > 0) {
        global.MSGT--;
        if (MSGT == 0) msg_off();
    }
}

Plymouth.SetRefreshFunction(refresh);
Plymouth.SetUpdateStatusFunction(on_status);
Plymouth.SetDisplayPasswordFunction(on_password);
Plymouth.SetDisplayQuestionFunction(on_question);
Plymouth.SetDisplayNormalFunction(on_normal);
Plymouth.SetDisplayMessageFunction(on_message);
Plymouth.SetHideMessageFunction(on_hide_message);
'''

PLYMOUTH = """[Plymouth Theme]
Name=Readback
Description=The boot written down: the units systemd starts fill the letters of the machine's name, in a field of noise
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/{name}
ScriptFile=/usr/share/plymouth/themes/{name}/{name}.script
"""


def grid_fonts(out):
    """Atlases of Latin Modern Mono with a tight line height, for the grid."""
    font = lib.lm_font()
    lines = []
    for i, fs in enumerate(lib.LM_SIZES):
        lh = int(round(fs * LH_FACTOR))
        for fid, col, bg in (("ink", INK, BG), ("acc", ACC, BG), ("lit", INK, LIT)):
            im, cw, ch, adv, lh2 = fontkit.ttf_atlas(font, fs, col, lh=lh, bg=bg + (255,))
            im.save(os.path.join(out, "font-%s-%d.png" % (fid, fs)), optimize=True)
        lines.append("FSL[%d] = %d; FSA[%d] = %d; FSH[%d] = %d;" % (i, fs, i, adv, i, lh2))
    lines.append("FSL.n = %d;" % len(lib.LM_SIZES))
    return "\n".join(lines)


def name_glyphs():
    """Letters for the machine's name: Latin Modern Sans Bold sampled onto the
    grid at a few heights, each glyph a hex string of its cells, row by row."""
    path = lib.lm_file("lmsans10-bold.otf", "LMSANSBOLD")
    ref = ImageFont.truetype(path, 1000)
    top = min(ref.getbbox(c)[1] for c in NAME_CHARS)
    bot = max(ref.getbbox(c)[3] for c in NAME_CHARS)
    lines = []
    for hi, h in enumerate(NAME_HEIGHTS):
        cell_h = 24                                  # supersampling
        cell_w = cell_h * ASPECT
        size = int(round(1000.0 * h * cell_h / (bot - top)))
        f = ImageFont.truetype(path, size)
        lines.append("NHL[%d] = %d;" % (hi, h))
        # small letters get a heavier stroke and a lower threshold, or thin
        # parts (the bar of a t, the top of an a) fall between the cells
        stroke = int(round(cell_h * (0.22 if h <= 10 else 0.2)))
        thr = 90 if h <= 10 else 95
        for ch in NAME_CHARS:
            cols = max(1, int(round(f.getlength(ch) / cell_w)))
            if h <= 10:
                cols += 1                            # keep small letters apart
            im = Image.new("L", (int(round(cols * cell_w)), h * cell_h), 0)
            ImageDraw.Draw(im).text((stroke * 0.5, -top * size / 1000.0), ch, font=f, fill=255,
                                    stroke_width=stroke, stroke_fill=255)
            small = im.resize((cols, h), Image.BOX)
            rows = ["".join("1" if small.getpixel((x, y)) >= thr else "0" for x in range(cols))
                    for y in range(h)]
            inked = [y for y, r in enumerate(rows) if "1" in r] or [0]
            bits = "".join(rows)
            bits += "0" * (-len(bits) % 4)
            hexs = "".join("%x" % int(bits[k:k + 4], 2) for k in range(0, len(bits), 4))
            lines.append('GW[%d]["%s"] = %d; GT[%d]["%s"] = %d; GE[%d]["%s"] = %d; GB[%d]["%s"] = "%s";'
                         % (hi, ch, cols, hi, ch, inked[0], hi, ch, inked[-1], hi, ch, hexs))
    lines.append("NHL.n = %d;" % len(NAME_HEIGHTS))
    return "\n".join(lines)


def build(dist):
    out = os.path.join(dist, NAME)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    tables = [grid_fonts(out), name_glyphs()]
    bg = ["%.6f" % ((c + 0.5) / 255) for c in BG]
    script = SCRIPT % {"lib": lib.lib_script(), "tables": "\n".join(tables),
                       "bgr": bg[0], "bgg": bg[1], "bgb": bg[2]}
    open(os.path.join(out, NAME + ".script"), "w").write(script)
    open(os.path.join(out, NAME + ".plymouth"), "w").write(PLYMOUTH.format(name=NAME))
    return out
