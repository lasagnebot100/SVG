"""Topographic contour lines of a fractal noise landscape (marching squares)."""
from __future__ import annotations

import math
from collections import defaultdict

from ..params import Param
from . import register

PARAMS = [
    Param("levels", "Anzahl Höhenlinien", 32, 4, 120, 1, rand=(14, 60)),
    Param("scale", "Rausch-Maßstab", 0.008, 0.001, 0.05, 0.0005, rand=(0.003, 0.015)),
    Param("octaves", "Detailstufen", 4, 1, 7, 1),
    Param("warp", "Verzerrung", 0.6, 0.0, 3.0, 0.05, help="Domain-Warping für organischere Formen"),
    Param("island", "Insel-Form", 0.3, 0.0, 1.0, 0.05, help="Abfall zum Rand hin"),
    Param("resolution", "Auflösung (mm)", 1.0, 0.4, 4.0, 0.1, randomize=False),
    Param("index_every", "Jede n-te Linie Stift 2", 5, 0, 20, 1, help="0 = aus"),
]

# marching-squares edge pairs per case (edges: 0 top, 1 right, 2 bottom, 3 left)
_CASES = {
    1: [(3, 2)], 2: [(2, 1)], 3: [(3, 1)], 4: [(0, 1)], 6: [(0, 2)], 7: [(3, 0)],
    8: [(3, 0)], 9: [(0, 2)], 11: [(0, 1)], 12: [(3, 1)], 13: [(2, 1)], 14: [(3, 2)],
}


@register("topo", "Höhenlinien",
          "Konturlinien einer zufälligen Landschaft – wie eine topografische Karte.", PARAMS)
def generate(d, rng, noise, p):
    x0, y0, x1, y1 = d.box
    res = p["resolution"]
    nx = int((x1 - x0) / res) + 1
    ny = int((y1 - y0) / res) + 1
    sc, warp, isl, octv = p["scale"], p["warp"], p["island"], p["octaves"]
    cx, cy = d.center
    rmax = math.hypot(d.inner_width, d.inner_height) / 2

    grid = []
    for j in range(ny):
        y = y0 + j * res
        row = []
        for i in range(nx):
            x = x0 + i * res
            wx = wy = 0.0
            if warp:
                wx = noise.noise2(x * sc * 0.7 + 5.2, y * sc * 0.7 + 1.3) * warp
                wy = noise.noise2(x * sc * 0.7 + 9.7, y * sc * 0.7 + 4.1) * warp
            v = noise.fbm2(x * sc + wx, y * sc + wy, octv)
            if isl:
                v -= isl * (math.hypot(x - cx, y - cy) / rmax) ** 2 * 1.2
            row.append(v)
        grid.append(row)

    flat = [v for row in grid for v in row]
    lo, hi = min(flat), max(flat)
    n_lv = p["levels"]
    step = (hi - lo) / (n_lv + 1)
    levels = [lo + step * (k + 1) for k in range(n_lv)]

    segs = defaultdict(list)   # level index -> list of (edge_id_a, edge_id_b)
    pts = {}                   # (level, edge_id) -> point

    def edge(i, j, e):
        # unique ids for shared cell edges
        return {0: ("h", i, j), 2: ("h", i, j + 1), 3: ("v", i, j), 1: ("v", i + 1, j)}[e]

    for j in range(ny - 1):
        r0, r1 = grid[j], grid[j + 1]
        for i in range(nx - 1):
            a, b, c, dd = r0[i], r0[i + 1], r1[i + 1], r1[i]   # tl, tr, br, bl
            vmin, vmax = min(a, b, c, dd), max(a, b, c, dd)
            k0 = max(0, math.ceil((vmin - lo) / step - 1))
            k1 = min(n_lv - 1, math.floor((vmax - lo) / step - 1))
            for k in range(k0, k1 + 1):
                lv = levels[k]
                case = (8 if a > lv else 0) | (4 if b > lv else 0) | (2 if c > lv else 0) | (1 if dd > lv else 0)
                if case in (0, 15):
                    continue
                if case in (5, 10):
                    center = (a + b + c + dd) / 4 > lv
                    if case == 5:
                        pairs = [(3, 0), (2, 1)] if center else [(0, 1), (3, 2)]
                    else:
                        pairs = [(0, 1), (3, 2)] if center else [(3, 0), (2, 1)]
                else:
                    pairs = _CASES[case]
                for ea, eb in pairs:
                    ids = []
                    for e in (ea, eb):
                        eid = edge(i, j, e)
                        if (k, eid) not in pts:
                            if e == 0:
                                t = (lv - a) / (b - a); pt = (i + t, j)
                            elif e == 1:
                                t = (lv - b) / (c - b); pt = (i + 1, j + t)
                            elif e == 2:
                                t = (lv - dd) / (c - dd); pt = (i + t, j + 1)
                            else:
                                t = (lv - a) / (dd - a); pt = (i, j + t)
                            pts[(k, eid)] = (x0 + pt[0] * res, y0 + pt[1] * res)
                        ids.append(eid)
                    segs[k].append((ids[0], ids[1]))

    every = p["index_every"]
    for k, seglist in segs.items():
        adj = defaultdict(list)
        for si, (ea, eb) in enumerate(seglist):
            adj[ea].append(si)
            adj[eb].append(si)
        used = [False] * len(seglist)
        layer = 2 if every and (k + 1) % every == 0 else 1
        for si in range(len(seglist)):
            if used[si]:
                continue
            used[si] = True
            chain = list(seglist[si])
            for direction in (0, 1):
                while True:
                    tip = chain[-1]
                    nxt = next((s for s in adj[tip] if not used[s]), None)
                    if nxt is None:
                        break
                    used[nxt] = True
                    ea, eb = seglist[nxt]
                    chain.append(eb if ea == tip else ea)
                if direction == 0:
                    chain.reverse()
            d.add([pts[(k, e)] for e in chain], layer)
