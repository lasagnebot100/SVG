"""Patterns & geometry: WFC, Truchet, Delaunay, TSP art, contours, streamlines, L-systems, circle packing."""
from __future__ import annotations

import math
import time

from ..tools import tool
from ._grid import SpatialGrid


def _arc(cx, cy, r, a0, a1, n=12):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n))
            for i in range(n + 1)]


# ---------------------------------------------------------------------------- tile sets (unit cell 0–1)
# sockets: (oben, rechts, unten, links); paths: Linien im Einheitsquadrat (x nach rechts, y nach unten)
def _pipe_tiles():
    h = 0.5
    straight = [[(h, 0), (h, 1)]]
    corner = [_arc(1, 0, h, math.pi / 2, math.pi)]                 # oben → rechts
    tee = [[(0, h), (1, h)], [(h, h), (h, 1)]]
    cross = [[(h, 0), (h, 1)], [(0, h), (1, h)]]
    end = [[(h, 0), (h, h)], _arc(h, h, 0.12, 0, math.tau, 16)]
    return {
        "leer": ((0, 0, 0, 0), [], 2.0, False),
        "gerade": ((1, 0, 1, 0), straight, 3.0, True),
        "kurve": ((1, 1, 0, 0), corner, 4.0, True),
        "t": ((0, 1, 1, 1), tee, 1.0, True),
        "kreuz": ((1, 1, 1, 1), cross, 0.6, False),
        "ende": ((1, 0, 0, 0), end, 0.4, True),
    }


def _circuit_tiles():
    def chip():
        return [[(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8), (0.2, 0.2)], [(0.5, 0), (0.5, 0.2)],
                [(0.5, 0.8), (0.5, 1)]]
    diag = [[(0.5, 0), (0.5, 0.25), (0.75, 0.5), (1, 0.5)]]
    return {
        "leer": ((0, 0, 0, 0), [], 3.0, False),
        "bahn": ((1, 0, 1, 0), [[(0.5, 0), (0.5, 1)]], 3.0, True),
        "knick": ((1, 1, 0, 0), diag, 3.0, True),
        "via": ((1, 0, 0, 0), [[(0.5, 0), (0.5, 0.42)], _arc(0.5, 0.5, 0.08, 0, math.tau, 12)], 0.8, True),
        "chip": ((1, 0, 1, 0), chip(), 0.5, True),
        "abzweig": ((1, 1, 1, 0), [[(0.5, 0), (0.5, 1)], [(0.5, 0.5), (1, 0.5)]], 0.8, True),
    }


TILESETS = {"rohre": _pipe_tiles, "platine": _circuit_tiles}


def _rotate_tile(sockets, paths, k):
    s = tuple(sockets[(i - k) % 4] for i in range(4))
    rp = []
    for path in paths:
        q = []
        for x, y in path:
            for _ in range(k):
                x, y = 1 - y, x                                    # 90° clockwise in a y-down cell
            q.append((x, y))
        rp.append(q)
    return s, rp


def _expand_tiles(tileset):
    defs = TILESETS[tileset]() if isinstance(tileset, str) else tileset
    tiles = {}
    for name, (sockets, paths, weight, rotate) in defs.items():
        seen = set()
        for k in range(4 if rotate else 1):
            s, p = _rotate_tile(sockets, paths, k)
            if s in seen:
                continue
            seen.add(s)
            tiles[f"{name}{k * 90 if rotate else ''}"] = (s, p, float(weight))
    return tiles


