"""robi-386: a 1992 PC boots — VGA text mode, POST, DOS prompt, LOADLIN; LUKS as UNLOCK.BAT."""
import os, shutil
from PIL import Image
import fontkit, lib

NAME = "robi-386"
SCALES = (1, 2, 3, 4)

# VGA palette, very slightly warmed like a real tube
COLORS = {
    "7":  (172, 172, 168, 255),   # light gray (default DOS text)
    "15": (255, 255, 250, 255),   # white
    "14": (255, 255, 96, 255),    # yellow
    "12": (255, 92, 88, 255),     # light red
    "11": (96, 255, 255, 255),    # light cyan
}


def pad_for(s):
    return 0


def crt_atlas(color, s):
    """VGA atlas with phosphor glow and scanlines baked in.

    Cells are opaque black and the glow stays inside the cell: plymouth's
    Image.Crop premultiplies alpha twice, so translucent pixels must not
    overlap other glyphs."""
    pad = pad_for(s)
    cw, ch = 9 * s + 2 * pad, 16 * s + 2 * pad
    im = Image.new("RGBA", (16 * cw, 16 * ch), (0, 0, 0, 0))
    for code in range(256):
        g = fontkit.render_glyph(code, color, s, 9)
        if s >= 2:
            px = g.load()
            for y in range(g.height):
                if y % s == s - 1:
                    for x in range(g.width):
                        p = px[x, y]
                        if p[3]:
                            px[x, y] = (int(p[0] * .62), int(p[1] * .62), int(p[2] * .62), p[3])
        cell = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        cell.alpha_composite(g, (pad, pad))
        cell = fontkit.add_glow(cell, color, 0.9 * s, 0.75)
        base = Image.new("RGBA", (cw, ch), (0, 0, 0, 255))
        base.alpha_composite(cell)
        im.alpha_composite(base, ((code % 16) * cw, (code // 16) * ch))
    return im, cw, ch


def cursor_img(s):
    pad = 2 * s       # loaded directly (no Crop), so a translucent glow is fine
    col = COLORS["7"]
    g = Image.new("RGBA", (9 * s, 16 * s), (0, 0, 0, 0))
    for y in range(13 * s, 15 * s):
        for x in range(0, 8 * s):
            g.putpixel((x, y), col)
    cell = Image.new("RGBA", (9 * s + 2 * pad, 16 * s + 2 * pad), (0, 0, 0, 0))
    cell.alpha_composite(g, (pad, pad))
    return fontkit.add_glow(cell, col, 1.1 * s, 0.55)


def ps(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


# --------------------------------------------------------------------------
# The boot sequence. Ops:
#   p fid text      print            n            newline
#   t fid text      ghost-type        w frames     wait
#   m from to       memory count     c            checkpoint (unlock happens here)
#   d               LOADLIN dots     e            end / idle
# --------------------------------------------------------------------------
def boot_ops():
    hdr = "ROBI BIOS Version 1.0"
    hdr = hdr + " " * (62 - len(hdr)) + "(C) 1992"
    return [
        ("p", "15", hdr), ("n",), ("n",),
        ("p", "7", "Am386DX-40 CPU at 40 MHz"), ("n",),
        ("p", "7", "Memory Test : "), ("m", 640, 4096), ("n",), ("n",),
        ("w", 6),
        ("p", "7", "Detecting drives ..."), ("n",), ("w", 15),
        ("p", "7", "  Floppy Drive A : 1.44M, 3.5 in."), ("n",), ("w", 8),
        ("p", "7", "  Primary Master : NVMe SSD"), ("n",), ("w", 8),
        ("p", "7", "Sound Blaster 2.0 at A220 I5 D1"), ("n",), ("w", 10),
        ("n",),
        ("p", "7", "Press DEL to enter SETUP"), ("n",), ("w", 25),
        ("n",),
        ("p", "7", "Starting MS-DOS..."), ("n",), ("w", 35), ("n",),
        ("p", "7", "C:\\>"), ("c",), ("w", 25),
        ("t", "7", "CD LINUX"), ("n",),
        ("p", "7", "C:\\LINUX>"), ("c",), ("w", 15),
        ("t", "7", "LOADLIN VMLINUZ root=/dev/mapper/root rw"), ("n",), ("w", 10),
        ("p", "7", "LOADLIN v1.6"), ("n",),
        ("p", "7", "Loading VMLINUZ"), ("d",), ("n",),
        ("p", "7", "Uncompressing Linux... Ok, booting the kernel."), ("n",),
        ("e",),
    ]


def shutdown_ops(reboot):
    if reboot:
        tail = [("p", "7", "Rebooting ..."), ("n",)]
        cmd = "REBOOT"
    else:
        tail = [("p", "7", "Heads parked."), ("n",), ("w", 20),
                ("p", "15", "It is now safe to turn off your computer."), ("n",)]
        cmd = "PARK"
    return [("n",), ("p", "7", "C:\\>"), ("w", 30), ("t", "7", cmd), ("n",), ("w", 25)] + tail + [("e",)]


def ops_script(var, ops):
    out = []
    for i, op in enumerate(ops):
        out.append('%s[%d].t = "%s";' % (var, i, op[0]))
        if len(op) > 1:
            a = op[1]
            out.append('%s[%d].a = %s;' % (var, i, ps(a) if isinstance(a, str) else str(a)))
        if len(op) > 2:
            b = op[2]
            out.append('%s[%d].b = %s;' % (var, i, ps(b) if isinstance(b, str) else str(b)))
    out.append("%s.n = %d;" % (var, len(ops)))
    return "\n".join(out)


SCRIPT = r'''# =============================================================================
#  ROBI 386 — a PC from 1992 boots Linux.
#
#  VGA text mode 80x25 (IBM VGA 8x16 font from the Linux kernel), POST,
#  DOS prompt, LOADLIN. The LUKS passphrase is asked for by UNLOCK.BAT.
#  Everything is drawn with the theme's own bitmap glyphs, so it needs no
#  fonts in the initramfs.
#
#  Claude, October 2026 — for Frank
# =============================================================================

Window.SetBackgroundTopColor(0, 0, 0);
Window.SetBackgroundBottomColor(0, 0, 0);

SW = Window.GetWidth();
SH = Window.GetHeight();
SX = Window.GetX();
SY = Window.GetY();
%(lib)s

# ---- text mode geometry -----------------------------------------------------
COLS = 80;
ROWS = 25;
S = pick_scale(SW, SH, 9, 16, COLS, ROWS, 4);
CW = 9 * S;
LH = 16 * S;
PAD = 0;
X0 = SX + Math.Int((SW - COLS * CW) / 2);
Y0 = SY + Math.Int((SH - ROWS * LH) / 2);
font_load("7",  "vga-7-"  + S + ".png", CW + 2 * PAD, LH + 2 * PAD, CW, LH, PAD);
font_load("15", "vga-15-" + S + ".png", CW + 2 * PAD, LH + 2 * PAD, CW, LH, PAD);
font_load("14", "vga-14-" + S + ".png", CW + 2 * PAD, LH + 2 * PAD, CW, LH, PAD);
font_load("12", "vga-12-" + S + ".png", CW + 2 * PAD, LH + 2 * PAD, CW, LH, PAD);
font_load("11", "vga-11-" + S + ".png", CW + 2 * PAD, LH + 2 * PAD, CW, LH, PAD);

# ---- console ----------------------------------------------------------------
CON.row = 0;
CON.col = 0;
CELL.init = 1;
CUR.sprite = Sprite(Image("cursor-" + S + ".png"));
CPAD = 0;
CUR.blink = 0;
CUR.on = 1;

fun cur_place() {
    CUR.sprite.SetPosition(X0 + CON.col * CW - CPAD, Y0 + CON.row * LH - CPAD, 5);
    CUR.blink = 0;
    CUR.sprite.SetOpacity(1);
}

fun con_scroll() {
    local.r = 0;
    local.c = 0;
    for (r = 0; r < ROWS - 1; r++) {
        for (c = 0; c < COLS; c++) {
            global.CELL[r][c] = CELL[r + 1][c];
            if (CELL[r][c]) CELL[r][c].SetY(Y0 + r * LH - PAD);
        }
    }
    for (c = 0; c < COLS; c++) global.CELL[ROWS - 1][c] = NULL;
}

fun con_nl() {
    CON.col = 0;
    CON.row++;
    if (CON.row >= ROWS) {
        con_scroll();
        CON.row = ROWS - 1;
    }
    cur_place();
}

fun con_put(fid, code) {
    if (code != 32) {
        global.CELL[CON.row][CON.col] = Sprite(glyph(fid, code));
        CELL[CON.row][CON.col].SetPosition(X0 + CON.col * CW - PAD, Y0 + CON.row * LH - PAD, 1);
    } else {
        global.CELL[CON.row][CON.col] = NULL;
    }
    CON.col++;
    if (CON.col >= COLS) con_nl();
    cur_place();
}

fun con_back() {
    if (CON.col == 0) return;
    CON.col--;
    global.CELL[CON.row][CON.col] = NULL;
    cur_place();
}

fun con_print(fid, s) {
    local.k = txt_codes(s);
    local.i = 0;
    for (i = 0; i < k.n; i++) con_put(fid, k[i]);
}

fun con_clear() {
    local.r = 0;
    local.c = 0;
    for (r = 0; r < ROWS; r++)
        for (c = 0; c < COLS; c++)
            global.CELL[r][c] = NULL;
    CON.row = 0;
    CON.col = 0;
    cur_place();
}

# ---- scripts ----------------------------------------------------------------
%(boot_ops)s
%(shutdown_ops)s
%(reboot_ops)s
%(unlock_ops)s
%(question_ops)s

MODE = Plymouth.GetMode();
if (MODE == "shutdown") PROG = SHUT;
else if (MODE == "reboot") PROG = REBT;
else PROG = BOOT;

# timeline state
TL.pc = 0;
TL.wait = 0;
TL.sub = 0;
TL.mem = 0;
TL.prog = PROG;
TL.saved_pc = 0;
TL.in_unlock = 0;

# password state
PW.pending = 0;      # a password/question request waits to be shown
PW.kind = 0;         # 1 = password, 2 = question
PW.prompt = "";
PW.bullets = 0;
PW.shown = 0;        # bullets / chars currently printed
PW.entry = "";
PW.active = 0;       # input line is on screen
PW.last = "";
PW.answered = 0;
PW.retry = 0;
PW.grace = 0;        # frames to hold the timeline after Enter (a retry may follow)
PW.early = 0;        # Enter came before the input line was shown
TL.noted = 0;

BOOTP = 0;           # boot progress 0..1
ROOT = 0;            # root file system mounted
DOTS = 0;
MSGQ.n = 0;

fun jitter(a, b) {
    return a + Math.Int(rnd() * (b - a + 1));
}

# start the UNLOCK.BAT sequence (called at a checkpoint, cursor after a prompt)
fun unlock_begin() {
    TL.saved_pc = TL.pc;
    TL.in_unlock = 1;
    if (PW.kind == 2) TL.prog = QUES;
    else TL.prog = UNLK;
    TL.pc = 0;
    TL.sub = 0;
    if (PW.kind == 2) con_nl();
}

# the input line: show the system prompt, then bullets / typed text
fun input_begin() {
    local.p = PW.prompt;
    local.i = 0;
    if (p == "") p = "Passphrase:";
    con_print("7", p);
    con_nl();
    PW.shown = 0;
    if (PW.early) {
        # Enter was pressed before the prompt was on screen
        for (i = 0; i < PW.bullets && CON.col < COLS - 1; i++) con_put("15", 42);
        con_nl();
        PW.early = 0;
        TL.pc++;
        return;
    }
    PW.active = 1;
    input_sync();
}

fun input_sync() {
    local.k = 0;
    local.i = 0;
    if (!PW.active) return;
    if (PW.kind == 1) {
        while (PW.shown < PW.bullets && CON.col < COLS - 1) { con_put("15", 42); PW.shown++; }
        while (PW.shown > PW.bullets) { con_back(); PW.shown--; }
    } else {
        while (PW.shown > 0) { con_back(); PW.shown--; }
        k = txt_codes(PW.entry);
        for (i = 0; i < k.n && CON.col < COLS - 1; i++) { con_put("15", k[i]); PW.shown++; }
    }
}

fun input_end() {
    PW.active = 0;
    con_nl();
}

fun msg_flush() {
    local.i = 0;
    if (MSGQ.n == 0) return;
    if (CON.col != 0) con_nl();
    for (i = 0; i < MSGQ.n; i++) { con_print("11", MSGQ[i]); con_nl(); }
    global.MSGQ.n = 0;
}

# one step of the timeline; returns when it has to wait
fun tl_step() {
    local.op = 0;
    local.k = 0;
    local.fast = 1;
    local.guard = 0;
    if (PW.pending) fast = 6;
    if (TL.wait > 0) { TL.wait -= fast; return; }
    while (guard < 200) {
        guard++;
        op = TL.prog[TL.pc];
        if (TL.pc >= TL.prog.n) return;
        if (op.t == "p") { con_print(op.a, op.b); TL.pc++; }
        else if (op.t == "n") { con_nl(); TL.pc++; msg_flush(); }
        else if (op.t == "w") { TL.wait = op.a; TL.pc++; return; }
        else if (op.t == "t") {
            if (!op.k) op.k = txt_codes(op.b);
            if (TL.sub < op.k.n) {
                con_put(op.a, op.k[TL.sub]);
                TL.sub++;
                TL.wait = jitter(1, 3);
                if (PW.pending || TL.in_unlock) TL.wait = 1;
                return;
            }
            TL.sub = 0;
            TL.pc++;
        }
        else if (op.t == "m") {
            if (TL.mem == 0) TL.mem = op.a;
            else if (PW.pending) TL.mem += 256;
            else TL.mem += 128;
            if (TL.mem > op.b) TL.mem = op.b;
            # print the counter in place: "  640K" .. "4096K"
            k = "" + TL.mem;
            while (k.Length() < 5) k = " " + k;
            if (TL.sub > 0) { local.j = 0; for (j = 0; j < 6; j++) con_back(); }
            con_print("7", k + "K");
            TL.sub = 1;
            if (TL.mem >= op.b) { con_print("7", " OK"); TL.sub = 0; TL.mem = 0; TL.pc++; }
            TL.wait = 1;
            return;
        }
        else if (op.t == "c") {
            if (PW.pending && !TL.in_unlock) { unlock_begin(); return; }
            if (PW.grace > 0) return;
            TL.pc++;
        }
        else if (op.t == "y") {
            if (PW.retry && !TL.noted) { con_print("12", "Access denied"); con_nl(); }
            TL.noted = 0;
            con_print("14", "Type your passphrase and press ENTER.");
            con_nl();
            TL.pc++;
        }
        else if (op.t == "i") {
            # hand over to the input line, wait for Enter (on_normal advances pc)
            if (!PW.active) input_begin();
            return;
        }
        else if (op.t == "g") {
            # after Enter: "Unlocking drive ..." with dots while cryptsetup works.
            # A new request with the same prompt means the passphrase was wrong.
            if (TL.sub == 0) {
                con_print("7", "Unlocking drive ...");
                TL.sub = 1;
            }
            if (PW.pending) {
                con_nl();
                if (PW.retry) { con_print("12", "Access denied"); con_nl(); TL.noted = 1; }
                con_nl();
                con_print("7", "C:\\>");
                if (PW.kind == 2) { TL.prog = QUES; con_nl(); }
                TL.pc = 0;
                TL.sub = 0;
                return;
            }
            if (PW.grace > 0) {
                TL.sub++;
                if (TL.sub %% 25 == 0 && CON.col < COLS - 4) con_put("7", 46);
                return;
            }
            con_print("7", " OK");
            TL.sub = 0;
            TL.pc++;
        }
        else if (op.t == "x") {
            # end of UNLOCK.BAT: back to the main program
            TL.in_unlock = 0;
            TL.prog = PROG;
            TL.pc = TL.saved_pc + 1;
            TL.sub = 0;
        }
        else if (op.t == "d") {
            # LOADLIN progress dots, driven by plymouth's boot progress and time
            k = Math.Int(BOOTP * 30);
            if (TL.sub %% 12 == 0 && DOTS < 30) k = Math.Max(k, DOTS + 1);
            TL.sub++;
            while (DOTS < k && DOTS < 30) { con_put("7", 46); DOTS++; }
            if (DOTS >= 30 || ROOT) { con_print("7", " ok"); TL.sub = 0; TL.pc++; TL.wait = 15; }
            return;
        }
        else if (op.t == "e") {
            msg_flush();
            return;
        }
        else TL.pc++;
    }
}

# ---- plymouth callbacks -----------------------------------------------------
fun on_password(prompt, bullets) {
    if (PW.kind != 1 || (!PW.pending && !PW.active)) {
        # a new request
        PW.retry = (PW.answered && prompt == PW.last);
        PW.kind = 1;
        PW.prompt = prompt;
        PW.pending = 1;
        PW.grace = 0;
        if (TL.in_unlock && !PW.active) { }
    }
    PW.bullets = bullets;
    input_sync();
}

fun on_question(prompt, entry) {
    if (PW.kind != 2 || (!PW.pending && !PW.active)) {
        PW.retry = 0;
        PW.kind = 2;
        PW.prompt = prompt;
        PW.pending = 1;
        PW.grace = 0;
    }
    PW.entry = entry;
    input_sync();
}

fun on_normal() {
    if (PW.kind == 1 && (PW.active || PW.pending)) {
        PW.answered = 1;
        PW.last = PW.prompt;
        PW.grace = 200;
    }
    if (PW.active) {
        input_end();
        TL.pc++;                 # continue after the input op
    } else if (PW.pending) {
        PW.early = 1;            # answered before the prompt was drawn
        if (!TL.in_unlock) PW.early = 0;
    }
    PW.pending = 0;
    PW.active = 0;
    PW.kind = 0;
}

fun on_message(text) {
    global.MSGQ[MSGQ.n] = text;
    global.MSGQ.n++;
}

fun on_progress(duration, progress) {
    global.BOOTP = progress;
}

fun on_root() {
    global.ROOT = 1;
    PW.grace = 0;
}

fun refresh() {
    if (PW.grace > 0) {
        PW.grace--;
        if (PW.pending) PW.grace = 0;
    }
    tl_step();
    CUR.blink++;
    if (CUR.blink >= 14) {
        CUR.blink = 0;
        CUR.on = !CUR.on;
        CUR.sprite.SetOpacity(CUR.on);
    }
}

cur_place();
Plymouth.SetRefreshFunction(refresh);
Plymouth.SetDisplayPasswordFunction(on_password);
Plymouth.SetDisplayQuestionFunction(on_question);
Plymouth.SetDisplayNormalFunction(on_normal);
Plymouth.SetDisplayMessageFunction(on_message);
Plymouth.SetBootProgressFunction(on_progress);
Plymouth.SetRootMountedFunction(on_root);
'''

PLYMOUTH = """[Plymouth Theme]
Name=ROBI 386
Description=A 1992 PC boots Linux: VGA text mode, POST, DOS prompt, LOADLIN, LUKS via UNLOCK.BAT
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/{name}
ScriptFile=/usr/share/plymouth/themes/{name}/{name}.script
"""


def unlock_ops():
    return [
        ("t", "7", "UNLOCK.BAT"), ("n",), ("w", 6),
        ("y",),                       # ECHO line (with "Access denied" on a late retry)
        ("i",),                       # system prompt + bullets, wait for Enter
        ("g",),                       # grace: a wrong passphrase comes back here
        ("n",), ("n",),
        ("p", "7", "C:\\>"),
        ("x",),
    ]


def question_ops():
    return [("i",), ("p", "7", "C:\\>"), ("x",)]


def build(dist):
    out = os.path.join(dist, NAME)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    for s in SCALES:
        for fid, col in COLORS.items():
            im, cw, ch = crt_atlas(col, s)
            im.save(os.path.join(out, "vga-%s-%d.png" % (fid, s)), optimize=True)
        cursor_img(s).save(os.path.join(out, "cursor-%d.png" % s), optimize=True)
    script = SCRIPT % {
        "lib": lib.lib_script(),
        "boot_ops": ops_script("BOOT", boot_ops()),
        "shutdown_ops": ops_script("SHUT", shutdown_ops(False)),
        "reboot_ops": ops_script("REBT", shutdown_ops(True)),
        "unlock_ops": ops_script("UNLK", unlock_ops()),
        "question_ops": ops_script("QUES", question_ops()),
    }
    open(os.path.join(out, NAME + ".script"), "w").write(script)
    open(os.path.join(out, NAME + ".plymouth"), "w").write(PLYMOUTH.format(name=NAME))
    return out
