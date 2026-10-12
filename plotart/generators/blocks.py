"""Pixel grid in the style of the reference print: squares, dashes and dots driven
by noise, with dense cells merging into vertical bars that are hatched solid."""
from __future__ import annotations

import math

from .. import geometry as geo
from ..params import Param
from . import register

PARAMS = [
    Param("cols", "Spalten", 48, 10, 140, 1, rand=(24, 80)),
    Param("gap", "Zwischenraum (Anteil)", 0.24, 0.05, 0.6, 0.01, rand=(0.12, 0.35)),
    Param("profile", "Verteilung", "bands", choices=[
        ("bands", "Bänder oben & unten"), ("top", "Verlauf von oben"),
        ("center", "Zentrum"), ("rings", "Ringe"), ("noise", "Nur Rauschen")]),
    Param("profile_mix", "Einfluss der Verteilung", 0.62, 0.0, 1.0, 0.02, rand=(0.35, 0.8)),
    Param("scale", "Rausch-Maßstab", 0.16, 0.02, 0.6, 0.01),
    Param("stretch", "Vertikale Streckung", 3.0, 1.0, 10.0, 0.5,
          help="größer = längere senkrechte Strukturen"),
    Param("jitter", "Zufall pro Zelle", 0.10, 0.0, 0.5, 0.01),
    Param("solid", "Schwelle für Balken", 0.74, 0.4, 1.0, 0.01),
    Param("max_run", "Max. Balkenlänge (Zellen)", 9, 1, 40, 1),
    Param("hmerge", "Waagrechte Verbindungen", 0.3, 0.0, 1.0, 0.05),
    Param("fill", "Füllung", "hatch", choices=[
        ("hatch", "Gefüllt (Schraffur)"), ("outline", "Nur Umriss"), ("mixed", "Gemischt")]),
    Param("hatch_density", "Schraffur-Dichte", 1.1, 0.3, 2.0, 0.05, randomize=False,
          help="1,0 = Linienabstand entspricht der Stiftbreite"),
    Param("accent", "Anteil Stift 2", 0.0, 0.0, 1.0, 0.05),
]


def _profile(kind: str, u: float, v: float) -> float:
    """u = vertical position 0..1, v = horizontal position 0..1."""
    if kind == "bands":
        return max(geo.smoothstep(0.48, 0.08, u), geo.smoothstep(0.78, 0.97, u))
    if kind == "top":
        return 1.0 - u
    if kind == "center":
        return 1.0 - geo.clamp(math.hypot(u - 0.5, (v - 0.5) * 0.8) * 2.2)
    if kind == "rings":
        return 0.5 + 0.5 * math.cos(math.hypot(u - 0.5, (v - 0.5) * 0.7) * 22)
    return 0.5


@register("blocks", "Pixel-Raster",
          "Quadrate, Striche und Punkte im Raster – dichte Zonen verschmelzen zu Balken.",
          PARAMS)
def generate(d, rng, noise, p):
    x0, y0, x1, y1 = d.box
    cols = p["cols"]
    cell = (x1 - x0) / cols
    rows = int((y1 - y0) // cell)
    oy = y0 + ((y1 - y0) - rows * cell) / 2
    gap = cell * p["gap"]
    size = cell - gap
    pen = d.pen_width
    spacing = pen / p["hatch_density"]
    sc, stretch, mix, jit = p["scale"], p["stretch"], p["profile_mix"], p["jitter"]

    col_shift = [noise.noise2(c * 0.21, 91.7) * 0.12 for c in range(cols)]
    col_bias = [rng.uniform(-1, 1) * jit * 0.6 for _ in range(cols)]

    dens = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            u = (r + 0.5) / rows + col_shift[c]
            prof = _profile(p["profile"], u, (c + 0.5) / cols)
            n = 0.5 + 0.9 * noise.fbm2(c * sc, r * sc / stretch, 3)
            v = mix * prof + (1 - mix) * n + col_bias[c] + rng.uniform(-jit, jit)
            dens[r][c] = geo.clamp(v)

    def draw_box(xa, ya, xb, yb, layer, mode):
        if mode == "mixed":
            mode = "hatch" if rng.random() < 0.6 else "outline"
        if mode == "hatch":
            d.add(geo.filled_rect(xa, ya, xb, yb, pen, spacing), layer)
        else:
            h = pen / 2
            d.add(geo.rect(xa + h, ya + h, xb - h, yb - h), layer)

    def cell_x(c):
        return x0 + c * cell + gap / 2

    def cell_y(r):
        return oy + r * cell + gap / 2

    solid = [[dens[r][c] >= p["solid"] for c in range(cols)] for r in range(rows)]
    fill = p["fill"]

    # --- individual cells ------------------------------------------------------------
    for r in range(rows):
        for c in range(cols):
            if solid[r][c]:
                continue
            v = dens[r][c]
            cx, cy = cell_x(c) + size / 2, cell_y(r) + size / 2
            if v < 0.10:
                if rng.random() < 0.5:
                    s = max(pen, size * 0.18)
                    draw_box(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2, 1, "hatch")
            elif v < 0.24:
                d.line(cell_x(c), cy, cell_x(c) + size, cy)
            else:
                t = geo.clamp((v - 0.24) / 0.22)
                s = size * geo.lerp(0.32, 1.0, t)
                if t >= 1.0 or rng.random() < 0.15:
                    s = size
                draw_box(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2, 1, fill)

    # --- merged vertical bars -----------------------------------------------------------
    max_run = p["max_run"]
    for c in range(cols):
        r = 0
        while r < rows:
            if not solid[r][c]:
                r += 1
                continue
            end = r
            while end + 1 < rows and solid[end + 1][c]:
                end += 1
            # split long runs into random chunks
            start = r
            while start <= end:
                length = min(end - start + 1, rng.randint(max(1, max_run // 2), max_run))
                stop = start + length - 1
                layer = 2 if rng.random() < p["accent"] else 1
                draw_box(cell_x(c), cell_y(start), cell_x(c) + size,
                         cell_y(stop) + size, layer, fill)
                # horizontal bridges to a solid neighbour on the right
                for rr in range(start, stop + 1):
                    if (fill != "outline" and c + 1 < cols and solid[rr][c + 1]
                            and rng.random() < p["hmerge"]):
                        draw_box(cell_x(c) + size - pen, cell_y(rr),
                                 cell_x(c + 1) + pen, cell_y(rr) + size, layer, "hatch")
                start = stop + 1
            r = end + 1
