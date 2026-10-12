"""Turn recorded items into polylines in device coordinates (for raster and plotter output)."""
from __future__ import annotations

import math

from ..geometry import segments_for_radius
from .core import IDENTITY, Item, mat_apply


def _scale_of(m) -> float:
    return math.sqrt(abs(m[0] * m[3] - m[1] * m[2])) or 1.0


def _ellipse(cx, cy, rx, ry, n):
    return [(cx + rx * math.cos(math.tau * i / n), cy + ry * math.sin(math.tau * i / n)) for i in range(n)]


def _rounded_rect(x, y, w, h, r, k):
    if r <= 0:
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    pts = []
    for cx, cy, a0 in ((x + w - r, y + r, -math.pi / 2), (x + w - r, y + h - r, 0),
                       (x + r, y + h - r, math.pi / 2), (x + r, y + r, math.pi)):
        for i in range(k + 1):
            a = a0 + math.pi / 2 * i / k
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _cubic(p0, c1, c2, p3, n):
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        out.append((u * u * u * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t * t * t * p3[0],
                    u * u * u * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t * t * t * p3[1]))
    return out


def flatten(item: Item, width: float, height: float, tol: float = 0.25, scale: float = 1.0):
    """Returns a list of (points, closed) in device units (user units × scale).

    `tol` is the maximum chord error in device units.
    """
    m = item.matrix or IDENTITY
    s = _scale_of(m) * scale
    k, d = item.kind, item.data
    subs: list[tuple[list, bool]] = []
    if k == "background":
        subs = [([(0, 0), (width, 0), (width, height), (0, height)], True)]
        m = IDENTITY
    elif k == "ellipse":
        n = segments_for_radius(max(d["rx"], d["ry"]) * s, tol)
        subs = [(_ellipse(d["cx"], d["cy"], d["rx"], d["ry"], n), True)]
    elif k == "rect":
        kk = max(2, segments_for_radius(d["r"] * s, tol) // 4) if d["r"] > 0 else 0
        subs = [(_rounded_rect(d["x"], d["y"], d["w"], d["h"], d["r"], kk), True)]
    elif k == "path":
        for segs, closed in zip(d["subpaths"], d["closed"]):
            pts = []
            for seg in segs:
                if seg[0] in ("M", "L"):
                    pts.append((seg[1], seg[2]))
                elif seg[0] == "C" and pts:
                    p0 = pts[-1]
                    c1, c2, p3 = (seg[1], seg[2]), (seg[3], seg[4]), (seg[5], seg[6])
                    length = (math.dist(p0, c1) + math.dist(c1, c2) + math.dist(c2, p3)) * s
                    n = max(2, min(400, int(math.sqrt(length / max(tol, 1e-3)) * 1.5) + 2))
                    pts.extend(_cubic(p0, c1, c2, p3, n))
            if len(pts) >= 2 or (len(pts) == 1 and not closed):
                subs.append((pts, closed))
    else:
        return []
    out = []
    for pts, closed in subs:
        if m is not IDENTITY and m != IDENTITY:
            pts = [mat_apply(m, x, y) for x, y in pts]
        if scale != 1.0:
            pts = [(x * scale, y * scale) for x, y in pts]
        out.append((pts, closed))
    return out