@tool("Muster", needs_rng=True)
def wave_function_collapse(cols, rows, tileset="rohre", wrap=False, max_tries=20, rng=None):
    """Wave Function Collapse: füllt ein Raster mit Kacheln, deren Kanten zusammenpassen → Raster mit Kachelnamen.

    Eingebaute Sätze: "rohre", "platine" – oder ein eigenes Dict
    {name: ((oben, rechts, unten, links), pfade, gewicht, drehbar)}. Zeichnen mit tile_paths().
    """
    tiles = _expand_tiles(tileset)
    names = list(tiles)
    sock = [tiles[n][0] for n in names]
    weight = [tiles[n][2] for n in names]
    T = len(names)
    # compat[d][a] = set of tiles b that may sit in direction d of a (0 up, 1 right, 2 down, 3 left)
    compat = [[{b for b in range(T) if sock[a][d] == sock[b][(d + 2) % 4]} for a in range(T)] for d in range(4)]
    dirs = ((0, -1), (1, 0), (0, 1), (-1, 0))
    for _try in range(int(max_tries)):
        wave = [set(range(T)) for _ in range(cols * rows)]
        if not wrap:                                               # no open ends at the border
            for y in range(rows):
                for x in range(cols):
                    for d, (dx, dy) in enumerate(dirs):
                        if not (0 <= x + dx < cols and 0 <= y + dy < rows):
                            wave[y * cols + x] = {t for t in wave[y * cols + x] if sock[t][d] == 0} or \
                                wave[y * cols + x]
        ok = True
        while True:
            best, best_e = -1, None
            for i, opts in enumerate(wave):
                if len(opts) > 1:
                    w = sum(weight[t] for t in opts)
                    e = math.log(w) - sum(weight[t] * math.log(weight[t]) for t in opts) / w + rng.random() * 1e-6
                    if best_e is None or e < best_e:
                        best, best_e = i, e
                elif not opts:
                    ok = False
                    break
            if not ok or best < 0:
                break
            opts = list(wave[best])
            r = rng.random() * sum(weight[t] for t in opts)
            for t in opts:
                r -= weight[t]
                if r <= 0:
                    break
            wave[best] = {t}
            stack = [best]
            while stack and ok:                                   # propagate constraints
                i = stack.pop()
                x, y = i % cols, i // cols
                for d, (dx, dy) in enumerate(dirs):
                    nx, ny = x + dx, y + dy
                    if wrap:
                        nx, ny = nx % cols, ny % rows
                    elif not (0 <= nx < cols and 0 <= ny < rows):
                        continue
                    j = ny * cols + nx
                    allowed = set()
                    for a in wave[i]:
                        allowed |= compat[d][a]
                    new = wave[j] & allowed
                    if new != wave[j]:
                        if not new:
                            ok = False
                            break
                        wave[j] = new
                        stack.append(j)
            if not ok:
                break
        if ok:
            return [[names[next(iter(wave[y * cols + x]))] for x in range(cols)] for y in range(rows)]
    raise ValueError("Wave Function Collapse fand keine Lösung – Raster verkleinern oder anderen Seed wählen")


@tool("Muster")
def tile_paths(grid, tileset="rohre", cell=40.0, x0=0.0, y0=0.0):
    """Linien eines Kachel-Rasters (aus wave_function_collapse) → [[(x, y), …], …] zum Zeichnen mit polyline()."""
    tiles = _expand_tiles(tileset)
    out = []
    for r, row in enumerate(grid):
        for c, name in enumerate(row):
            for path in tiles[name][1]:
                out.append([(x0 + (c + x) * cell, y0 + (r + y) * cell) for x, y in path])
    return out


# ---------------------------------------------------------------------------- Truchet
@tool("Muster", needs_rng=True)
def truchet(cols, rows, cell=40.0, style="boegen", x0=0.0, y0=0.0, bias=0.5, rng=None):
    """Truchet-Kacheln → Linien [[(x, y), …]]. style: "boegen" (Viertelkreise), "diagonal", "dreiecke" (Flächen).

    bias = Wahrscheinlichkeit der ersten Ausrichtung; eine Zahl oder eine Funktion f(spalte, zeile) → 0…1.
    Bei "dreiecke" sind es geschlossene Flächen für polygon().
    """
    out = []
    for r in range(rows):
        for c in range(cols):
            x, y = x0 + c * cell, y0 + r * cell
            b = bias(c, r) if callable(bias) else bias
            flip = rng.random() < b
            if style == "diagonal":
                out.append([(x, y), (x + cell, y + cell)] if flip else [(x + cell, y), (x, y + cell)])
            elif style == "dreiecke":
                k = rng.randrange(4)
                corners = [(x, y), (x + cell, y), (x + cell, y + cell), (x, y + cell)]
                out.append([corners[k], corners[(k + 1) % 4], corners[(k + 2) % 4]])
            else:
                h = cell / 2
                if flip:
                    out.append(_arc(x, y, h, 0, math.pi / 2))
                    out.append(_arc(x + cell, y + cell, h, math.pi, 1.5 * math.pi))
                else:
                    out.append(_arc(x + cell, y, h, math.pi / 2, math.pi))
                    out.append(_arc(x, y + cell, h, 1.5 * math.pi, 2 * math.pi))
    return out


