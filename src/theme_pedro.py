"""pedro-raccoon-luks: FilaCo's Pedro animation plus a LUKS passphrase prompt.

The 198 animation frames come with "Pedro Raccoon Plymouth" by FilaCo (MIT,
https://github.com/FilaCo/plymouth-theme-pedro-raccoon, also on the KDE Store
as store.kde.org/p/2148515) and are not part of this repository. The build
writes only the script, the fonts and the .plymouth file; install.sh copies
the frames from the installed original theme (/usr/share/plymouth/themes/
pedro-raccoon).
"""
import os, shutil
import fontkit, lib

NAME = "pedro-raccoon-luks"
N_FRAMES = 198

COLORS = {
    "w": (246, 236, 242, 255),   # bullets / entry: the pinkish white of Pedro's disc
    "g": (150, 136, 152, 255),   # system prompt text
    "r": (255, 120, 160, 255),   # "wrong passphrase"
}

SCRIPT = r'''# =============================================================================
#  Pedro Raccoon — LUKS edition
#
#  Animation from "Pedro Raccoon Plymouth" by FilaCo (MIT licence),
#  https://github.com/FilaCo/plymouth-theme-pedro-raccoon
#  (also store.kde.org/p/2148515): its 198 frames, unchanged, copied from the
#  installed original by install.sh.
#  Added: passphrase / question / message display for encrypted disks, drawn
#  with a bitmap font so it needs nothing from the initramfs besides this
#  folder. Pedro dances faster while you type.
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

# ---- font -------------------------------------------------------------------
S = 1;
if (SH >= 900) S = 2;
if (SH >= 1500) S = 3;
if (SH >= 2000) S = 4;
SS = S - 1;                      # smaller size for the system prompt
if (SS < 1) SS = 1;
font_load("w", "font-w-" + S + ".png", 9 * S, 16 * S, 9 * S, 16 * S, 0);
font_load("r", "font-r-" + SS + ".png", 9 * SS, 16 * SS, 9 * SS, 16 * SS, 0);
font_load("g", "font-g-" + SS + ".png", 9 * SS, 16 * SS, 9 * SS, 16 * SS, 0);
ADV = 9 * S;
LH = 16 * S;
MAXC = Math.Int(SW * 0.92 / ADV);
MAXCS = Math.Int(SW * 0.92 / (9 * SS));

# ---- animation --------------------------------------------------------------
anim.count = %(nframes)d;
for (i = 0; i < anim.count; i++)
    anim.img[i] = Image("animation-" + (i + 1) + ".png");
anim.zoom = 1;
if (SH >= 1700) anim.zoom = 2;
anim.size = anim.img[0].GetWidth() * anim.zoom;
anim.sprite = Sprite();
anim.sprite.SetPosition(SX + SW / 2 - anim.size / 2, SY + SH / 2 - anim.size / 2, 0);
anim.idx = 169;          # like the original's 1.0: start near the end of the loop
anim.shown = -1;
anim.acc = 0;
anim.boost = 0;          # extra frames to dance through (typing)

fun anim_step() {
    local.speed = 0.5;   # 25 fps at plymouth's 50 Hz refresh
    if (anim.boost > 0) {
        speed = 1.5;
        anim.boost -= 1;
    }
    anim.acc += speed;
    while (anim.acc >= 1) {
        anim.acc -= 1;
        anim.idx = (anim.idx + 1) %% anim.count;
    }
    if (anim.idx != anim.shown) {
        if (anim.zoom > 1)
            anim.sprite.SetImage(anim.img[anim.idx].Scale(anim.size, anim.size));
        else
            anim.sprite.SetImage(anim.img[anim.idx]);
        anim.shown = anim.idx;
    }
}

# ---- layout below the disc --------------------------------------------------
BASE = SY + SH / 2 + anim.size / 2 + LH * 1.4;
Y_INFO = BASE;                       # "wrong passphrase"
Y_PROMPT = BASE + 16 * SS * 1.6;     # system prompt (small, dim)
Y_ENTRY = Y_PROMPT + 16 * SS * 2;    # bullets / typed answer
Y_CAPS = Y_ENTRY + LH * 1.6;         # caps lock hint
Y_MSG = SY + SH - LH * 2.5;          # boot messages

fun centered(fid, s, y, z) {
    local.a = FONT[fid].adv;
    local.t = txt_fit(s, Math.Int(SW * 0.92 / a));
    local.n = txt_len(t);
    return txt_run(fid, t, SX + SW / 2 - n * a / 2, y, z);
}

# ---- password / question state ----------------------------------------------
P.active = 0;            # 1 = password, 2 = question
P.bullets = -1;
P.prompt = "";
P.last = "";
P.answered = 0;
P.err = 0;               # frames left to show "wrong passphrase"
P.blink = 0;
P.caps = 0;

fun draw_entry(s) {
    global.entry_run = centered("w", s, Y_ENTRY, 10);
    # cursor right after the entry
    global.cursor_x = SX + SW / 2 + txt_len(txt_fit(s, MAXC)) * ADV / 2;
    global.cursor_run = txt_run("w", "_", global.cursor_x, Y_ENTRY, 10);
}

fun on_password(prompt, bullets) {
    local.s = "";
    local.i = 0;
    local.n = 0;
    if (P.active != 1) {
        if (P.answered && prompt == P.last) P.err = 200;
        P.active = 1;
        P.prompt = prompt;
        P.bullets = -1;
        if (prompt == "") prompt = "Passphrase";
        global.prompt_run = centered("g", prompt, Y_PROMPT, 10);
        global.question_run = NULL;
    }
    if (bullets > P.bullets && P.bullets >= 0) anim.boost += 4 * (bullets - P.bullets);
    if (bullets != P.bullets) {
        P.bullets = bullets;
        n = bullets;
        if (n > MAXC / 2 - 2) n = Math.Int(MAXC / 2 - 2);
        for (i = 0; i < n; i++) s = s + "• ";
        draw_entry(s);
    }
}

fun on_question(prompt, entry) {
    if (P.active != 2) {
        P.active = 2;
        P.err = 0;
        global.err_run = NULL;
        global.prompt_run = centered("g", prompt, Y_PROMPT, 10);
    }
    draw_entry(entry);
    anim.boost += 4;
}

fun on_normal() {
    if (P.active == 1) {
        P.answered = 1;
        P.last = P.prompt;
    }
    P.active = 0;
    P.bullets = -1;
    global.prompt_run = NULL;
    global.entry_run = NULL;
    global.cursor_run = NULL;
    global.caps_run = NULL;
    P.caps = 0;
}

fun on_message(text) {
    global.msg_run = centered("g", text, Y_MSG, 10);
}

fun on_hide_message(text) {
    global.msg_run = NULL;
}

fun refresh() {
    anim_step();
    if (P.active) {
        P.blink = (P.blink + 1) %% 50;
        if (global.cursor_run) run_opacity(global.cursor_run, P.blink < 25);
        if (P.active == 1 && P.blink %% 10 == 0) {
            if (Plymouth.GetCapslockState()) {
                if (!P.caps) global.caps_run = centered("r", "[ CAPS LOCK ]", Y_CAPS, 10);
                P.caps = 1;
            } else {
                P.caps = 0;
                global.caps_run = NULL;
            }
        }
    }
    if (P.err > 0) {
        if (!global.err_run) global.err_run = centered("r", "wrong. try again.", Y_INFO, 10);
        P.err -= 1;
        if (P.err < 25) run_opacity(global.err_run, P.err / 25);
        if (P.err == 0) global.err_run = NULL;
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
Name=Pedro Raccoon (LUKS)
Description=Pedro Raccoon Plymouth by FilaCo, with a passphrase prompt for encrypted disks
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
    for fid, col in COLORS.items():
        for s in (1, 2, 3, 4):
            im, cw, ch = fontkit.atlas(col, s, 9, 0)
            im.save(os.path.join(out, "font-%s-%d.png" % (fid, s)), optimize=True)
    script = SCRIPT % {"lib": lib.lib_script(), "nframes": N_FRAMES}
    open(os.path.join(out, NAME + ".script"), "w").write(script)
    open(os.path.join(out, NAME + ".plymouth"), "w").write(PLYMOUTH.format(name=NAME))
    return out
