"""Full-colour SVG output of a sketch (fills, opacity, gradients, blend modes, text, images)."""
from __future__ import annotations

import base64
import html
import json

from ..svg import _fmt
from .color import Color, Gradient
from .core import Sketch

_CAPS = {"round": "round", "square": "butt", "project": "square"}
_VALIGN = {"top": "hanging", "center": "central", "bottom": "text-after-edge", "baseline": None}
_ANCHOR = {"left": "start", "center": "middle", "right": "end"}


class _Defs:
    def __init__(self):
        self.ids: dict[int, str] = {}
        self.out: list[str] = []

    def paint(self, p) -> tuple[str, float | None]:
        """Returns (paint attribute value, opacity or None)."""
        if p is None:
            return "none", None
        if isinstance(p, Color):
            return p.hex, (p.a if p.a < 1 else None)
        if isinstance(p, Gradient):
            gid = self.ids.get(id(p))
            if gid is None:
                gid = f"g{len(self.ids) + 1}"
                self.ids[id(p)] = gid
                stops = "".join(
                    f'<stop offset="{_fmt(o)}" stop-color="{c.hex}"'
                    + (f' stop-opacity="{_fmt(c.a)}"' if c.a < 1 else "") + "/>"
                    for o, c in p.stops)
                if p.kind == "linear":
                    x1, y1, x2, y2 = (_fmt(v) for v in p.coords)
                    self.out.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                                    f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{stops}</linearGradient>')
                else:
                    cx, cy, r = (_fmt(v) for v in p.coords)
                    self.out.append(f'<radialGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                                    f'cx="{cx}" cy="{cy}" r="{r}">{stops}</radialGradient>')
            return f"url(#{gid})", None
        raise TypeError(f"Unbekannte Farbe {p!r}")


def _style_attrs(style, defs: _Defs, cache: dict, text=False) -> str:
    key = (id(style), text)
    if key in cache:
        return cache[key][1]
    parts = []
    fill, fo = defs.paint(style.fill)
    parts.append(f'fill="{fill}"')
    if fo is not None:
        parts.append(f'fill-opacity="{_fmt(fo)}"')
    if style.stroke is not None and style.weight > 0:
        stroke, so = defs.paint(style.stroke)
        parts.append(f'stroke="{stroke}" stroke-width="{_fmt(style.weight)}"')
        if so is not None:
            parts.append(f'stroke-opacity="{_fmt(so)}"')
        if not text:
            cap = _CAPS.get(style.cap, "round")
            if cap != "butt":
                parts.append(f'stroke-linecap="{cap}"')
            if style.join != "miter":
                parts.append(f'stroke-linejoin="{style.join}"')
    if style.blend and style.blend not in ("normal", "blend"):
        parts.append(f'style="mix-blend-mode:{style.blend}"')
    s = " ".join(parts)
    cache[key] = (style, s)          # keep style alive so id() stays unique
    return s


def _path_d(subpaths, closed) -> str:
    out = []
    for segs, cl in zip(subpaths, closed):
        for seg in segs:
            out.append(seg[0] + " ".join(_fmt(v) for v in seg[1:]))
        if cl:
            out.append("Z")
    return "".join(out)


def render_svg(sk: Sketch, meta: dict | None = None, items=None) -> str:
    """SVG of the sketch (or of `items`, e.g. one animation frame, on the sketch's canvas)."""
    w, h, unit = _fmt(sk.width), _fmt(sk.height), sk.unit
    size_unit = "mm" if unit == "mm" else ""
    defs = _Defs()
    cache: dict = {}
    body: list[str] = []
    for it in (sk.items if items is None else items):
        d = it.data
        tr = ""
        if it.matrix is not None:
            # matrix entries need more precision than coordinates
            tr = ' transform="matrix(' + " ".join(f"{v:.6g}" for v in it.matrix) + ')"'
        k = it.kind
        if k == "background":
            fill, fo = defs.paint(d["paint"])
            op = f' fill-opacity="{_fmt(fo)}"' if fo is not None else ""
            body.append(f'<rect width="{w}" height="{h}" fill="{fill}"{op}/>')
            continue
        if k == "image":
            b64 = base64.b64encode(d["png"]).decode()
            rendering = "" if d["smooth"] else ' style="image-rendering:pixelated"'
            body.append(f'<image x="{_fmt(d["x"])}" y="{_fmt(d["y"])}" width="{_fmt(d["w"])}" '
                        f'height="{_fmt(d["h"])}" preserveAspectRatio="none"{rendering}{tr} '
                        f'xlink:href="data:image/png;base64,{b64}"/>')
            continue
        if k == "text":
            st = it.style
            attrs = _style_attrs(st, defs, cache, text=True)
            extra = f' font-size="{_fmt(st.text_size)}" font-family="{html.escape(st.text_font, quote=True)}"'
            anchor = _ANCHOR.get(st.text_align, "start")
            if anchor != "start":
                extra += f' text-anchor="{anchor}"'
            vb = _VALIGN.get(st.text_valign)
            if vb:
                extra += f' dominant-baseline="{vb}"'
            if "bold" in st.text_style:
                extra += ' font-weight="bold"'
            if "italic" in st.text_style:
                extra += ' font-style="italic"'
            body.append(f'<text x="{_fmt(d["x"])}" y="{_fmt(d["y"])}" {attrs}{extra}{tr}>'
                        f'{html.escape(d["s"])}</text>')
            continue
        attrs = _style_attrs(it.style, defs, cache)
        if k == "ellipse":
            if abs(d["rx"] - d["ry"]) < 1e-9:
                body.append(f'<circle cx="{_fmt(d["cx"])}" cy="{_fmt(d["cy"])}" r="{_fmt(d["rx"])}" {attrs}{tr}/>')
            else:
                body.append(f'<ellipse cx="{_fmt(d["cx"])}" cy="{_fmt(d["cy"])}" rx="{_fmt(d["rx"])}" '
                            f'ry="{_fmt(d["ry"])}" {attrs}{tr}/>')
        elif k == "rect":
            r = f' rx="{_fmt(d["r"])}"' if d["r"] > 0 else ""
            body.append(f'<rect x="{_fmt(d["x"])}" y="{_fmt(d["y"])}" width="{_fmt(d["w"])}" '
                        f'height="{_fmt(d["h"])}"{r} {attrs}{tr}/>')
        elif k == "path":
            rule = ' fill-rule="evenodd"' if d.get("evenodd") else ""
            body.append(f'<path d="{_path_d(d["subpaths"], d["closed"])}"{rule} {attrs}{tr}/>')

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'width="{w}{size_unit}" height="{h}{size_unit}" viewBox="0 0 {w} {h}">']
    if meta:
        out.append(f"<metadata><plotart>{html.escape(json.dumps(meta, ensure_ascii=False))}</plotart></metadata>")
    if defs.out:
        out.append("<defs>" + "".join(defs.out) + "</defs>")
    out.extend(body)
    out.append("</svg>")
    return "\n".join(out)
