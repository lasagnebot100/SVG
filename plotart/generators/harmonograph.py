"""Damped harmonograph – one long, continuous pendulum curve (or several, for moiré)."""
from __future__ import annotations

import math

from ..params import Param
from . import register

PARAMS = [
    Param("ratio", "Frequenzverhältnis", "3:2", choices=[
        ("1:1", "1 : 1"), ("2:1", "2 : 1"), ("3:2", "3 : 2"), ("4:3", "4 : 3"),
        ("3:1", "3 : 1"), ("5:4", "5 : 4"), ("random", "Zufällig")]),
    Param("detune", "Verstimmung", 0.006, 0.0, 0.05, 0.001),
    Param("damping", "Dämpfung", 0.004, 0.0005, 0.02, 0.0001),
    Param("duration", "Dauer", 400.0, 20.0, 1500.0, 10.0, rand=(150, 800)),
    Param("rotary", "Drehpendel", False, help="dritte, kreisende Komponente"),
    Param("copies", "Anzahl Kurven", 1, 1, 12, 1, rand=(1, 5), help="mehrere leicht versetzte Kurven = Moiré"),
    Param("offset", "Versatz zwischen Kurven", 0.04, 0.0, 0.5, 0.005),
    Param("alternate", "Kurven abwechselnd Stift 2", False),
]


@register("harmonograph", "Harmonograph",
          "Gedämpfte Pendelschwingungen – eine einzige, endlose Linie.", PARAMS)
def generate(d, rng, noise, p):
    if p["ratio"] == "random":
        f1, f2 = rng.randint(1, 5), rng.randint(1, 5)
    else:
        f1, f2 = (int(v) for v in p["ratio"].split(":"))
    det = p["detune"]
    pend = [
        (f1 + rng.uniform(-det, det), rng.uniform(0, math.tau), 1.0),
        (f2 + rng.uniform(-det, det), rng.uniform(0, math.tau), rng.uniform(0.3, 1.0)),
        (f2 + rng.uniform(-det, det), rng.uniform(0, math.tau), 1.0),
        (f1 + rng.uniform(-det, det), rng.uniform(0, math.tau), rng.uniform(0.3, 1.0)),
    ]
    rot_f = f1 + rng.uniform(-det, det)
    damp = p["damping"]
    steps_per_unit = 40
    curves = []
    for cpy in range(p["copies"]):
        ph = cpy * p["offset"]
        pts = []
        n = int(p["duration"] * steps_per_unit)
        for i in range(n):
            t = i / steps_per_unit
            e = math.exp(-damp * t)
            x = (pend[0][2] * math.sin(pend[0][0] * t + pend[0][1] + ph)
                 + pend[1][2] * math.sin(pend[1][0] * t + pend[1][1])) * e
            y = (pend[2][2] * math.sin(pend[2][0] * t + pend[2][1])
                 + pend[3][2] * math.sin(pend[3][0] * t + pend[3][1] + ph)) * e
            if p["rotary"]:
                x += 0.5 * math.cos(rot_f * t) * e
                y += 0.5 * math.sin(rot_f * t) * e
            pts.append((x, y))
        curves.append(pts)

    # fit all curves into the drawing box, keeping the aspect ratio
    xs = [x for c in curves for x, _ in c]
    ys = [y for c in curves for _, y in c]
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    s = min(d.inner_width / bw, d.inner_height / bh)
    mx, my = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    cx, cy = d.center
    for k, c in enumerate(curves):
        layer = 2 if p["alternate"] and k % 2 else 1
        d.add([(cx + (x - mx) * s, cy + (y - my) * s) for x, y in c], layer)
