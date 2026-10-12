"""Small image helpers shared by the generators (Pillow only)."""
import math

from PIL import Image, ImageFilter


def ps(s):
    """A Python string as a Plymouth-script string literal."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def glow(r, core_col, halo_col, reach=6.0, core=0.35, halo_gain=0.9, fade_edge=True):
    """A luminous dot: solid core of radius core*r, bright limb, long corona.
    The image is (2*ceil(r*reach)+1) px square; with fade_edge the corona
    reaches exactly zero at the border, so moving it leaves no square seams."""
    size = int(math.ceil(r * reach)) * 2 + 1
    ss = 3
    S = size * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    px = im.load()
    c = (S - 1) / 2
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - c, y - c) / ss / r
            if d <= core:
                px[x, y] = core_col + (255,)
                continue
            a = math.exp(-((d - core) / 0.55) ** 2) * 0.95 + halo_gain * 0.35 / (1 + (d * 1.3) ** 2.2)
            a = min(1.0, a)
            if fade_edge:
                t = min(1.0, max(0.0, (d / reach - 0.62) / 0.38))
                a *= 1 - t * t * (3 - 2 * t)
            t = min(1.0, (d - core) / 0.8)
            col = tuple(int(core_col[i] * (1 - t) + halo_col[i] * t) for i in range(3))
            if a > 0.003:
                px[x, y] = col + (int(a * 255),)
    return im.resize((size, size), Image.LANCZOS)


def blob(r, col, alpha=1.0, sigma=0.45):
    """A soft gaussian disc of radius ~r (alpha falls to ~0 at 2r)."""
    size = int(math.ceil(r * 2.4)) * 2 + 1
    im = Image.new("RGBA", (size, size), col + (0,))
    px = im.load()
    c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - c, y - c) / max(r, 0.01)
            a = alpha * math.exp(-(d * d) / (2 * sigma * sigma * 4))
            if d > 2.3:
                a *= max(0.0, (2.4 - d) / 0.1)
            px[x, y] = col + (int(round(255 * min(1.0, a))),)
    return im


def hband(w, h, col, a_top, a_mid, a_bottom, mid=0.5):
    """A horizontal band whose alpha goes a_top -> a_mid (at mid) -> a_bottom."""
    im = Image.new("RGBA", (1, h), col + (0,))
    for y in range(h):
        t = y / max(1, h - 1)
        if t < mid:
            u = t / mid
            a = a_top + (a_mid - a_top) * (u * u * (3 - 2 * u))
        else:
            u = (t - mid) / (1 - mid)
            a = a_mid + (a_bottom - a_mid) * (u * u * (3 - 2 * u))
        im.putpixel((0, y), col + (int(round(255 * a)),))
    return im.resize((w, h), Image.NEAREST)


def soften(im, radius):
    return im.filter(ImageFilter.GaussianBlur(radius))
