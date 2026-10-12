"""Circle packing; each circle filled with rings, a spiral or hatching."""
from __future__ import annotations

import math
from collections import defaultdict

from .. import geometry as geo
from ..params import Param
from . import register

PARAMS = [
    Param("min_r", "Min. Radius (mm)", 1.5, 0.5, 20.0, 0.5, rand=(0.5, 4)),
    Param("max_r", "Max. Radius (mm)", 32.0, 3.0, 120.0, 1.0, rand=(10, 60)),
    Param("gap", "Abstand (mm)", 1.2, 0.0, 10.0, 0.1, rand=(0.4, 3)),
    Param("attempts", "Versuche", 5000, 200, 30000, 100, rand=(2000, 10000)),
    Param("fill", "Füllung", "mixed", choices=[
        ("mixed", "Gemischt"), ("rings", "Ringe"), ("spiral", "Spirale"),
        ("hatch", "Schraffur"), ("outline", "Nur Umriss")]),
    Param("spacing", "Linienabstand Füllung (mm)", 1.2, 0.3, 6.0, 0.1, rand=(0.6, 2.5)),
    Param("angle_mode", "Schraffur-Winkel", "noise", choices=[
        ("noise", "Rauschfeld"), ("random", "Zufällig"), ("fixed", "Einheitlich")]),
    Param("accent", "Anteil Stift 2", 0.15, 0.0, 1.0, 0.05),
]


@register("circles", "Kreis-Packung",
          "Dicht gepackte Kreise, gefüllt mit Ringen, Spiralen oder Schraffuren.", PARAMS)
def generate(d, rng, noise, p):
    x0, y0, x1, y1 = d.box
    rmin, rmax, gap = p["min_r"], max(p["max_r"], p["min_r"]), p["gap"]
    cell = 2 * rmax + gap
    grid = defaultdict(list)
    circles = []

    for _ in range(p["attempts"]):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        r = min(rmax, x - x0, x1 - x, y - y0, y1 - y)
        kx, ky = int(x // cell), int(y // cell)
        for ix in (kx - 1, kx, kx + 1):
            for iy in (ky - 1, ky, ky + 1):
                for cx, cy, cr in grid.get((ix, iy), ()):
                    r = min(r, math.hypot(cx - x, cy - y) - cr - gap)
        if r < rmin:
            continue
        circles.append((x, y, r))
        grid[(kx, ky)].append((x, y, r))

    spacing = max(p["spacing"], d.pen_width * 0.8)
    for x, y, r in circles:
        layer = 2 if rng.random() < p["accent"] else 1
        mode = p["fill"]
        if mode == "mixed":
            mode = rng.choices(["rings", "spiral", "hatch", "outline"], [3, 2, 3, 1])[0]
        if p["angle_mode"] == "noise":
            ang = noise.noise2(x * 0.01, y * 0.01) * math.pi * 2
        elif p["angle_mode"] == "random":
            ang = rng.uniform(0, math.pi)
        else:
            ang = math.pi / 4
        if mode == "rings":
            rr = r
            while rr > spacing * 0.5:
                d.circle(x, y, rr, layer)
                rr -= spacing
        elif mode == "spiral":
            d.add(geo.spiral(x, y, r, spacing, ang), layer)
        elif mode == "hatch":
            d.circle(x, y, r, layer)
            d.add(geo.hatch_circle(x, y, r, spacing, ang), layer)
        else:
            d.circle(x, y, r, layer)
