"""Import SVG files as polylines (paths incl. arcs, basic shapes, groups with transforms)."""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from .color import Color, to_color
from .data import DataError, read_text

_NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
_CMD = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])([^MmLlHhVvCcSsQqTtAaZz]*)")


@dataclass
class SvgShape:
    paths: list = field(default_factory=list)      # [(points, closed), …]
    fill: Color | None = None
    stroke: Color | None = None
    stroke_width: float = 1.0


@dataclass
class SvgDrawing:
    shapes: list
    x: float
    y: float
    width: float
    height: float

    def __repr__(self):
        return f"SvgDrawing({len(self.shapes)} Formen, {self.width:g} × {self.height:g})"

    def all_paths(self):
        for s in self.shapes:
            yield from s.paths


# ------------------------------------------------------------------------ transforms
def _mul(m, n):
    a1, b1, c1, d1, e1, f1 = m
    a2, b2, c2, d2, e2, f2 = n
    return (a1 * a2 + c1 * b2, b1 * a2 + d1 * b2, a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


def _parse_transform(s: str):
    m = (1, 0, 0, 1, 0, 0)
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", s or ""):
        v = [float(x) for x in _NUM.findall(args)]
        if name == "matrix" and len(v) == 6:
            t = tuple(v)
        elif name == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate":
            a = math.radians(v[0])
            t = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0)
            if len(v) == 3:
                t = _mul(_mul((1, 0, 0, 1, v[1], v[2]), t), (1, 0, 0, 1, -v[1], -v[2]))
        elif name == "skewX":
            t = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif name == "skewY":
            t = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        else:
            continue
        m = _mul(m, t)
    return m


def _apply(m, pts):
    return [(m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]) for x, y in pts]


# ------------------------------------------------------------------------ path data
def _cubic(p0, p1, p2, p3, n):
    return [((1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t * t * p2[0] + t ** 3 * p3[0],
             (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t * t * p2[1] + t ** 3 * p3[1])
            for t in (i / n for i in range(1, n + 1))]


def _quad(p0, p1, p2, n):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in (i / n for i in range(1, n + 1))]


def _arc(p0, rx, ry, phi, large, sweep, p1, n_per_rad=6):
    """SVG elliptical arc (endpoint parametrisation) → points (excluding p0)."""
    if rx == 0 or ry == 0:
        return [p1]
    rx, ry = abs(rx), abs(ry)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1, y1 = cp * dx + sp * dy, -sp * dx + cp * dy
    lam = x1 * x1 / (rx * rx) + y1 * y1 / (ry * ry)
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    den = rx * rx * y1 * y1 + ry * ry * x1 * x1
    co = math.sqrt(max(0.0, num / den)) if den else 0.0
    if large == sweep:
        co = -co
    cxp, cyp = co * rx * y1 / ry, -co * ry * x1 / rx
    cx = cp * cxp - sp * cyp + (p0[0] + p1[0]) / 2
    cy = sp * cxp + cp * cyp + (p0[1] + p1[1]) / 2

    def ang(ux, uy, vx, vy):
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a
    t1 = ang(1, 0, (x1 - cxp) / rx, (y1 - cyp) / ry)
    dt = ang((x1 - cxp) / rx, (y1 - cyp) / ry, (-x1 - cxp) / rx, (-y1 - cyp) / ry)
    if not sweep and dt > 0:
        dt -= math.tau
    elif sweep and dt < 0:
        dt += math.tau
    n = max(2, int(abs(dt) * n_per_rad * max(1.0, math.sqrt(max(rx, ry)) / 2)))
    out = []
    for i in range(1, n + 1):
        t = t1 + dt * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((cp * x - sp * y + cx, sp * x + cp * y + cy))
    return out


def parse_path(d: str, seg: int = 12) -> list[tuple[list, bool]]:
    subs, cur, closed = [], [], False
    pos = start = (0.0, 0.0)
    last_ctrl, last_cmd = None, ""

    def flush():
        nonlocal cur, closed
        if len(cur) >= 2:
            subs.append((cur, closed))
        cur, closed = [], False

    for cmd, args in _CMD.findall(d or ""):
        v = [float(x) for x in _NUM.findall(args)]
        rel = cmd.islower()
        C = cmd.upper()
        if C == "Z":
            if cur:
                closed = True
                flush()
            pos = start
            last_cmd = C
            continue
        step = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7}[C]
        groups = [v[i:i + step] for i in range(0, len(v) - step + 1, step)] or [[]]
        for gi, g in enumerate(groups):
            if not g and step:
                break
            ox, oy = pos if rel else (0.0, 0.0)
            if C == "M" and gi == 0:
                flush()
                pos = start = (g[0] + ox, g[1] + oy)
                cur = [pos]
                last_ctrl = None
                continue
            if C in ("M", "L"):
                pos = (g[0] + ox, g[1] + oy)
                cur.append(pos)
                last_ctrl = None
            elif C == "H":
                pos = (g[0] + (pos[0] if rel else 0), pos[1])
                cur.append(pos)
                last_ctrl = None
            elif C == "V":
                pos = (pos[0], g[0] + (pos[1] if rel else 0))
                cur.append(pos)
                last_ctrl = None
            elif C in ("C", "S"):
                if C == "C":
                    c1 = (g[0] + ox, g[1] + oy)
                    c2, p = (g[2] + ox, g[3] + oy), (g[4] + ox, g[5] + oy)
                else:
                    c1 = (2 * pos[0] - last_ctrl[0], 2 * pos[1] - last_ctrl[1]) \
                        if last_ctrl and last_cmd in ("C", "S") else pos
                    c2, p = (g[0] + ox, g[1] + oy), (g[2] + ox, g[3] + oy)
                cur.extend(_cubic(pos, c1, c2, p, seg))
                last_ctrl, pos = c2, p
            elif C in ("Q", "T"):
                if C == "Q":
                    c, p = (g[0] + ox, g[1] + oy), (g[2] + ox, g[3] + oy)
                else:
                    c = (2 * pos[0] - last_ctrl[0], 2 * pos[1] - last_ctrl[1]) \
                        if last_ctrl and last_cmd in ("Q", "T") else pos
                    p = (g[0] + ox, g[1] + oy)
                cur.extend(_quad(pos, c, p, seg))
                last_ctrl, pos = c, p
            elif C == "A":
                p = (g[5] + ox, g[6] + oy)
                cur.extend(_arc(pos, g[0], g[1], math.radians(g[2]), bool(g[3]), bool(g[4]), p))
                pos = p
                last_ctrl = None
            last_cmd = C
        last_cmd = C
    flush()
    return subs