@tool("Muster")
def join_paths(paths, tolerance=0.01):
    """Verbindet Linien mit gemeinsamen Endpunkten zu langen Linien (z. B. Truchet-Bögen → Schlangen)."""
    paths = [list(p) for p in paths if len(p) >= 2]
    key = lambda p: (round(p[0] / tolerance), round(p[1] / tolerance))
    ends: dict = {}
    for i, p in enumerate(paths):
        ends.setdefault(key(p[0]), []).append(i)
        ends.setdefault(key(p[-1]), []).append(i)
    used = [False] * len(paths)
    out = []
    for i in range(len(paths)):
        if used[i]:
            continue
        used[i] = True
        line = paths[i][:]
        for forward in (True, False):
            while True:
                tip = line[-1] if forward else line[0]
                nxt = next((j for j in ends.get(key(tip), ()) if not used[j]), None)
                if nxt is None:
                    break
                used[nxt] = True
                seg = paths[nxt]
                if key(seg[0]) != key(tip):
                    seg = seg[::-1]
                line = line + seg[1:] if forward else seg[::-1][:-1] + line
        out.append(line)
    return out


# ---------------------------------------------------------------------------- Delaunay
@tool("Muster")
def delaunay(points):
    """Delaunay-Triangulation → Dreiecke als Index-Tripel [(i, j, k), …] (Bowyer–Watson; scipy, wenn vorhanden)."""
    pts = [(float(p[0]), float(p[1])) for p in points]
    if len(pts) < 3:
        return []
    try:
        from scipy.spatial import Delaunay as _D
        return [tuple(int(v) for v in t) for t in _D(pts).simplices]
    except Exception:
        pass
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    mx, my = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    d = max(max(xs) - min(xs), max(ys) - min(ys)) * 20 + 1
    P = pts + [(mx - d, my - d), (mx + d, my - d), (mx, my + d)]
    n = len(pts)

    def circ(a, b, c):
        (ax, ay), (bx, by), (cx, cy) = P[a], P[b], P[c]
        D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(D) < 1e-12:
            return (0.0, 0.0, float("inf"))
        ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / D
        uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / D
        return (ux, uy, (ax - ux) ** 2 + (ay - uy) ** 2)

    tris = {(n, n + 1, n + 2): circ(n, n + 1, n + 2)}
    order = sorted(range(n), key=lambda i: (pts[i][0], pts[i][1]))
    for i in order:
        x, y = P[i]
        bad = [t for t, (ux, uy, r2) in tris.items() if (x - ux) ** 2 + (y - uy) ** 2 < r2 - 1e-9]
        edges: dict = {}
        for t in bad:
            for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                k = tuple(sorted(e))
                edges[k] = edges.get(k, 0) + 1
            del tris[t]
        for (a, b), cnt in edges.items():
            if cnt == 1:
                tris[(a, b, i)] = circ(a, b, i)
    return [t for t in tris if max(t) < n]


@tool("Muster")
def delaunay_edges(points):
    """Kanten der Delaunay-Triangulation [(i, j)] (jede Kante einmal)."""
    edges = set()
    for a, b, c in delaunay(points):
        for e in ((a, b), (b, c), (c, a)):
            edges.add(tuple(sorted(e)))
    return sorted(edges)


