#!/usr/bin/env python3
"""One picture of food: a slice of dark chocolate layer cake.

Pure Python standard library only. Builds the picture pixel by pixel
into a byte buffer and writes a PNG with a hand-rolled encoder
(zlib + struct, no PIL). Runs with no network access.
"""
import math
import os
import struct
import zlib

W = H = 900
OUT = "/output/entry.png"

buf = bytearray(W * H * 3)


def clamp(v, lo=0, hi=255):
    return lo if v < lo else hi if v > hi else v


def set_px(x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = r
        buf[i + 1] = g
        buf[i + 2] = b


def blend_px(x, y, r, g, b, a):
    if 0 <= x < W and 0 <= y < H and a > 0:
        i = (y * W + x) * 3
        if a >= 1.0:
            buf[i] = r
            buf[i + 1] = g
            buf[i + 2] = b
        else:
            buf[i] = int(buf[i] + (r - buf[i]) * a)
            buf[i + 1] = int(buf[i + 1] + (g - buf[i + 1]) * a)
            buf[i + 2] = int(buf[i + 2] + (b - buf[i + 2]) * a)


def mix(c1, c2, t):
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))


def noise2(x, y):
    """Cheap deterministic hash noise in [0, 1)."""
    n = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    n ^= n >> 13
    n = (n * 1274126177) & 0xFFFFFFFF
    n ^= n >> 16
    return (n & 0xFF) / 255.0


def paint_background():
    """Warm dark backdrop: vertical gradient + warm glow + vignette."""
    top = (52, 30, 18)
    mid = (40, 22, 13)
    bot = (24, 13, 8)
    gx, gy = 360.0, 60.0
    r2 = 780.0 * 780.0
    for y in range(H):
        t = y / (H - 1)
        if t < 0.55:
            base = mix(top, mid, t / 0.55)
        else:
            base = mix(mid, bot, (t - 0.55) / 0.45)
        row = y * W * 3
        for x in range(W):
            dx = x - gx
            dy = y - gy
            d2 = dx * dx * 0.7 + dy * dy
            g = 1.0 - d2 / r2
            if g > 0:
                r = base[0] + int(64 * g)
                gg = base[1] + int(34 * g)
                b = base[2] + int(14 * g)
            else:
                r, gg, b = base
            cx = (x - 450) / 450.0
            cy = (y - 450) / 450.0
            vd = cx * cx + cy * cy
            if vd > 0.55:
                f = 1.0 - 0.30 * min(1.0, (vd - 0.55) / 0.45)
                r = int(r * f)
                gg = int(gg * f)
                b = int(b * f)
            i = row + x * 3
            buf[i] = clamp(r)
            buf[i + 1] = clamp(gg)
            buf[i + 2] = clamp(b)


def fill_ellipse(cx, cy, rx, ry, color, alpha=1.0):
    x0 = max(0, int(cx - rx))
    x1 = min(W - 1, int(cx + rx) + 1)
    y0 = max(0, int(cy - ry))
    y1 = min(H - 1, int(cy + ry) + 1)
    for y in range(y0, y1 + 1):
        ny = (y - cy) / ry
        w = rx * math.sqrt(max(0.0, 1.0 - ny * ny))
        xa = max(x0, int(cx - w))
        xb = min(x1, int(cx + w))
        for x in range(xa, xb + 1):
            if alpha >= 1.0:
                set_px(x, y, color[0], color[1], color[2])
            else:
                blend_px(x, y, color[0], color[1], color[2], alpha)


def fill_poly(pts, fn):
    """Scanline polygon fill; fn(x, y) paints each inside pixel."""
    ys = [p[1] for p in pts]
    y0 = max(0, int(min(ys)))
    y1 = min(H - 1, int(max(ys)) + 1)
    n = len(pts)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x1, y1v = pts[i]
            x2, y2v = pts[(i + 1) % n]
            if (y1v <= y < y2v) or (y2v <= y < y1v):
                xs.append(x1 + (y - y1v) * (x2 - x1) / (y2v - y1v))
        if len(xs) < 2:
            continue
        xs.sort()
        xa = max(0, int(xs[0]))
        xb = min(W - 1, int(xs[-1]))
        for x in range(xa, xb + 1):
            fn(x, y)


def soft_disc(cx, cy, r, color, alpha):
    """Filled disc with a soft falloff edge."""
    x0 = max(0, int(cx - r))
    x1 = min(W - 1, int(cx + r) + 1)
    y0 = max(0, int(cy - r))
    y1 = min(H - 1, int(cy + r) + 1)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
            if d < 1.0:
                a = alpha * (1.0 - d) * (1.0 - d)
                blend_px(x, y, color[0], color[1], color[2], a)


# ---- cake slice geometry ---------------------------------------------
# Front (cut) face triangle: tip T, top-back TR, bottom-back BR.
T = (240.0, 655.0)
TR = (640.0, 315.0)
BR = (645.0, 700.0)
# Depth offsets for the top surface and the right side face.
T2 = (305.0, 615.0)
TR2 = (705.0, 275.0)
BR2 = (710.0, 660.0)


