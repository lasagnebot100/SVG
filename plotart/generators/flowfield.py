"""Evenly spaced streamlines through a noise-based vector field."""
from __future__ import annotations

import math
from collections import defaultdict

from ..params import Param
from . import register

PARAMS = [
    Param("field", "Feld", "noise", choices=[
        ("noise", "Rauschen"), ("vortex", "Wirbel"), ("waves", "Wellen"), ("radial", "Explosion")]),
    Param("separation", "Linienabstand (mm)", 2.2, 0.6, 10.0, 0.1, rand=(1.2, 4.0)),
    Param("scale", "Rausch-Maßstab", 0.006, 0.001, 0.03, 0.0005, rand=(0.002, 0.012)),
    Param("turbulence", "Turbulenz", 1.2, 0.0, 4.0, 0.05),
    Param("max_len", "Max. Linienlänge (mm)", 260.0, 10.0, 1000.0, 5.0),
    Param("min_len", "Min. Linienlänge (mm)", 8.0, 0.0, 100.0, 1.0),
    Param("density", "Füllgrad", 1.0, 0.1, 1.0, 0.05, rand=(0.4, 1.0),
          help="Anteil der Startpunkte, die genutzt werden"),
    Param("accent", "Anteil Stift 2", 0.0, 0.0, 1.0, 0.05),
]


@register("flowfield", "Strömungsfeld",
          "Gleichmäßig verteilte Stromlinien, die einem Rauschfeld folgen.", PARAMS)
def generate(d, rng, noise, p):
    x0, y0, x1, y1 = d.box
    cx, cy = d.center
    sep = p["separation"]
    dtest = sep * 0.55
    step = min(0.5, sep / 3)
    sc, turb = p["scale"], p["turbulence"]
    field = p["field"]
    max_steps = int(p["max_len"] / step)

    def angle(x, y):
        n = noise.fbm2(x * sc, y * sc, 2)
        if field == "noise":
            return n * math.pi * 2 * turb
        if field == "vortex":
            return math.atan2(y - cy, x - cx) + math.pi / 2 + 0.35 + n * turb * 2
        if field == "waves":
            return math.sin(y * sc * 6 + n * 3) * (0.6 + turb * 0.5)
        return math.atan2(y - cy, x - cx) + n * turb * 2  # radial

    grid: dict[tuple[int, int], list[tuple[float, float]]] = defaultdict(list)

    def key(x, y):
        return (int(x // dtest), int(y // dtest))

    def free(x, y, own=None, s=0.0):
        kx, ky = key(x, y)
        lim = dtest * dtest
        for ix in (kx - 1, kx, kx + 1):
            for iy in (ky - 1, ky, ky + 1):
                for qx, qy in grid.get((ix, iy), ()):
                    if (qx - x) ** 2 + (qy - y) ** 2 < lim:
                        return False
                if own is not None:
                    for qx, qy, qs in own.get((ix, iy), ()):
                        if abs(qs - s) > 3 * dtest and (qx - x) ** 2 + (qy - y) ** 2 < lim:
                            return False
        return True

    def trace(x, y, sign, own, s_sign):
        pts = []
        s = 0.0
        for _ in range(max_steps):
            a = angle(x, y)
            # midpoint (RK2) integration for smoother curves
            mx, my = x + math.cos(a) * step * 0.5 * sign, y + math.sin(a) * step * 0.5 * sign
            a = angle(mx, my)
            nx, ny = x + math.cos(a) * step * sign, y + math.sin(a) * step * sign
            s += step
            if not (x0 <= nx <= x1 and y0 <= ny <= y1):
                break
            if not free(nx, ny, own, s * s_sign):
                break
            own[key(nx, ny)].append((nx, ny, s * s_sign))
            pts.append((nx, ny))
            x, y = nx, ny
        return pts

    # candidate seeds on a shuffled jittered grid
    seeds = []
    gx = int((x1 - x0) / sep)
    gy = int((y1 - y0) / sep)
    for i in range(gx):
        for j in range(gy):
            seeds.append((x0 + (i + rng.random()) * sep, y0 + (j + rng.random()) * sep))
    rng.shuffle(seeds)
    seeds = seeds[: int(len(seeds) * p["density"])]

    for sx, sy in seeds:
        if not free(sx, sy):
            continue
        own = defaultdict(list)
        own[key(sx, sy)].append((sx, sy, 0.0))
        fwd = trace(sx, sy, 1, own, 1)
        bwd = trace(sx, sy, -1, own, -1)
        line = bwd[::-1] + [(sx, sy)] + fwd
        if len(line) * step < p["min_len"] or len(line) < 2:
            continue
        for x, y in line:
            grid[key(x, y)].append((x, y))
        layer = 2 if (p["accent"] > 0 and
                      noise.noise2(sx * 0.01 + 50, sy * 0.01) * 0.5 + 0.5 < p["accent"]) else 1
        d.add(line, layer)