# ------------------------------------------------------------------------ document
def _style(el, inherited: dict) -> dict:
    st = dict(inherited)
    for k in ("fill", "stroke", "stroke-width", "opacity", "fill-opacity", "stroke-opacity", "display"):
        if el.get(k) is not None:
            st[k] = el.get(k)
    for part in (el.get("style") or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            st[k.strip()] = v.strip()
    return st


def _paint(value, opacity) -> Color | None:
    if value is None or value in ("none", "transparent") or value.startswith("url("):
        return None
    v = value.strip()
    m = re.match(r"rgba?\(([^)]*)\)", v)
    try:
        if m:
            parts = [p.strip() for p in m.group(1).split(",")]
            nums = [float(p.rstrip("%")) * (2.55 if p.endswith("%") else 1) for p in parts[:3]]
            a = float(parts[3]) if len(parts) > 3 else 1.0
            c = Color(*nums, a)
        else:
            c = to_color((v,))
    except ValueError:
        c = Color(0, 0, 0)
    return c.alpha(c.a * opacity) if opacity < 1 else c


def _length(v, default=0.0):
    if v is None:
        return default
    m = _NUM.match(str(v).strip())
    return float(m.group()) if m else default


def _ellipse_pts(cx, cy, rx, ry, n=48):
    return [(cx + rx * math.cos(math.tau * i / n), cy + ry * math.sin(math.tau * i / n)) for i in range(n)]


def parse_svg(text: str) -> SvgDrawing:
    try:
        root = ET.fromstring(text.encode() if isinstance(text, str) else text)
    except ET.ParseError as exc:
        raise DataError(f"SVG konnte nicht gelesen werden: {exc}") from exc
    vb = [float(x) for x in _NUM.findall(root.get("viewBox") or "")]
    if len(vb) == 4:
        x0, y0, w, h = vb
    else:
        x0, y0, w, h = 0.0, 0.0, _length(root.get("width"), 100), _length(root.get("height"), 100)
    shapes: list[SvgShape] = []

    def walk(el, m, st):
        tag = el.tag.rsplit("}", 1)[-1]
        if tag in ("defs", "clipPath", "mask", "symbol", "metadata", "title", "desc", "style", "marker", "pattern"):
            return
        st = _style(el, st)
        if st.get("display") == "none":
            return
        m = _mul(m, _parse_transform(el.get("transform")))
        g = lambda k, d=0.0: _length(el.get(k), d)   # noqa: E731
        subs = None
        if tag == "path":
            subs = parse_path(el.get("d", ""))
        elif tag == "rect":
            x, y, rw, rh = g("x"), g("y"), g("width"), g("height")
            rx = g("rx", g("ry"))
            ry = g("ry", rx)
            if rx > 0:
                rx, ry = min(rx, rw / 2), min(ry, rh / 2)
                d = (f"M{x + rx},{y} H{x + rw - rx} A{rx},{ry} 0 0 1 {x + rw},{y + ry} V{y + rh - ry} "
                     f"A{rx},{ry} 0 0 1 {x + rw - rx},{y + rh} H{x + rx} A{rx},{ry} 0 0 1 {x},{y + rh - ry} "
                     f"V{y + ry} A{rx},{ry} 0 0 1 {x + rx},{y} Z")
                subs = parse_path(d)
            else:
                subs = [([(x, y), (x + rw, y), (x + rw, y + rh), (x, y + rh)], True)]
        elif tag == "circle":
            subs = [(_ellipse_pts(g("cx"), g("cy"), g("r"), g("r")), True)]
        elif tag == "ellipse":
            subs = [(_ellipse_pts(g("cx"), g("cy"), g("rx"), g("ry")), True)]
        elif tag == "line":
            subs = [([(g("x1"), g("y1")), (g("x2"), g("y2"))], False)]
        elif tag in ("polyline", "polygon"):
            v = [float(x) for x in _NUM.findall(el.get("points", ""))]
            subs = [(list(zip(v[::2], v[1::2])), tag == "polygon")]
        if subs:
            op = float(st.get("opacity", 1))
            fill = _paint(st.get("fill", "black"), op * float(st.get("fill-opacity", 1)))
            stroke = _paint(st.get("stroke"), op * float(st.get("stroke-opacity", 1)))
            scale = math.sqrt(abs(m[0] * m[3] - m[1] * m[2])) or 1
            shapes.append(SvgShape([(_apply(m, pts), cl) for pts, cl in subs if len(pts) >= 2],
                                   fill, stroke, _length(st.get("stroke-width"), 1.0) * scale))
        for child in el:
            walk(child, m, st)

    walk(root, (1, 0, 0, 1, -x0, -y0), {})
    return SvgDrawing(shapes, 0.0, 0.0, w, h)


def load_svg(path: str) -> SvgDrawing:
    """SVG-Datei laden → Formen (Punktlisten mit Füllung/Kontur)."""
    return parse_svg(read_text(path))
