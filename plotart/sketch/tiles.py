"""Large-format printing: split a sketch across several sheets (A4, A3 …) with overlap, crop marks
and labels – for posters and murals from an ordinary printer, or for plotting on several sheets.

Each tile is the sketch with every item shifted by the tile origin, so it renders exactly like the
whole picture. Limitation: a background() with a gradient is not shifted.
"""
from __future__ import annotations

import copy
import math
import re
from pathlib import Path
from typing import Callable

from ..core import PAPER_SIZES
from .core import IDENTITY, Item, Sketch
from .render_svg import render_svg


class TileError(ValueError):
    pass


def paper_size(paper: str, landscape: bool = False) -> tuple[float, float]:
    if paper not in PAPER_SIZES:
        raise TileError(f"Unbekanntes Papierformat {paper!r}. Möglich: {', '.join(PAPER_SIZES)}")
    w, h = PAPER_SIZES[paper]
    return (max(w, h), min(w, h)) if landscape else (min(w, h), max(w, h))


def plan_tiles(width_mm: float, height_mm: float, paper: str = "A4", landscape: bool | None = None,
               margin: float = 8.0, overlap: float = 10.0) -> dict:
    """Sheet layout for a print of width_mm × height_mm. landscape=None picks the orientation with fewer sheets."""
    if width_mm <= 0 or height_mm <= 0:
        raise TileError("Die Druckgröße muss größer als 0 sein")
    if landscape is None:
        options = [plan_tiles(width_mm, height_mm, paper, o, margin, overlap) for o in (False, True)]
        return min(options, key=lambda p: (p["cols"] * p["rows"], p["landscape"]))
    pw, ph = paper_size(paper, landscape)
    aw, ah = pw - 2 * margin, ph - 2 * margin
    if min(aw, ah) <= overlap + 5:
        raise TileError("Rand und Überlappung sind zu groß für dieses Papier")
    cols = max(1, math.ceil((width_mm - overlap) / (aw - overlap)))
    rows = max(1, math.ceil((height_mm - overlap) / (ah - overlap)))
    # all sheets equally large (no thin strip at the end): tw·cols − overlap·(cols−1) = width
    tw = (width_mm + (cols - 1) * overlap) / cols if cols > 1 else width_mm
    th = (height_mm + (rows - 1) * overlap) / rows if rows > 1 else height_mm
    tiles = [{"row": r, "col": c, "x": c * (tw - overlap), "y": r * (th - overlap), "w": tw, "h": th}
             for r in range(rows) for c in range(cols)]
    return {"paper": paper, "landscape": landscape, "page": (pw, ph), "printable": (aw, ah), "margin": margin,
            "overlap": overlap, "cols": cols, "rows": rows, "tiles": tiles, "size": (width_mm, height_mm)}


def crop_sketch(sk: Sketch, x: float, y: float, w: float, h: float) -> Sketch:
    """The region (x, y, w, h) of a sketch as a sketch of its own (in sketch units)."""
    t = copy.copy(sk)
    t.width, t.height = w, h
    t.items = [Item(it.kind, it.data, it.style, _shift(it.matrix or IDENTITY, x, y)) for it in sk.items]
    return t


def _shift(m, x, y):
    a, b, c, d, e, f = m
    return (a, b, c, d, e - x, f - y)


def print_size(sk: Sketch, print_width: float | None = None) -> tuple[float, float]:
    """Physical size in mm: sketches in mm at 1:1 unless print_width is given; pixel sketches need print_width."""
    if print_width:
        return float(print_width), float(print_width) * sk.height / sk.width
    if sk.unit == "mm":
        return sk.width, sk.height
    raise TileError("Bei Skizzen in Pixeln bitte die Druckbreite in mm angeben (z. B. 1000)")


