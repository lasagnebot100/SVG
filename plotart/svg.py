"""SVG export (mm units, Inkscape layers – works with AxiDraw, vpype, Inkscape, iDraw …)."""
from __future__ import annotations

import html
import json

from .core import Drawing


def _fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def path_data(path) -> str:
    pts = [f"{_fmt(x)} {_fmt(y)}" for x, y in path]
    return "M" + pts[0] + "L" + " ".join(pts[1:])


def to_svg(drawing: Drawing, background: str | None = None) -> str:
    w, h = _fmt(drawing.width), _fmt(drawing.height)
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
        f'width="{w}mm" height="{h}mm" viewBox="0 0 {w} {h}">',
    ]
    if drawing.meta:
        meta = html.escape(json.dumps(drawing.meta, ensure_ascii=False))
        out.append(f"<metadata><plotart>{meta}</plotart></metadata>")
    if background:
        out.append(f'<rect width="{w}" height="{h}" fill="{background}"/>')
    for layer in sorted(drawing.layers):
        color = drawing.colors.get(layer, "#000000")
        out.append(
            f'<g inkscape:groupmode="layer" inkscape:label="{layer} Stift {layer}" '
            f'id="layer{layer}" fill="none" stroke="{color}" '
            f'stroke-width="{_fmt(drawing.pen_width)}" stroke-linecap="round" '
            f'stroke-linejoin="round">'
        )
        for p in drawing.layers[layer]:
            out.append(f'<path d="{path_data(p)}"/>')
        out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)


def to_png(drawing: Drawing, filename: str, px_per_mm: float = 4.0,
           background: str = "#fbfaf7") -> None:
    """Raster preview (needs Pillow)."""
    from PIL import Image, ImageDraw

    s = px_per_mm
    img = Image.new("RGB", (int(drawing.width * s), int(drawing.height * s)), background)
    d = ImageDraw.Draw(img)
    width = max(1, round(drawing.pen_width * s))
    for layer in sorted(drawing.layers):
        color = drawing.colors.get(layer, "#000000")
        for p in drawing.layers[layer]:
            d.line([(x * s, y * s) for x, y in p], fill=color, width=width, joint="curve")
    img.save(filename)
