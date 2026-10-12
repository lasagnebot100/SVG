"""Stacked ridge lines with hidden-line removal (à la „Unknown Pleasures“)."""
from __future__ import annotations

import math

from ..params import Param
from . import register

PARAMS = [
    Param("lines", "Anzahl Linien", 70, 10, 250, 1, rand=(40, 130)),
    Param("amplitude", "Höhe der Spitzen (mm)", 35.0, 2.0, 150.0, 1.0, rand=(15, 70)),
    Param("scale", "Rausch-Maßstab", 0.035, 0.005, 0.2, 0.001),
    Param("focus", "Breite der Zone", 0.28, 0.05, 1.0, 0.01,
          help="Breite des Bereichs mit hohen Spitzen (Anteil der Breite)"),
    Param("sharpness", "Schärfe", 2.0, 0.5, 5.0, 0.1),
    Param("baseline", "Grundrauschen", 0.04, 0.0, 0.5, 0.01),
    Param("drift", "Versatz pro Linie", 0.08, 0.0, 0.5, 0.01),
    Param("accent_every", "Jede n-te Linie Stift 2", 0, 0, 20, 1, help="0 = aus"),
]


@register("waves", "Wellenlinien",
          "Gestapelte Bergrücken mit verdeckten Linien – Plattencover-Ästhetik.", PARAMS)
def generate(d, rng, noise, p):
    x0, y0, x1, y1 = d.box
    amp = p["amplitude"]
    n_lines = p["lines"]
    res = 0.5
    nx = int((x1 - x0) / res) + 1
    xs = [x0 + (x1 - x0) * i / (nx - 1) for i in range(nx)]
    top = y0 + amp
    dy = (y1 - top) / max(1, n_lines - 1)
    focus = p["focus"]
    center_shift = [rng.uniform(-0.08, 0.08) for _ in range(n_lines)]
    horizon = [math.inf] * nx
    every = p["accent_every"]

    for i in reversed(range(n_lines)):            # front (bottom) to back (top)
        base = top + i * dy
        ys = []
        for k, x in enumerate(xs):
            u = (x - x0) / (x1 - x0) - 0.5 - center_shift[i]
            env = math.exp(-(u / focus) ** 2 * 2.5)
            n = 0.5 + 0.5 * noise.fbm2(x * p["scale"], i * p["drift"] + 13.7, 4)
            h = (n ** p["sharpness"]) * env + p["baseline"] * (0.5 + 0.5 * noise.noise2(x * 0.3, i * 0.7))
            ys.append(base - amp * h)
        layer = 2 if every and i % every == 0 else 1
        piece = []
        prev_vis = None
        for k in range(nx):
            vis = ys[k] < horizon[k] - 0.05
            if prev_vis is not None and vis != prev_vis:
                # interpolate crossing between k-1 and k
                a0 = ys[k - 1] - horizon[k - 1] if horizon[k - 1] != math.inf else -1e9
                a1 = ys[k] - horizon[k] if horizon[k] != math.inf else -1e9
                t = a0 / (a0 - a1) if a0 != a1 and abs(a0) < 1e8 and abs(a1) < 1e8 else 0.5
                cx = xs[k - 1] + (xs[k] - xs[k - 1]) * t
                cy = ys[k - 1] + (ys[k] - ys[k - 1]) * t
                if vis:
                    piece = [(cx, cy)]
                else:
                    piece.append((cx, cy))
                    d.add(piece, layer)
                    piece = []
            if vis:
                piece.append((xs[k], ys[k]))
            prev_vis = vis
        if len(piece) >= 2:
            d.add(piece, layer)
        for k in range(nx):
            if ys[k] < horizon[k]:
                horizon[k] = ys[k]
