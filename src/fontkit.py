"""Bitmap font kit: IBM VGA 8x16 (CP437) from the Linux kernel's lib/fonts/font_8x16.c."""
import re, os
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "font_8x16.c")   # Linux kernel, lib/fonts/font_8x16.c (GPL-2.0)

def load_vga():
    txt = open(SRC).read()
    body = txt[txt.index("fontdata_8x16"):]
    vals = [int(v, 16) for v in re.findall(r"0x([0-9a-fA-F]{2}),", body)]
    assert len(vals) >= 4096, len(vals)
    vals = vals[:4096]
    return [vals[i*16:(i+1)*16] for i in range(256)]

GLYPHS = load_vga()

def cp437_char(code):
    if code == 0: return "\x00"
    return bytes([code]).decode("cp437")

# Unicode -> cp437 code for everything cp437 can represent (plus a few aliases)
U2CP = {}
for c in range(32, 256):
    U2CP[cp437_char(c)] = c
# control-range glyphs of cp437 (smileys, arrows, bullet...)
CTRL = "\u0000☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼"
for c, ch in enumerate(CTRL):
    if c: U2CP[ch] = c
U2CP["⌂"] = 127
U2CP["∙"] = 0xF9
U2CP["·"] = 0xFA

def glyph_char(code):
    """The Unicode character CP437 draws for a code (including the 1..31 symbols)."""
    if 0 < code < 32:
        return CTRL[code]
    if code == 127:
        return "⌂"
    return cp437_char(code)


def glyph_cell(code, cell_w=9):
    """Return list of rows (lists of 0/1) for one glyph in a cell_w x 16 cell (VGA 9th-column rule)."""
    rows = []
    for r in GLYPHS[code]:
        bits = [(r >> (7 - b)) & 1 for b in range(8)]
        if cell_w == 9:
            bits.append(bits[7] if 0xC0 <= code <= 0xDF else 0)
        rows.append(bits)
    return rows

def render_glyph(code, color, scale=1, cell_w=9, sx=None, sy=None):
    sx = sx or scale; sy = sy or scale
    im = Image.new("RGBA", (cell_w * sx, 16 * sy), (0, 0, 0, 0))
    px = im.load()
    for y, row in enumerate(glyph_cell(code, cell_w)):
        for x, on in enumerate(row):
            if on:
                for dy in range(sy):
                    for dx in range(sx):
                        px[x*sx+dx, y*sy+dy] = color
    return im

def render_text(text, color, scale=1, cell_w=9, bg=None):
    codes = [U2CP.get(ch, ord("?")) for ch in text]
    im = Image.new("RGBA", (len(codes) * cell_w * scale, 16 * scale), bg or (0, 0, 0, 0))
    for i, c in enumerate(codes):
        g = render_glyph(c, color, scale, cell_w)
        im.alpha_composite(g, (i * cell_w * scale, 0))
    return im

def add_glow(im, color, radius, strength):
    """Phosphor bloom: blurred copy of alpha, tinted, composited under the sharp image."""
    a = im.split()[3].filter(ImageFilter.GaussianBlur(radius))
    a = a.point(lambda v: min(255, int(v * strength)))
    glow = Image.new("RGBA", im.size, color[:3] + (0,))
    glow.putalpha(a)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(glow)
    out.alpha_composite(im)
    return out

def atlas(color, scale=1, cell_w=9, pad=0, glow=None, codes=range(256)):
    """16x16 atlas; each cell is (cell_w*scale + 2*pad) x (16*scale + 2*pad); glyph drawn at (pad, pad)."""
    cw, ch = cell_w * scale + 2 * pad, 16 * scale + 2 * pad
    im = Image.new("RGBA", (16 * cw, 16 * ch), (0, 0, 0, 0))
    for c in codes:
        g = render_glyph(c, color, scale, cell_w)
        cell = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        cell.alpha_composite(g, (pad, pad))
        if glow:
            cell = add_glow(cell, color, *glow)
        im.alpha_composite(cell, ((c % 16) * cw, (c // 16) * ch))
    return im, cw, ch


def ttf_atlas(path, size, color, adv=None, lh=None, pad=0, glow=None, bg=None):
    """CP437-indexed 16x16 atlas from a TrueType/OpenType font (antialiased)."""
    from PIL import ImageFont, ImageDraw
    font = ImageFont.truetype(path, size)
    if adv is None:
        adv = int(round(font.getlength("M")))
    asc, desc = font.getmetrics()
    if lh is None:
        lh = int(round((asc + desc) * 1.15))
    cw, ch = adv + 2 * pad, lh + 2 * pad
    im = Image.new("RGBA", (16 * cw, 16 * ch), (0, 0, 0, 0))
    top = (lh - (asc + desc)) // 2
    for code in range(1, 256):
        u = glyph_char(code)
        if not u.strip() and code != 32:
            continue
        cell = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        d = ImageDraw.Draw(cell)
        w = font.getlength(u)
        d.text((pad + (adv - w) / 2, pad + top), u, font=font, fill=color)
        if glow:
            cell = add_glow(cell, color, *glow)
        if bg:
            # opaque cell: plymouth's Image.Crop premultiplies alpha a second
            # time, so translucent edges would come out too dark.
            base = Image.new("RGBA", (cw, ch), bg)
            base.alpha_composite(cell)
            cell = base
        im.alpha_composite(cell, ((code % 16) * cw, (code // 16) * ch))
    return im, cw, ch, adv, lh


def opaque_glow_atlas(color, s, glow=(0.9, 0.75), scan=None, bg=(0, 0, 0, 255)):
    """VGA atlas (16x16 cells of 9s x 16s) with the glow kept inside each cell and an
    opaque background: plymouth's Image.Crop premultiplies alpha a second time, so
    nothing translucent may survive into the cropped glyphs."""
    cw, ch = 9 * s, 16 * s
    im = Image.new("RGBA", (16 * cw, 16 * ch), bg)
    for code in range(256):
        g = render_glyph(code, color, s, 9)
        if scan and s >= 2:
            px = g.load()
            for y in range(g.height):
                if y % s == s - 1:
                    for x in range(g.width):
                        p = px[x, y]
                        if p[3]:
                            px[x, y] = (int(p[0] * scan), int(p[1] * scan), int(p[2] * scan), p[3])
        cell = add_glow(g, color, glow[0] * s, glow[1]) if glow else g
        base = Image.new("RGBA", (cw, ch), bg)
        base.alpha_composite(cell)
        im.alpha_composite(base, ((code % 16) * cw, (code // 16) * ch))
    return im, cw, ch