def export_tiles(sk: Sketch, out_dir: str | Path, paper: str = "A4", landscape: bool | None = None,
                 print_width: float | None = None, overlap: float = 10.0, margin: float = 8.0, dpi: int = 200,
                 formats=("png", "pdf", "svg"), title: str = "",
                 progress: Callable[[int, int], None] | None = None) -> dict:
    """Write the sheets: tafel_R-S.png (with marks), alle_blaetter.pdf, tafel_R-S.svg and uebersicht.png."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise TileError("Großformat braucht Pillow: pip install Pillow") from None
    from .data import DataError
    from .export import render_png
    from .fonts import find_font

    width_mm, height_mm = print_size(sk, print_width)
    plan = plan_tiles(width_mm, height_mm, paper, landscape, margin, overlap)
    k = sk.width / width_mm                        # sketch units per mm
    px = dpi / 25.4                                # pixels per mm
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    try:
        font = ImageFont.truetype(find_font("sans"), max(10, round(3.2 * px)))
    except (OSError, DataError):
        font = ImageFont.load_default()
    n = len(plan["tiles"])
    pages, files = [], []
    for i, t in enumerate(plan["tiles"]):
        tile = crop_sketch(sk, t["x"] * k, t["y"] * k, t["w"] * k, t["h"] * k)
        name = f"tafel_{t['row'] + 1}-{t['col'] + 1}"
        if "png" in formats or "pdf" in formats:
            from io import BytesIO
            art = Image.open(BytesIO(render_png(tile, scale=px / k))).convert("RGBA")
            page = Image.new("RGB", (round(plan["page"][0] * px), round(plan["page"][1] * px)), "white")
            m = round(margin * px)
            page.paste(art, (m, m), art)
            _marks(ImageDraw.Draw(page), plan, t, px, font, f"{title + ' – ' if title else ''}Blatt {i + 1} von {n} · "
                   f"Reihe {t['row'] + 1}, Spalte {t['col'] + 1}")
            if "png" in formats:
                page.save(out / f"{name}.png", dpi=(dpi, dpi))
                files.append(f"{name}.png")
            pages.append(page)
        if "svg" in formats:
            svg = render_svg(tile)
            svg = re.sub(r'(<svg[^>]*?) width="[^"]*" height="[^"]*"', lambda mt: f'{mt.group(1)} width="{t["w"]:.2f}mm" '
                         f'height="{t["h"]:.2f}mm"', svg, count=1)
            (out / f"{name}.svg").write_text(svg, encoding="utf-8")
            files.append(f"{name}.svg")
        if progress:
            progress(i + 1, n)
    if "pdf" in formats and pages:
        pages[0].save(out / "alle_blaetter.pdf", save_all=True, append_images=pages[1:], resolution=dpi)
        files.append("alle_blaetter.pdf")
    _overview(sk, plan, k, font).save(out / "uebersicht.png")
    files.append("uebersicht.png")
    return {"dir": str(out), "sheets": n, "cols": plan["cols"], "rows": plan["rows"], "paper": paper,
            "landscape": plan["landscape"], "size_mm": (round(width_mm, 1), round(height_mm, 1)), "files": files}


def _marks(d, plan, t, px, font, label):
    """Crop marks at the tile corners, overlap ticks (where the next sheet goes) and a label – all in the margin."""
    m = plan["margin"]
    x0, y0, x1, y1 = m, m, m + t["w"], m + t["h"]
    gap, ln, grey = 1.5, min(5.0, m - 2), (90, 90, 90)
    w = max(1, round(0.2 * px))
    for cx, sx in ((x0, -1), (x1, 1)):
        for cy, sy in ((y0, -1), (y1, 1)):
            d.line([((cx + sx * gap) * px, cy * px), ((cx + sx * (gap + ln)) * px, cy * px)], fill=grey, width=w)
            d.line([(cx * px, (cy + sy * gap) * px), (cx * px, (cy + sy * (gap + ln)) * px)], fill=grey, width=w)
    ov = plan["overlap"]
    blue = (40, 110, 220)
    if t["col"] < plan["cols"] - 1:                 # the right neighbour starts here (glue area to the right)
        xo = x1 - ov
        for cy in (y0 - gap, y1 + gap):
            d.line([(xo * px, cy * px), (xo * px, (cy - ln if cy < y0 else cy + ln) * px)], fill=blue, width=w)
    if t["row"] < plan["rows"] - 1:                 # the sheet below starts here
        yo = y1 - ov
        for cx in (x0 - gap, x1 + gap):
            d.line([(cx * px, yo * px), ((cx - ln if cx < x0 else cx + ln) * px, yo * px)], fill=blue, width=w)
    d.text(((x0 + 4) * px, (y1 + gap + 1) * px), label, fill=grey, font=font)     # right of the corner mark


def _overview(sk, plan, k, font):
    """Small picture of the whole work with the sheet grid and numbers."""
    from io import BytesIO

    from PIL import Image, ImageDraw
    from .export import render_png
    scale = 900 / max(sk.width, sk.height)
    img = Image.open(BytesIO(render_png(sk, scale=scale))).convert("RGB")
    d = ImageDraw.Draw(img)
    s = scale * k                                    # overview pixels per mm
    for i, t in enumerate(plan["tiles"]):
        box = (t["x"] * s, t["y"] * s, (t["x"] + t["w"]) * s, (t["y"] + t["h"]) * s)
        d.rectangle(box, outline=(220, 40, 60), width=2)
        d.text((box[0] + 6, box[1] + 4), str(i + 1), fill=(220, 40, 60), font=font)
    return img