# ---------------------------------------------------------------------------- TSP art
@tool("Muster")
def tsp_path(points, max_seconds=2.0, closed=False):
    """Kurze Rundreise durch alle Punkte (nächster Nachbar + 2-opt) → Punkte in Reihenfolge.

    Mit Stippling-Punkten eines Bildes entsteht „TSP-Kunst“: das ganze Bild aus einer einzigen Linie.
    """
    pts = [(float(p[0]), float(p[1])) for p in points]
    n = len(pts)
    if n < 4:
        return pts
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    area = (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1)
    cell = math.sqrt(area / n) * 2
    grid = SpatialGrid.of_points(pts, cell)
    # nearest-neighbour tour
    used = [False] * n
    tour = [0]
    used[0] = True
    grid.remove(*pts[0], 0)
    cur = 0
    diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) + cell
    for _ in range(n - 1):
        x, y = pts[cur]
        r = cell
        while True:
            best, bd = None, float("inf")
            for j in grid.near(x, y, r):
                d = (pts[j][0] - x) ** 2 + (pts[j][1] - y) ** 2
                if d < bd:
                    best, bd = j, d
            # everything within r lies in the searched cells → the best one is the true nearest
            if best is not None and (bd <= r * r or r > diag):
                break
            r *= 2
        used[best] = True
        grid.remove(pts[best][0], pts[best][1], best)
        tour.append(best)
        cur = best
    # 2-opt with neighbour lists and a time budget
    K = 8
    grid = SpatialGrid.of_points(pts, cell)
    neigh = []
    for i, (x, y) in enumerate(pts):
        cand = sorted((j for j in grid.near(x, y, cell * 1.5) if j != i),
                      key=lambda j: (pts[j][0] - x) ** 2 + (pts[j][1] - y) ** 2)[:K]
        neigh.append(cand)
    pos = [0] * n
    for i, c in enumerate(tour):
        pos[c] = i

    def dist(a, b):
        return math.hypot(pts[a][0] - pts[b][0], pts[a][1] - pts[b][1])

    deadline = time.perf_counter() + max_seconds
    improved = True
    while improved and time.perf_counter() < deadline:
        improved = False
        for i in range(n - 1):
            a, b = tour[i], tour[i + 1]
            dab = dist(a, b)
            for c in neigh[a]:
                j = pos[c]
                if j == i or j == i + 1 or j >= n - 1:
                    continue
                d = tour[j + 1]
                if d == a:
                    continue
                delta = dist(a, c) + dist(b, d) - dab - dist(c, d)
                if delta < -1e-9:
                    lo, hi = (i + 1, j) if j > i else (j + 1, i)     # reverse the stretch between both edges
                    tour[lo:hi + 1] = tour[lo:hi + 1][::-1]
                    for k in range(lo, hi + 1):
                        pos[tour[k]] = k
                    improved = True
                    break
            if time.perf_counter() > deadline:
                break
    # long edges are what the eye notices: check each of them against every other edge
    lengths = sorted(dist(tour[i], tour[i + 1]) for i in range(n - 1))
    limit = lengths[len(lengths) // 2] * 4
    changed = True
    while changed and time.perf_counter() < deadline + max_seconds * 0.5:
        changed = False
        for i in range(n - 1):
            a, b = tour[i], tour[i + 1]
            dab = dist(a, b)
            if dab <= limit:
                continue
            best, best_j = -1e-9, -1
            for j in range(n - 1):
                if abs(j - i) < 2:
                    continue
                c, d = tour[j], tour[j + 1]
                delta = dist(a, c) + dist(b, d) - dab - dist(c, d)
                if delta < best:
                    best, best_j = delta, j
            if best_j >= 0:
                lo, hi = (i + 1, best_j) if best_j > i else (best_j + 1, i)
                tour[lo:hi + 1] = tour[lo:hi + 1][::-1]
                changed = True
    out = [pts[i] for i in tour]
    return out + [out[0]] if closed else out


# ---------------------------------------------------------------------------- contours
@tool("Muster")
def contour_lines(field, levels, x0=0.0, y0=0.0, cell=1.0):
    """Höhenlinien (Marching Squares) eines 2D-Felds (Liste von Zeilen oder numpy-Array) → [[(x, y), …]].

    levels: eine Zahl oder eine Liste von Höhen. Ein Feldpunkt [zeile][spalte] liegt bei
    (x0 + spalte·cell, y0 + zeile·cell). Für Funktionen siehe contours().
    """
    if hasattr(field, "tolist"):
        field = field.tolist()
    rows, cols = len(field), len(field[0])
    lv = [levels] if isinstance(levels, (int, float)) else list(levels)
    out = []
    for level in lv:
        level = level + 1e-9 * (abs(level) + 1)       # values exactly on the level would create junctions
        segs = []
        for r in range(rows - 1):
            f0, f1 = field[r], field[r + 1]
            for c in range(cols - 1):
                a, b, cc, d = f0[c], f0[c + 1], f1[c + 1], f1[c]          # tl, tr, br, bl
                idx = (a > level) << 3 | (b > level) << 2 | (cc > level) << 1 | (d > level)
                if idx in (0, 15):
                    continue

                def lerp(v1, v2, p1, p2):
                    t = 0.5 if v1 == v2 else (level - v1) / (v2 - v1)
                    return (x0 + (p1[0] + (p2[0] - p1[0]) * t) * cell, y0 + (p1[1] + (p2[1] - p1[1]) * t) * cell)
                top = lerp(a, b, (c, r), (c + 1, r))
                right = lerp(b, cc, (c + 1, r), (c + 1, r + 1))
                bottom = lerp(d, cc, (c, r + 1), (c + 1, r + 1))
                left = lerp(a, d, (c, r), (c, r + 1))
                table = {1: [(left, bottom)], 2: [(bottom, right)], 3: [(left, right)], 4: [(top, right)],
                         5: [(left, top), (bottom, right)], 6: [(top, bottom)], 7: [(left, top)],
                         8: [(left, top)], 9: [(top, bottom)], 10: [(left, bottom), (top, right)],
                         11: [(top, right)], 12: [(left, right)], 13: [(bottom, right)], 14: [(left, bottom)]}
                segs.extend(table[idx])
        tol = cell * 1e-4
        segs = [s for s in segs if math.dist(s[0], s[1]) > tol]       # drop degenerate bits at grid nodes
        out.extend(join_paths([list(s) for s in segs], tolerance=tol))
    return out


@tool("Muster")
def contours(fn, levels, width, height, resolution=4.0, x0=0.0, y0=0.0):
    """Höhenlinien einer Funktion fn(x, y) → Linien. Beispiel: contours(lambda x, y: noise(x*0.01, y*0.01), 12, width, height)."""
    if isinstance(levels, int) and not isinstance(levels, bool):
        n = levels
        levels = [(i + 0.5) / n for i in range(n)]
    cols = int(width / resolution) + 1
    rows = int(height / resolution) + 1
    field = [[fn(x0 + c * resolution, y0 + r * resolution) for c in range(cols)] for r in range(rows)]
    return contour_lines(field, levels, x0, y0, resolution)


# ---------------------------------------------------------------------------- streamlines
@tool("Muster", needs_rng=True)
def streamlines(angle, width, height, spacing=10.0, step=1.0, min_length=10, max_steps=2000, x0=0.0, y0=0.0,
                test=0.6, rng=None):
    """Gleichmäßig verteilte Stromlinien durch ein Richtungsfeld (Jobard & Lefer) → [[(x, y), …]].

    angle(x, y) liefert die Richtung im Bogenmaß, z. B. lambda x, y: noise(x*0.005, y*0.005) * TAU * 2.
    spacing = Abstand der Linien; test = wie nah Linien sich kommen dürfen (Anteil von spacing).
    """
    grid = SpatialGrid(spacing)
    lines = []
    dtest2 = (spacing * test) ** 2
    dsep2 = spacing ** 2

    def free(x, y, d2, own=None):
        if not (x0 <= x <= x0 + width and y0 <= y <= y0 + height):
            return False
        for li, (px, py) in grid.near(x, y, spacing):
            if li == own:
                continue
            if (px - x) ** 2 + (py - y) ** 2 < d2:
                return False
        return True

    def trace(x, y, sign, own):
        pts = []
        for _ in range(max_steps):
            a = angle(x, y)
            nx, ny = x + math.cos(a) * step * sign, y + math.sin(a) * step * sign
            if not free(nx, ny, dtest2, own):
                break
            # stop on closed loops: back near its own early points
            if len(pts) > 20 and (nx - pts[0][0]) ** 2 + (ny - pts[0][1]) ** 2 < (step * 1.5) ** 2:
                break
            pts.append((nx, ny))
            x, y = nx, ny
        return pts

    def add_line(x, y):
        li = len(lines)
        fwd = trace(x, y, 1, li)
        back = trace(x, y, -1, li)
        line = back[::-1] + [(x, y)] + fwd
        if len(line) < min_length:
            return None
        for p in line:
            grid.insert(p[0], p[1], (li, p))
        lines.append(line)
        return line

    queue = []
    sx, sy = x0 + width * (0.3 + 0.4 * rng.random()), y0 + height * (0.3 + 0.4 * rng.random())
    first = add_line(sx, sy)
    if first:
        queue.append(first)
    # seed further lines beside existing ones; random seeds fill disconnected regions
    tries = 0
    while True:
        while queue:
            line = queue.pop(0)
            for k in range(0, len(line), max(1, int(spacing / step / 2))):
                x, y = line[k]
                a = angle(x, y)
                for side in (1, -1):
                    cx, cy = x - math.sin(a) * spacing * side, y + math.cos(a) * spacing * side
                    if free(cx, cy, dsep2):
                        new = add_line(cx, cy)
                        if new:
                            queue.append(new)
        found = False
        while tries < 200 and not found:
            tries += 1
            cx, cy = x0 + rng.random() * width, y0 + rng.random() * height
            if free(cx, cy, dsep2):
                new = add_line(cx, cy)
                if new:
                    queue.append(new)
                    found = True
        if not found:
            break
    return lines


# ---------------------------------------------------------------------------- L-systems
@tool("Muster", needs_rng=True)
def lsystem(axiom, rules, iterations=4, max_length=500000, rng=None):
    """L-System: Ersetzungsregeln anwenden → Zeichenkette. rules = {"F": "F[+F]F[-F]F"}.

    Zufällige Regeln: {"F": [("F[+F]F", 0.6), ("F[-F]F", 0.4)]}.
    """
    s = str(axiom)
    for _ in range(int(iterations)):
        out = []
        for ch in s:
            r = rules.get(ch)
            if r is None:
                out.append(ch)
            elif isinstance(r, str):
                out.append(r)
            else:
                tot = sum(w for _, w in r)
                x = rng.random() * tot
                for txt, w in r:
                    x -= w
                    if x <= 0:
                        out.append(txt)
                        break
                else:
                    out.append(r[-1][0])
        s = "".join(out)
        if len(s) > max_length:
            raise ValueError(f"L-System zu lang ({len(s)} Zeichen) – weniger Iterationen wählen")
    return s


@tool("Muster", needs_rng=True)
def turtle(commands, x=0.0, y=0.0, heading=-90.0, step=10.0, angle=25.0, shrink=1.0, jitter=0.0, rng=None):
    """Turtle-Grafik für L-Systeme → Linien [[(x, y), …]] (je Ast eine Linie).

    F/G: vorwärts zeichnen · f: vorwärts ohne Strich · + / -: drehen · [ ]: Ast merken/zurück ·
    | umdrehen. heading in Grad (-90 = nach oben). shrink verkürzt Äste pro Ebene; jitter = Zufallswinkel.
    """
    a = math.radians(heading)
    da = math.radians(angle)
    stack = []
    lines = []
    cur = [(x, y)]
    length = step
    for ch in commands:
        if ch in "FG":
            x += math.cos(a) * length
            y += math.sin(a) * length
            cur.append((x, y))
        elif ch == "f":
            x += math.cos(a) * length
            y += math.sin(a) * length
            if len(cur) > 1:
                lines.append(cur)
            cur = [(x, y)]
        elif ch in "+-":
            j = (rng.random() - 0.5) * 2 * math.radians(jitter) if jitter else 0.0
            a += (da if ch == "+" else -da) + j
        elif ch == "|":
            a += math.pi
        elif ch == "[":
            stack.append((x, y, a, length))
            length *= shrink
        elif ch == "]":
            if len(cur) > 1:
                lines.append(cur)
            x, y, a, length = stack.pop()
            cur = [(x, y)]
    if len(cur) > 1:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------------------- circle packing
@tool("Muster", needs_rng=True)
def circle_packing(width, height, min_r=2.0, max_r=60.0, attempts=5000, padding=1.0, x0=0.0, y0=0.0,
                   inside=None, max_circles=5000, rng=None):
    """Kreispackung: Kreise, die sich nicht überlappen → [(x, y, r)], große zuerst.

    inside(x, y) → bool beschränkt auf eine Form (z. B. Buchstaben, Bildbereiche).
    """
    circles = []
    grid = SpatialGrid(max_r * 2)
    for _ in range(int(attempts)):
        if len(circles) >= max_circles:
            break
        x, y = x0 + rng.random() * width, y0 + rng.random() * height
        if inside is not None and not inside(x, y):
            continue
        r = min(max_r, x - x0, x0 + width - x, y - y0, y0 + height - y)
        for j in grid.near(x, y, max_r * 2 + padding):
            cx, cy, cr = circles[j]
            r = min(r, math.hypot(cx - x, cy - y) - cr - padding)
            if r < min_r:
                break
        if r >= min_r:
            circles.append((x, y, r))
            grid.insert(x, y, len(circles) - 1)
    circles.sort(key=lambda c: -c[2])
    return circles
