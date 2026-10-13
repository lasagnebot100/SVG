"""Hidden-line removal for plotter output (pure Python).

A screen shows overlaps by painting over them – a pen plotter draws every line.
Occluder processes the shapes in painting order: an opaque filled shape erases the
parts of all earlier lines that lie inside it, then its own outline is added. The
result is what you would see, as lines only (3D scenes, overlapping circles, …).
"""
from __future__ import annotations

import math


class Occluder:
    def __init__(self, width: float, height: float, cells: int = 64, eps: float = 1e-6):
        self.cell = max(width, height, 1e-9) / cells
        self.eps = eps
        self.grid: dict = {}
        self.segs: dict = {}         # id → (x0, y0, x1, y1, layer, key=(polyline, segment, t0, t1))
        self._next = 0
        self._poly = 0

    # ------------------------------------------------------------- spatial index
    def _cells(self, x0, y0, x1, y1):
        c = self.cell
        for gx in range(int(math.floor(min(x0, x1) / c)), int(math.floor(max(x0, x1) / c)) + 1):
            for gy in range(int(math.floor(min(y0, y1) / c)), int(math.floor(max(y0, y1) / c)) + 1):
                yield gx, gy

    def _insert(self, x0, y0, x1, y1, layer, key):
        sid = self._next
        self._next += 1
        self.segs[sid] = (x0, y0, x1, y1, layer, key)
        for cell in self._cells(x0, y0, x1, y1):
            self.grid.setdefault(cell, set()).add(sid)

    def _remove(self, sid):
        x0, y0, x1, y1, *_ = self.segs.pop(sid)
        for cell in self._cells(x0, y0, x1, y1):
            s = self.grid.get(cell)
            if s is not None:
                s.discard(sid)

    def _duplicate(self, x0, y0, x1, y1, layer) -> bool:
        e = self.eps * 10
        for cell in self._cells(x0, y0, x0, y0):
            for sid in self.grid.get(cell, ()):
                a0, b0, a1, b1, lay, _ = self.segs[sid]
                if lay != layer:
                    continue
                if (abs(a0 - x0) < e and abs(b0 - y0) < e and abs(a1 - x1) < e and abs(b1 - y1) < e) or \
                   (abs(a0 - x1) < e and abs(b0 - y1) < e and abs(a1 - x0) < e and abs(b1 - y0) < e):
                    return True
        return False

    # ------------------------------------------------------------- public
    def add_line(self, pts, layer):
        """A visible polyline (later shapes may still hide parts of it)."""
        pl = self._poly
        self._poly += 1
        for k in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[k], pts[k + 1]
            if abs(x0 - x1) < self.eps and abs(y0 - y1) < self.eps:
                continue
            if not self._duplicate(x0, y0, x1, y1, layer):       # shared edges of neighbouring faces
                self._insert(x0, y0, x1, y1, layer, (pl, k, 0.0, 1.0))

    def clear(self):
        """An opaque background hides everything drawn so far."""
        self.grid.clear()
        self.segs.clear()

    def occlude(self, rings, evenodd: bool = False):
        """Erase everything inside the filled region `rings` (list of closed point lists)."""
        rings = [r for r in rings if len(r) >= 3]
        if not rings:
            return
        edges = []
        for r in rings:
            for k in range(len(r)):
                edges.append((r[k], r[(k + 1) % len(r)]))
        xs = [p[0] for r in rings for p in r]
        ys = [p[1] for r in rings for p in r]
        bx0, by0, bx1, by1 = min(xs), min(ys), max(xs), max(ys)
        cand = set()
        for cell in self._cells(bx0, by0, bx1, by1):
            cand |= self.grid.get(cell, set())
        for sid in cand:
            x0, y0, x1, y1, layer, key = self.segs[sid]
            if max(x0, x1) < bx0 or min(x0, x1) > bx1 or max(y0, y1) < by0 or min(y0, y1) > by1:
                continue
            ts = [0.0, 1.0]
            for (ax, ay), (bx, by) in edges:
                t = _intersect(x0, y0, x1, y1, ax, ay, bx, by)
                if t is not None:
                    ts.append(t)
            ts.sort()
            keep = []
            dx, dy = x1 - x0, y1 - y0
            for ta, tb in zip(ts, ts[1:]):
                if tb - ta < 1e-9:
                    continue
                tm = (ta + tb) / 2
                mx, my = x0 + dx * tm, y0 + dy * tm
                if _inside(mx, my, rings, evenodd) and _edge_dist(mx, my, edges) > self.eps * 100:
                    continue
                if keep and abs(keep[-1][1] - ta) < 1e-12:
                    keep[-1] = (keep[-1][0], tb)            # merge neighbouring visible pieces
                else:
                    keep.append((ta, tb))
            if keep == [(0.0, 1.0)]:
                continue
            self._remove(sid)
            pl, k, a, b = key
            for ta, tb in keep:
                self._insert(x0 + dx * ta, y0 + dy * ta, x0 + dx * tb, y0 + dy * tb, layer,
                             (pl, k, a + (b - a) * ta, a + (b - a) * tb))

    def polylines(self):
        """→ [(points, layer)], neighbouring pieces joined again."""
        order = sorted(self.segs.values(), key=lambda s: s[5])
        out = []
        cur, cur_key, cur_layer = None, None, None
        for x0, y0, x1, y1, layer, key in order:
            if cur is not None and key[0] == cur_key and layer == cur_layer and \
               abs(cur[-1][0] - x0) < 1e-6 and abs(cur[-1][1] - y0) < 1e-6:
                cur.append((x1, y1))
                continue
            if cur is not None:
                out.append((cur, cur_layer))
            cur, cur_key, cur_layer = [(x0, y0), (x1, y1)], key[0], layer
        if cur is not None:
            out.append((cur, cur_layer))
        return out


def _intersect(x0, y0, x1, y1, ax, ay, bx, by):
    """Parameter t on segment 0→1 where it crosses segment a→b (or None)."""
    dx, dy = x1 - x0, y1 - y0
    ex, ey = bx - ax, by - ay
    den = dx * ey - dy * ex
    if abs(den) < 1e-15:
        return None
    t = ((ax - x0) * ey - (ay - y0) * ex) / den
    u = ((ax - x0) * dy - (ay - y0) * dx) / den
    if 0.0 < t < 1.0 and -1e-12 <= u <= 1.0 + 1e-12:
        return t
    return None


def _inside(x, y, rings, evenodd):
    wn = 0
    crossings = 0
    for r in rings:
        n = len(r)
        for k in range(n):
            (ax, ay), (bx, by) = r[k], r[(k + 1) % n]
            if (ay <= y) != (by <= y):
                xc = ax + (y - ay) * (bx - ax) / (by - ay)
                if xc > x:
                    crossings += 1
                    wn += 1 if by > ay else -1
    return (crossings % 2 == 1) if evenodd else wn != 0


def _edge_dist(x, y, edges):
    best = math.inf
    for (ax, ay), (bx, by) in edges:
        ex, ey = bx - ax, by - ay
        ll = ex * ex + ey * ey
        t = 0.0 if ll == 0 else max(0.0, min(1.0, ((x - ax) * ex + (y - ay) * ey) / ll))
        d = math.hypot(x - ax - ex * t, y - ay - ey * t)
        if d < best:
            best = d
    return best
