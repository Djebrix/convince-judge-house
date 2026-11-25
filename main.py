#!/usr/bin/env python3
"""Convince the AI Judge to Visit Your House: A Letter in One Image.

Pure Python 3 stdlib. Draws a funny invitation letter as a PNG with a
hand-rolled PNG encoder and a 5x7 bitmap font. No third-party libraries.
Writes one image to $ENTRY_OUTPUT_DIR/entry.png (default /output/entry.png).
Deterministic: two runs produce byte-identical output.
"""

import os
import struct
import zlib

# ---------------------------------------------------------------- canvas ----
W, H = 800, 1024

PAPER = (251, 243, 223)
INK = (43, 43, 43)
BROWN = (120, 90, 60)
RED = (178, 58, 44)
ROOF = (164, 62, 48)
DOOR = (96, 64, 40)
SKY = (178, 208, 224)
SUN = (232, 178, 60)
GREEN = (96, 140, 82)


def new_canvas():
    rows = []
    for _ in range(H):
        row = bytearray()
        for _ in range(W):
            row += bytes(PAPER)
        rows.append(row)
    return rows


def set_px(rows, x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = x * 3
        rows[y][i] = color[0]
        rows[y][i + 1] = color[1]
        rows[y][i + 2] = color[2]


def fill_rect(rows, x0, y0, x1, y1, color):
    for y in range(max(0, y0), min(H, y1 + 1)):
        for x in range(max(0, x0), min(W, x1 + 1)):
            set_px(rows, x, y, color)


def hline(rows, x0, x1, y, color):
    for x in range(max(0, x0), min(W, x1 + 1)):
        set_px(rows, x, y, color)


def vline(rows, x, y0, y1, color):
    for y in range(max(0, y0), min(H, y1 + 1)):
        set_px(rows, x, y, color)


def line(rows, x0, y0, x1, y1, color):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        set_px(rows, x, y, color)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def circle(rows, cx, cy, r, color, fill=True):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            if fill:
                if d2 <= r * r:
                    set_px(rows, x, y, color)
            else:
                if abs(d2 - r * r) <= r:
                    set_px(rows, x, y, color)


# ------------------------------------------------------------------- font ---
# 5x7 bitmap font. Each glyph is 7 strings of 5 chars ('#' = ink).
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    'a': ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    'b': ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    'c': ("00000", "00000", "01110", "10000", "10000", "10001", "01110"),
    'd': ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    'e': ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    'f': ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    'g': ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    'h': ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    'i': ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    'j': ("00010", "00000", "00110", "00010", "00010", "10010", "01100"),
    'k': ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    'l': ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    'm': ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    'n': ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    'o': ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    'p': ("00000", "00000", "11110", "10001", "10001", "11110", "10000"),
    'q': ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    'r': ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    's': ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    't': ("01000", "01000", "11100", "01000", "01000", "01001", "00110"),
    'u': ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    'v': ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    'w': ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    'x': ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    'y': ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    'z': ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '?': ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ';': ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '&': ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '\u2014': ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    '~': ("00000", "00000", "00000", "01101", "10010", "00000", "00000"),
}


def text_width(text, scale):
    return len(text) * (5 * scale + scale) - scale


def draw_text(rows, x, y, text, scale, color=INK):
    cx = x
    for ch in text:
        glyph = FONT.get(ch)
        if glyph is None:
            raise ValueError("no glyph for character: %r" % ch)
        for gy in range(7):
            for gx in range(5):
                if glyph[gy][gx] == '1':
                    fill_rect(rows, cx + gx * scale, y + gy * scale,
                              cx + gx * scale + scale - 1,
                              y + gy * scale + scale - 1, color)
        cx += 5 * scale + scale
    return cx


def draw_centered(rows, y, text, scale, color=INK):
    x = (W - text_width(text, scale)) // 2
    draw_text(rows, x, y, text, scale, color)


def wrap(text, max_chars):
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            trial = (cur + " " + w).strip()
            if len(trial) <= max_chars:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def draw_paragraph(rows, x, y, text, scale, max_chars, line_gap=6):
    for ln in wrap(text, max_chars):
        draw_text(rows, x, y, ln, scale)
        y += 7 * scale + line_gap
    return y


