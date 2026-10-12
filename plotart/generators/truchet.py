"""Truchet tiles with multiple bands – the pieces join into long continuous curves."""
from __future__ import annotations

import math

from .. import geometry as geo
from ..params import Param
from . import register

PARAMS = [
    Param("tiles", "Kacheln pro Zeile", 12, 2, 60, 1, rand=(5, 24)),
    Param("bands", "Linien pro Band", 5, 1, 20, 1, rand=(2, 10)),
    Param("style", "Stil", "arcs", choices=[
        ("arcs", "Bögen (Smith)"), ("diagonal", "Diagonalen (10 PRINT)"), ("mixed", "Bögen + Kreuze")]),
    Param("bias", "Ordnung ↔ Zufall", 0.5, 0.0, 1.0, 0.05,
          help="0/1 = gleichmäßig ausgerichtet, 0,5 = völlig zufällig"),
    Param("frame", "Rahmen zeichnen", False),
]


@register("truchet", "Truchet-Muster",
          "Kacheln mit Viertelkreisen – fügen sich zu endlosen Schlangenlinien.", PARAMS)
def generate(d, rng, noise, p):
    x0, y0, x1, y1 = d.box
    cols = p["tiles"]
    t = (x1 - x0) / cols
    rows = int((y1 - y0) // t)
    oy = y0 + ((y1 - y0) - rows * t) / 2
    bands = p["bands"]
    w = 0.41 * t / bands
    radii = [t / 2 + (k - (bands - 1) / 2) * w for k in range(bands)]
    offsets = [(k - (bands - 1) / 2) * w * math.sqrt(2) for k in range(bands)]

    for r in range(rows):
        for c in range(cols):
            tx, ty = x0 + c * t, oy + r * t
            flip = rng.random() < p["bias"]
            style = p["style"]
            if style == "mixed":
                style = "cross" if rng.random() < 0.15 else "arcs"
            if style == "arcs":
                corners = [(tx, ty, 0), (tx + t, ty + t, math.pi)] if flip else \
                          [(tx + t, ty, math.pi / 2), (tx, ty + t, -math.pi / 2)]
                for cx, cy, a0 in corners:
                    for rad in radii:
                        d.add(geo.arc(cx, cy, rad, a0, a0 + math.pi / 2))
            elif style == "cross":
                # straight bands through the tile, horizontal and vertical (over/under look)
                for rad in radii:
                    d.line(tx + rad, ty, tx + rad, ty + t)
                for rad in radii:
                    if abs(rad - t / 2) > w * (bands / 2):
                        d.line(tx, ty + rad, tx + t, ty + rad)
                    else:
                        lo = t / 2 - (bands / 2) * w
                        hi = t / 2 + (bands / 2) * w
                        d.line(tx, ty + rad, tx + lo, ty + rad)
                        d.line(tx + hi, ty + rad, tx + t, ty + rad)
            else:
                for off in offsets:
                    pts = _diag(tx, ty, t, off, flip)
                    if pts:
                        d.add(pts)
    if p["frame"]:
        d.rect(x0, oy, x0 + cols * t, oy + rows * t)


def _diag(tx, ty, t, c, flip):
    """Line x - y = c (or mirrored) clipped to the tile."""
    if abs(c) >= t:
        return None
    if c >= 0:
        a, b = (c, 0), (t, t - c)
    else:
        a, b = (0, -c), (t + c, t)
    if flip:
        a, b = (t - a[0], a[1]), (t - b[0], b[1])
    return [(tx + a[0], ty + a[1]), (tx + b[0], ty + b[1])]