def top_y(x):
    return T[1] + (x - T[0]) * (TR[1] - T[1]) / (TR[0] - T[0])


def bot_y(x):
    return T[1] + (x - T[0]) * (BR[1] - T[1]) / (BR[0] - T[0])


SPONGE_D = (56, 28, 15)
SPONGE_L = (82, 44, 23)
CREAM = (248, 233, 206)
CREAM_SH = (226, 203, 164)
GANACHE = (30, 14, 7)
GANACHE_HI = (122, 70, 34)


def face_px(x, y):
    """One pixel of the cake's cut face: sponge / cream layers."""
    yt = top_y(x)
    yb = bot_y(x)
    f = (y - yt) / max(1.0, yb - yt)
    n = noise2(x, y)
    n2 = noise2(x * 3 + 11, y * 3 + 7)
    if f < 0.09:
        # ganache band hugging the top edge, with a sheen line
        c = list(GANACHE)
        if 0.015 < f < 0.05:
            c = [min(255, v + 55) for v in c]
        if n2 > 0.90:
            c = [min(255, v + 30) for v in c]
    elif f < 0.37:
        c = list(SPONGE_L if n > 0.45 else SPONGE_D)
        if n2 > 0.92:
            c = [max(0, v - 18) for v in c]
    elif f < 0.46:
        c = list(CREAM if n > 0.5 else CREAM_SH)
    elif f < 0.71:
        c = list(SPONGE_L if n > 0.45 else SPONGE_D)
        if n2 > 0.92:
            c = [max(0, v - 18) for v in c]
    elif f < 0.80:
        c = list(CREAM if n > 0.5 else CREAM_SH)
    else:
        c = list(SPONGE_L if n > 0.45 else SPONGE_D)
        if n2 > 0.92:
            c = [max(0, v - 18) for v in c]
    # gentle shading: darker towards the bottom and the back edge
    shade = 1.0 - 0.16 * f - 0.08 * (x - T[0]) / (TR[0] - T[0])
    jit = (n - 0.5) * 10
    set_px(x, y,
           clamp(int(c[0] * shade + jit)),
           clamp(int(c[1] * shade + jit)),
           clamp(int(c[2] * shade + jit)))


def side_px(x, y):
    """Right side face: darker sponge with two thin cream bands."""
    f = (y - TR2[1]) / max(1.0, BR2[1] - TR2[1])
    n = noise2(x, y)
    if 0.30 < f < 0.37 or 0.62 < f < 0.69:
        c = list(CREAM_SH)
    else:
        c = list((60, 31, 17) if n > 0.45 else (50, 25, 14))
    shade = 1.0 - 0.10 * f
    set_px(x, y, clamp(int(c[0] * shade)), clamp(int(c[1] * shade)),
           clamp(int(c[2] * shade)))


def top_px(x, y):
    """Ganache top surface with a long sheen streak."""
    # fraction across the parallelogram width (0 at front edge)
    # front edge T->TR, back edge T2->TR2; use y offset from front edge
    yt = top_y(x)
    yb = yt - 58.0  # approx back edge offset
    s = (yt - y) / max(1.0, yt - yb)
    n = noise2(x, y)
    c = [46, 22, 11]
    sheen = math.exp(-((s - 0.38) / 0.20) ** 2)
    c[0] = int(c[0] + 88 * sheen + (n - 0.5) * 8)
    c[1] = int(c[1] + 48 * sheen + (n - 0.5) * 6)
    c[2] = int(c[2] + 22 * sheen + (n - 0.5) * 4)
    # second, weaker streak near the back edge
    sheen2 = math.exp(-((s - 0.78) / 0.12) ** 2)
    c[0] = int(c[0] + 30 * sheen2)
    c[1] = int(c[1] + 16 * sheen2)
    c[2] = int(c[2] + 8 * sheen2)
    set_px(x, y, clamp(c[0]), clamp(c[1]), clamp(c[2]))


DRIPS = [
    (300, 20, 48), (355, 23, 80), (412, 19, 58),
    (468, 24, 90), (525, 20, 64), (582, 22, 82),
    (625, 18, 46),
]


def draw_drips():
    """Glossy ganache drips hanging from the top edge of the face."""
    for xd, w, length in DRIPS:
        yt = top_y(xd) - 4
        r = w / 2.0
        y_end = yt + length
        x0 = max(0, int(xd - r - 2))
        x1 = min(W - 1, int(xd + r + 2))
        y0 = max(0, int(yt))
        y1 = min(H - 1, int(y_end + r))
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                dx = abs(x - xd)
                if y <= y_end:
                    if dx > r:
                        continue
                else:
                    if math.sqrt(dx * dx + (y - y_end) ** 2) > r:
                        continue
                # gloss stripe on the left side of each drip
                n = noise2(x, y)
                if abs(x - (xd - r * 0.35)) < 2.6:
                    c = (128, 74, 36)
                elif dx > r * 0.72:
                    c = (18, 8, 4)
                else:
                    c = (34, 16, 8)
                set_px(x, y,
                       clamp(c[0] + int((n - 0.5) * 8)),
                       clamp(c[1] + int((n - 0.5) * 6)),
                       clamp(c[2] + int((n - 0.5) * 4)))


