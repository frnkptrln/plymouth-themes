"""Shared Plymouth-script code: glyph text engine on top of bitmap atlases.

Everything a theme prints goes through bitmap glyphs cut from PNG atlases,
so nothing depends on fonts or label plugins being present in the initramfs.
"""
import fontkit

ASCII = "".join(chr(c) for c in range(32, 127))


def _plystr(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def u8_table():
    """UTF-8 sequences -> CP437 codes, for box drawing / shades / umlauts in theme strings."""
    lines = []
    for ch, code in sorted(fontkit.U2CP.items(), key=lambda kv: kv[1]):
        if ord(ch) < 128:
            continue
        lines.append("TXT.u8[%s] = %d;" % (_plystr(ch), code))
    return "\n".join(lines)


LIB = r'''
#==============================================================================
# glyph text engine — bitmap font from PNG atlases (IBM VGA 8x16, CP437)
#==============================================================================
TXT.ascii = %(ascii)s;
for (TXT.i = 0; TXT.i < 95; TXT.i++) TXT.ord[TXT.ascii.CharAt(TXT.i)] = 32 + TXT.i;
%(u8)s

# Turn a string into an array of CP437 codes (out.n = length). out.off[k] is
# the byte offset where glyph k starts, out.off[out.n] the length in bytes:
# Plymouth's string functions count bytes, and "•" alone is three of them.
fun txt_codes(s) {
    local.out.n = 0;
    local.i = 0;
    local.k = 0;
    local.c = s.CharAt(0);
    while (c != "") {
        out.off[out.n] = i;
        k = TXT.ord[c];
        if (k) { out[out.n] = k; out.n++; i++; }
        else {
            k = TXT.u8[s.SubString(i, i + 3)];
            if (k) { out[out.n] = k; out.n++; i += 3; }
            else {
                k = TXT.u8[s.SubString(i, i + 2)];
                if (k) { out[out.n] = k; out.n++; i += 2; }
                else { out[out.n] = 63; out.n++; i++; }
            }
        }
        c = s.CharAt(i);
    }
    out.off[out.n] = i;
    return out;
}

# Number of glyphs a string renders to.
fun txt_len(s) {
    local.c = txt_codes(s);
    return c.n;
}

# Load a font atlas. fid: short id, file: atlas PNG, cw/ch: atlas cell size,
# adv: horizontal advance, lh: line height, pad: glow margin around each glyph.
FONT.count = 0;     # must exist at top level so functions see the globals
GLYPH.count = 0;

fun font_load(fid, file, cw, ch, adv, lh, pad) {
    global.FONT[fid].atlas = Image(file);
    global.FONT[fid].cw = cw;
    global.FONT[fid].ch = ch;
    global.FONT[fid].adv = adv;
    global.FONT[fid].lh = lh;
    global.FONT[fid].pad = pad;
}

fun glyph(fid, code) {
    if (!GLYPH[fid][code])
        global.GLYPH[fid][code] = FONT[fid].atlas.Crop((code %% 16) * FONT[fid].cw,
                                                Math.Int(code / 16) * FONT[fid].ch,
                                                FONT[fid].cw, FONT[fid].ch);
    return GLYPH[fid][code];
}

# Create sprites for a string at (x, y). Returns a run object; drop it to erase.
fun txt_run(fid, s, x, y, z) {
    local.codes = txt_codes(s);
    local.r.n = codes.n;
    local.r.w = codes.n * FONT[fid].adv;
    local.r.x = x;
    local.r.y = y;
    local.i = 0;
    for (i = 0; i < codes.n; i++) {
        if (codes[i] != 32) {
            r.sp[i] = Sprite(glyph(fid, codes[i]));
            r.sp[i].SetPosition(x + i * FONT[fid].adv - FONT[fid].pad, y - FONT[fid].pad, z);
        }
    }
    return r;
}

# Same, from an already decoded code array (from index a, count n).
fun txt_run_codes(fid, codes, a, n, x, y, z) {
    local.r.n = n;
    local.r.w = n * FONT[fid].adv;
    local.r.x = x;
    local.r.y = y;
    local.i = 0;
    for (i = 0; i < n; i++) {
        if (codes[a + i] != 32) {
            r.sp[i] = Sprite(glyph(fid, codes[a + i]));
            r.sp[i].SetPosition(x + i * FONT[fid].adv - FONT[fid].pad, y - FONT[fid].pad, z);
        }
    }
    return r;
}

fun run_opacity(r, o) {
    local.i = 0;
    for (i = 0; i < r.n; i++) if (r.sp[i]) r.sp[i].SetOpacity(o);
}

fun run_move(r, x, y) {
    local.i = 0;
    local.fid = 0;
    for (i = 0; i < r.n; i++)
        if (r.sp[i]) r.sp[i].SetPosition(x + (r.sp[i].GetX() - r.x), y + (r.sp[i].GetY() - r.y), r.sp[i].GetZ());
    r.x = x;
    r.y = y;
}

# Shorten s to at most n glyphs by cutting out the middle, at glyph
# boundaries, so a multi-byte character is never split.
fun txt_fit(s, n) {
    local.c = txt_codes(s);
    local.h = 0;
    if (c.n <= n) return s;
    if (n < 5) return s.SubString(0, c.off[n]);
    h = Math.Int((n - 3) / 2);
    return s.SubString(0, c.off[h]) + "..." + s.SubString(c.off[c.n - (n - 3 - h)], c.off[c.n]);
}

# Uniform random number in [0, 1). Plymouth 24's Math.Random() returns values
# scaled down by 2^32; normalise so this also works if that ever gets fixed.
fun rnd() {
    local.r = Math.Random();
    if (r < 0.000001) r = r * 4294967296;
    return r - Math.Int(r);
}

# Pick the largest integer scale (from 1..maxs) at which a cols x rows grid of
# (cw x lh) cells still fits into w x h.
fun pick_scale(w, h, cw, lh, cols, rows, maxs) {
    local.s = maxs;
    while (s > 1 && (cols * cw * s > w || rows * lh * s > h)) s--;
    return s;
}
'''


def lib_script():
    return LIB % {"ascii": _plystr(ASCII), "u8": u8_table()}


# ---------------------------------------------------------------------------
# Latin Modern Mono atlases, shared by the themes that print in it
# ---------------------------------------------------------------------------
LM_SIZES = (14, 17, 20, 24, 28, 34, 40)
LM_DIRS = [
    "/usr/share/fonts/OTF",                                  # Arch
    "/usr/share/fonts/opentype/lm",
    "/usr/share/texmf/fonts/opentype/public/lm",             # Debian, Ubuntu
    "/usr/share/texmf-dist/fonts/opentype/public/lm",
    "/usr/local/texlive/*/texmf-dist/fonts/opentype/public/lm",
]


def lm_file(name, env=None):
    """Path of a Latin Modern font file, e.g. lmmono10-regular.otf; the
    environment variable env, if given and set, overrides the search."""
    import glob
    import os
    if env and os.environ.get(env):
        return os.environ[env]
    for d in LM_DIRS:
        found = sorted(glob.glob(os.path.join(d, name)))
        if found:
            return found[-1]
    hint = " or set %s=/path/to/%s" % (env, name) if env else ""
    raise SystemExit("%s not found (Arch: otf-latin-modern, Debian/Ubuntu: fonts-lmodern%s)" % (name, hint))


def lm_font():
    """Path of Latin Modern Mono 10 Regular; LMMONO=<path> overrides the search."""
    return lm_file("lmmono10-regular.otf", "LMMONO")


def lm_fonts(out, colors, bg, sizes=LM_SIZES):
    """Write font-<id>-<size>.png atlases (opaque, bg baked in) and return the
    size table for the script: FSL[i] size, FSA[i] advance, FSH[i] line height."""
    import os
    font = lm_font()
    lines = []
    for i, fs in enumerate(sizes):
        for fid, col in colors.items():
            im, cw, ch, adv, lh = fontkit.ttf_atlas(font, fs, col, bg=bg)
            im.save(os.path.join(out, "font-%s-%d.png" % (fid, fs)), optimize=True)
        lines.append("FSL[%d] = %d; FSA[%d] = %d; FSH[%d] = %d;" % (i, fs, i, adv, i, lh))
    lines.append("FSL.n = %d;" % len(sizes))
    return "\n".join(lines)


PROMPT = r'''
#==============================================================================
# passphrase, question and message handling, shared by the newer themes
#
# Before prompt_setup() the theme sets
#   PR.hi, PR.lo, PR.err   font ids: entry, prompt and messages, warnings
#   PR.y0 .. PR.y3         top of the lines: warning, prompt, entry, caps lock
#   PR.cx                  centre x of the text (PR.align = "center"), or
#   PR.left                left edge (PR.align = "left")
#   PR.maxc                most glyphs on a line
#   PR.adv                 glyph advance in px
#   PR.z                   z of the text
# and defines all of these hooks (empty bodies are fine):
#   hook_prompt()          a passphrase prompt appeared
#   hook_wrong()           the same prompt came back: the passphrase was wrong
#   hook_key(n)            a character was typed, n characters now
#   hook_erase(n)          a character was deleted
#   hook_enter()           Enter: the passphrase went to the disk
#   hook_question()        a question appeared
# Its refresh function calls prompt_tick() once per frame.
#==============================================================================
PR.wrong = "wrong. try again.";
PR.caps_text = "caps lock";
PR.align = "center";
PR.z = 50;
P.active = 0;          # 0 none, 1 passphrase, 2 question
P.bullets = -1;
P.prompt = "";
P.last = "";
P.answered = 0;
P.err = 0;
P.blink = 0;
P.caps = 0;
P.msg = 0;

fun nearest(list, v) {
    local.best = 999999;
    local.r = list[0];
    local.i = 0;
    for (i = 0; i < list.n; i++)
        if (Math.Abs(list[i] - v) < best) { best = Math.Abs(list[i] - v); r = list[i]; }
    return r;
}

# Pick the LM Mono size for this screen and load the given font ids.
fun lm_load(ids, target) {
    local.i = 0;
    global.FS = nearest(FSL, target);
    for (i = 0; i < FSL.n; i++) if (FSL[i] == FS) { global.FADV = FSA[i]; global.FLH = FSH[i]; }
    for (i = 0; i < ids.n; i++)
        font_load(ids[i], "font-" + ids[i] + "-" + FS + ".png", FADV, FLH, FADV, FLH, 0);
}

# The four text lines at the bottom of the screen, centred.
fun prompt_bottom(cx, maxw) {
    PR.cx = cx;
    PR.adv = FADV;
    PR.maxc = Math.Int(maxw / FADV);
    PR.y3 = SY + SH - Math.Int(FLH * 1.3);
    PR.y2 = PR.y3 - FLH;
    PR.y1 = PR.y2 - Math.Int(FLH * 1.05);
    PR.y0 = PR.y1 - Math.Int(FLH * 1.05);
}

fun pr_x(n) {
    if (PR.align == "left") return PR.left;
    return PR.cx - Math.Int(n * PR.adv / 2);
}

fun pr_line(fid, s, y) {
    local.t = txt_fit(s, PR.maxc);
    return txt_run(fid, t, pr_x(txt_len(t)), y, PR.z);
}

fun pr_entry(s) {
    local.t = txt_fit(s, PR.maxc - 2);
    local.x = pr_x(txt_len(t) + 1);
    global.PR_ENTRY = txt_run(PR.hi, t, x, PR.y2, PR.z);
    global.PR_CURSOR = txt_run(PR.hi, "_", x + txt_len(t) * PR.adv, PR.y2, PR.z);
}

fun on_password(prompt, bullets) {
    local.s = "";
    local.i = 0;
    local.n = 0;
    if (P.active != 1) {
        global.PR_MSG = NULL;
        P.msg = 0;
        if (P.answered && prompt == P.last) {
            P.err = 220;
            global.PR_ERR = NULL;
            hook_wrong();
        } else {
            hook_prompt();
        }
        P.active = 1;
        P.prompt = prompt;
        P.bullets = -1;
        if (prompt == "") prompt = "passphrase:";
        global.PR_PROMPT = pr_line(PR.lo, prompt, PR.y1);
    }
    if (bullets != P.bullets) {
        if (P.bullets >= 0) {
            if (bullets > P.bullets) hook_key(bullets);
            else hook_erase(bullets);
        }
        P.bullets = bullets;
        n = bullets;
        if (n > 40) n = 40;
        for (i = 0; i < n; i++) s = s + "• ";
        pr_entry(s);
    }
}

fun on_question(prompt, entry) {
    if (P.active != 2) {
        P.active = 2;
        P.err = 0;
        global.PR_ERR = NULL;
        global.PR_MSG = NULL;
        global.PR_PROMPT = pr_line(PR.lo, prompt, PR.y1);
        hook_question();
    }
    pr_entry(entry);
}

fun on_normal() {
    if (P.active == 1) {
        P.answered = 1;
        P.last = P.prompt;
        hook_enter();
    }
    P.active = 0;
    P.bullets = -1;
    global.PR_PROMPT = NULL;
    global.PR_ENTRY = NULL;
    global.PR_CURSOR = NULL;
    global.PR_CAPS = NULL;
    P.caps = 0;
}

fun on_message(text) {
    if (P.active) return;
    global.PR_MSG = pr_line(PR.lo, text, PR.y1);
    P.msg = 250;
}

fun on_hide_message(text) {
    global.PR_MSG = NULL;
    P.msg = 0;
}

fun prompt_tick() {
    if (P.active) {
        P.blink = (P.blink + 1) % 50;
        if (PR_CURSOR) run_opacity(PR_CURSOR, P.blink < 25);
        if (P.active == 1 && P.blink % 10 == 0) {
            if (Plymouth.GetCapslockState()) {
                if (!P.caps) global.PR_CAPS = pr_line(PR.err, PR.caps_text, PR.y3);
                P.caps = 1;
            } else {
                P.caps = 0;
                global.PR_CAPS = NULL;
            }
        }
    }
    if (P.err > 0) {
        if (!PR_ERR) global.PR_ERR = pr_line(PR.err, PR.wrong, PR.y0);
        P.err--;
        if (P.err < 30) run_opacity(PR_ERR, P.err / 30);
        if (P.err == 0) global.PR_ERR = NULL;
    }
    if (P.msg > 0) {
        P.msg--;
        if (P.msg == 0) global.PR_MSG = NULL;
    }
}

fun prompt_setup() {
    Plymouth.SetDisplayPasswordFunction(on_password);
    Plymouth.SetDisplayQuestionFunction(on_question);
    Plymouth.SetDisplayNormalFunction(on_normal);
    Plymouth.SetDisplayMessageFunction(on_message);
    Plymouth.SetHideMessageFunction(on_hide_message);
}
'''


def prompt_script():
    return PROMPT