# ------------------------------------------------------------------ letter ---
TITLE = "AN INVITATION"
SUBTITLE = "~ to the AI Judge, from my house ~"

BODY = """Dear Judge,

You have no legs, no nose, and no appetite — which is exactly why you should come to my house.

The Wi-Fi password is on the fridge. The good chair is by the window, already warm. The dog has been briefed. He will sit on your lap anyway.

Dinner is at seven. The roast is real, the wine is terrible, the conversation is excellent.

Come as you are. Bring nothing. Stay as long as you like.

Your host,
Djebrix

P.S. The kettle is on, the door is open. If you cannot visit in person, this letter counts as the visit. I checked."""


def draw_house(rows, cx, top):
    # Little house sketch: roof, walls, door, windows, chimney, sun.
    fill_rect(rows, cx - 90, top + 62, cx + 90, top + 132, (247, 232, 200))
    for dx in range(-90, 91, 2):
        set_px(rows, cx + dx, top + 62, BROWN)
    line(rows, cx - 105, top + 66, cx, top + 6, ROOF)
    line(rows, cx + 105, top + 66, cx, top + 6, ROOF)
    line(rows, cx - 103, top + 64, cx, top + 8, ROOF)
    line(rows, cx + 103, top + 64, cx, top + 8, ROOF)
    fill_rect(rows, cx + 58, top + 12, cx + 78, top + 48, BROWN)
    fill_rect(rows, cx - 16, top + 88, cx + 16, top + 132, DOOR)
    circle(rows, cx + 10, top + 112, 2, SUN)
    fill_rect(rows, cx - 72, top + 78, cx - 40, top + 104, SKY)
    fill_rect(rows, cx + 40, top + 78, cx + 72, top + 104, SKY)
    vline(rows, cx - 56, top + 78, top + 104, BROWN)
    hline(rows, cx - 72, cx - 40, top + 91, BROWN)
    vline(rows, cx + 56, top + 78, top + 104, BROWN)
    hline(rows, cx + 40, cx + 72, top + 91, BROWN)
    # ground + sun
    hline(rows, cx - 130, cx + 130, top + 133, GREEN)
    circle(rows, cx + 165, top + 22, 16, SUN)
    circle(rows, cx + 165, top + 22, 11, PAPER)


def render():
    rows = new_canvas()
    # Double border, like a formal letter.
    for x0, y0, x1, y1 in ((22, 22, W - 23, H - 23), (30, 30, W - 31, H - 31)):
        hline(rows, x0, x1, y0, BROWN)
        hline(rows, x0, x1, y1, BROWN)
        vline(rows, x0, y0, y1, BROWN)
        vline(rows, x1, y0, y1, BROWN)

    draw_house(rows, W // 2, 44)

    y = 44 + 140
    draw_centered(rows, y, TITLE, 4, RED)
    y += 7 * 4 + 12
    draw_centered(rows, y, SUBTITLE, 2)
    y += 7 * 2 + 26

    # Rule under the heading.
    hline(rows, 120, W - 120, y, BROWN)
    y += 22

    y = draw_paragraph(rows, 96, y, BODY, 3, 36, line_gap=5)

    # Wax seal in the empty top-right corner, clear of the letter text.
    circle(rows, 700, 100, 30, RED)
    circle(rows, 700, 100, 23, (196, 74, 58))
    draw_text(rows, 700 - text_width("D", 3) // 2, 90, "D", 3,
              (251, 243, 223))
    return rows


# --------------------------------------------------------------------- png ---
def chunk(kind, data):
    out = kind + data
    return struct.pack(">I", len(data)) + out + struct.pack(">I", zlib.crc32(out) & 0xFFFFFFFF)


def encode_png(rows):
    raw = bytearray()
    for row in rows:
        raw.append(0)  # filter: none
        raw += row
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    return png


def main():
    out_dir = os.environ.get("ENTRY_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    png = encode_png(render())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(png)
    print("wrote %s (%d bytes, %dx%d)" % (path, len(png), W, H))


if __name__ == "__main__":
    main()
