# -*- coding: utf-8 -*-
r"""Generate the light and dark icons for the ICSPL Export buttons.

Standard library only (zlib + struct), so it runs on any CPython 3 install
with no Pillow and no SVG converter. Run from the project root:

    python tools\make_icons.py

Writes icon.png (light theme) and icon.dark.png (dark theme) into each
pushbutton folder. Icons are 96 x 96 RGBA with transparent corners.
Run with CPython 3, not IronPython.
"""

import os
import struct
import zlib

SIZE = 96
SUPERSAMPLE = 3  # 3 x 3 sample points per pixel for smooth edges

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PANEL_DIR = os.path.join(ROOT, "ICSPL Export.extension", "Export.tab", "Export.panel")

WHITE = (255, 255, 255)

# (button folder name, accent colours per theme, glyph)
BUTTONS = [
    ("PDF Print", {"light": (198, 40, 40), "dark": (239, 83, 80)}, "pdf"),
    ("DWG Export", {"light": (21, 101, 192), "dark": (66, 165, 245)}, "dwg"),
    ("NWC Export", {"light": (239, 108, 0), "dark": (255, 167, 38)}, "nwc"),
    ("IFC Export", {"light": (46, 125, 50), "dark": (102, 187, 106)}, "ifc"),
]


def in_rrect(x, y, x0, y0, x1, y1, r):
    if x < x0 or x > x1 or y < y0 or y > y1:
        return False
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def in_poly(x, y, pts):
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def near_segment(x, y, ax, ay, bx, by, w):
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / length2))
    px, py = ax + t * dx, ay + t * dy
    return (x - px) ** 2 + (y - py) ** 2 <= (w / 2.0) ** 2


def hit(kind, args, x, y):
    if kind == "rect":
        x0, y0, x1, y1 = args
        return x0 <= x <= x1 and y0 <= y <= y1
    if kind == "rrect":
        return in_rrect(x, y, *args)
    if kind == "poly":
        return in_poly(x, y, args)
    if kind == "seg":
        return near_segment(x, y, *args)
    raise ValueError("unknown shape: {}".format(kind))


def glyph_layers(glyph, accent):
    """Ordered (shape kind, args, colour) layers, bottom first."""
    layers = [("rrect", (4, 4, 92, 92, 18), accent)]
    page = ("rrect", (30, 16, 70, 80, 3), WHITE)
    if glyph == "pdf":
        layers.append(page)
        layers.append(("rect", (36, 34, 64, 37), accent))
        layers.append(("rect", (36, 42, 64, 45), accent))
        layers.append(("rect", (36, 56, 64, 68), accent))  # label band
    elif glyph == "dwg":
        layers.append(page)
        for x in (40, 52, 64):
            layers.append(("rect", (x - 1, 30, x + 1, 66), accent))
        for y in (36, 48, 60):
            layers.append(("rect", (36, y - 1, 68, y + 1), accent))
    elif glyph == "nwc":
        layers.append(("poly", [(48, 18), (72, 32), (72, 64), (48, 78), (24, 64), (24, 32)], WHITE))
        layers.append(("seg", (48, 48, 24, 32, 4), accent))
        layers.append(("seg", (48, 48, 72, 32, 4), accent))
        layers.append(("seg", (48, 48, 48, 78, 4), accent))
    elif glyph == "ifc":
        # three stacked floor slabs = a building model
        for y in (28, 48, 68):
            layers.append(("poly", [(20, y), (48, y - 8), (76, y), (48, y + 8)], WHITE))
    else:
        raise ValueError("unknown glyph: {}".format(glyph))
    return layers


def render(layers):
    """Composite the layers into rows of RGBA bytes."""
    total = float(SUPERSAMPLE * SUPERSAMPLE)
    rows = []
    for py in range(SIZE):
        row = bytearray(SIZE * 4)
        for px in range(SIZE):
            dst_r = dst_g = dst_b = dst_a = 0.0
            for kind, args, color in layers:
                hits = 0
                for sy in range(SUPERSAMPLE):
                    for sx in range(SUPERSAMPLE):
                        x = px + (sx + 0.5) / SUPERSAMPLE
                        y = py + (sy + 0.5) / SUPERSAMPLE
                        if hit(kind, args, x, y):
                            hits += 1
                if hits == 0:
                    continue
                sa = hits / total
                out_a = sa + dst_a * (1.0 - sa)
                dst_r = (color[0] * sa + dst_r * dst_a * (1.0 - sa)) / out_a
                dst_g = (color[1] * sa + dst_g * dst_a * (1.0 - sa)) / out_a
                dst_b = (color[2] * sa + dst_b * dst_a * (1.0 - sa)) / out_a
                dst_a = out_a
            row[px * 4:px * 4 + 4] = bytes((
                int(round(dst_r)), int(round(dst_g)), int(round(dst_b)),
                int(round(dst_a * 255)),
            ))
        rows.append(row)
    return rows


def write_png(path, rows):
    raw = b"".join(b"\x00" + bytes(row) for row in rows)

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)  # 8-bit RGBA
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", header))
        f.write(chunk(b"IDAT", zlib.compress(raw, 9)))
        f.write(chunk(b"IEND", b""))


def main():
    for name, colours, glyph in BUTTONS:
        folder = os.path.join(PANEL_DIR, name + ".pushbutton")
        if not os.path.isdir(folder):
            raise SystemExit("Missing button folder: {}".format(folder))
        for theme, filename in (("light", "icon.png"), ("dark", "icon.dark.png")):
            out = os.path.join(folder, filename)
            write_png(out, render(glyph_layers(glyph, colours[theme])))
            print("wrote {}".format(out))


if __name__ == "__main__":
    main()