def draw_dollop():
    """Whipped-cream dollop: stacked soft ellipses with a swirl tip."""
    cx, cy = 520, 402
    fill_ellipse(cx, cy + 6, 58, 30, (232, 208, 166))
    fill_ellipse(cx, cy, 56, 30, (255, 246, 228))
    fill_ellipse(cx, cy - 16, 42, 24, (255, 248, 232))
    fill_ellipse(cx + 2, cy - 30, 26, 17, (255, 250, 238))
    fill_ellipse(cx + 6, cy - 42, 13, 10, (255, 250, 240))
    # swirl shading arcs (darker cream, thin)
    for ang in range(0, 300, 12):
        a = math.radians(ang)
        x = int(cx + 34 * math.cos(a))
        y = int(cy - 4 + 18 * math.sin(a))
        soft_disc(x, y, 3, (214, 186, 140), 0.35)
    # soft shadow where the dollop meets the cake
    fill_ellipse(cx, cy + 26, 52, 10, (20, 10, 5), 0.25)


def draw_raspberry(cx, cy, r):
    """A raspberry built from drupelet bumps."""
    fill_ellipse(cx, cy, r, r, (148, 16, 42))
    for gy in range(-2, 3):
        for gx in range(-2, 3):
            ox = gx * r * 0.42
            oy = gy * r * 0.42
            if ox * ox + oy * oy > (r * 0.82) ** 2:
                continue
            shade = noise2(cx + int(ox), cy + int(oy))
            col = (190, 34, 58) if shade > 0.55 else (168, 22, 48)
            if shade < 0.2:
                col = (128, 12, 36)
            soft_disc(cx + ox, cy + oy, r * 0.26, col, 0.95)
            soft_disc(cx + ox - r * 0.08, cy + oy - r * 0.10,
                      r * 0.09, (255, 130, 150), 0.8)
    soft_disc(cx - r * 0.3, cy - r * 0.35, r * 0.28, (255, 110, 135), 0.45)


def draw_blueberry(cx, cy, r):
    fill_ellipse(cx, cy, r, r, (52, 44, 96))
    fill_ellipse(cx - r * 0.25, cy - r * 0.3, r * 0.55, r * 0.5,
                 (92, 82, 150))
    soft_disc(cx - r * 0.3, cy - r * 0.35, r * 0.25, (190, 185, 235), 0.7)
    soft_disc(cx + r * 0.1, cy - r * 0.1, r * 0.14, (30, 26, 60), 0.9)


def draw_curl(cx, cy, r0, a0, a1):
    """A chocolate curl: dark arc with a lighter edge."""
    steps = 26
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        x = cx + r0 * math.cos(a)
        y = cy + r0 * 0.8 * math.sin(a)
        soft_disc(x, y, 6.5, (42, 21, 11), 1.0)
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        x = cx + r0 * math.cos(a) - 2
        y = cy + r0 * 0.8 * math.sin(a) - 2
        soft_disc(x, y, 2.2, (118, 66, 34), 0.9)


def draw_crumbs():
    """A few crumbs and a chocolate sauce drizzle on the plate."""
    for i in range(18):
        x = 300 + int(noise2(i * 17, 3) * 380)
        y = 742 + int(noise2(i * 17, 9) * 34)
        r = 2 + int(noise2(i * 31, 5) * 3)
        soft_disc(x, y, r, (48, 24, 12), 0.9)
    # (sauce drizzle removed: it read as a stray squiggle at the plate edge)


def save_png(path, w, h, data):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += data[y * w * 3:(y + 1) * w * 3]
    comp = zlib.compress(bytes(raw), 6)

    def chunk(typ, payload):
        out = struct.pack(">I", len(payload)) + typ + payload
        out += struct.pack(">I", zlib.crc32(typ + payload) & 0xFFFFFFFF)
        return out

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    paint_background()
    # plate shadow, then plate
    fill_ellipse(450, 722, 365, 96, (10, 5, 3), 0.45)
    fill_ellipse(450, 700, 355, 108, (233, 220, 196))
    fill_ellipse(450, 700, 330, 96, (247, 239, 220))
    fill_ellipse(450, 734, 300, 62, (210, 190, 160), 0.30)
    # soft shadow of the cake on the plate
    fill_ellipse(470, 692, 295, 52, (20, 10, 5), 0.26)
    # cake: side face, cut face, ganache top
    fill_poly([TR, TR2, BR2, BR], side_px)
    fill_poly([T, TR, BR], face_px)
    fill_poly([T, TR, TR2, T2], top_px)
    draw_drips()
    # toppings on the ganache top
    draw_curl(385, 512, 20, 200, 20)
    draw_curl(448, 468, 16, 180, 350)
    draw_dollop()
    draw_blueberry(566, 372, 16)
    draw_raspberry(612, 356, 27)
    draw_raspberry(658, 392, 20)
    draw_crumbs()
    size = save_png(OUT, W, H, buf)
    print(f"wrote {OUT}: {W}x{H}, {size} bytes")


if __name__ == "__main__":
    main()
