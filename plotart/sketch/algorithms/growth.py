"""Growth algorithms: differential growth, diffusion-limited aggregation, space colonization."""
from __future__ import annotations

import math

from ..tools import tool
from ._grid import SpatialGrid


# ---------------------------------------------------------------------------- differential growth
@tool("Wachstum", needs_rng=True)
class DifferentialGrowth:
    """Wachsende Linie, die sich wie Koralle faltet: g = DifferentialGrowth(punkte); g.step(); g.points.

    Nachbarn halten sich wie Federn zusammen, alle anderen Knoten in der Nähe stoßen sich ab,
    zufällig eingefügte Knoten erzeugen Druck – die Linie faltet sich, ohne sich zu kreuzen.
    closed=True: geschlossene Schleife. growth: Anteil neuer Knoten pro Schritt.
    bounds=(x0, y0, x1, y1) oder eine Funktion inside(x, y) → bool begrenzt das Wachstum.
    """

    def __init__(self, points, closed=True, max_edge=6.0, radius=None, attraction=0.3, repulsion=0.5,
                 alignment=0.1, growth=0.02, max_move=1.5, bounds=None, max_nodes=6000, rng=None):
        if rng is None:
            import random
            rng = random.Random(1)
        self.pts = [[float(p[0]), float(p[1])] for p in points]
        if len(self.pts) < 2:
            raise ValueError("DifferentialGrowth braucht mindestens 2 Startpunkte")
        self.closed = bool(closed)
        self.max_edge = float(max_edge)
        self.rest = self.max_edge * 0.6
        self.radius = float(radius) if radius else self.max_edge * 2.0
        self.attraction, self.repulsion, self.alignment = float(attraction), float(repulsion), float(alignment)
        self.growth = float(growth)
        self.max_move = float(max_move)
        self.bounds = bounds
        self.max_nodes = int(max_nodes)
        self.rng = rng
        self.steps = 0
        self._subdivide()

    @property
    def points(self):
        return [tuple(p) for p in self.pts]

    def __len__(self):
        return len(self.pts)

    def _inside(self, x, y):
        b = self.bounds
        if b is None:
            return True
        if callable(b):
            return bool(b(x, y))
        return b[0] <= x <= b[2] and b[1] <= y <= b[3]

    def _subdivide(self, extra=0):
        """Split edges longer than max_edge, plus `extra` random edges (growth pressure)."""
        pts = self.pts
        n = len(pts)
        edges = n if self.closed else n - 1
        rnd = set()
        if extra and edges > 0:
            for _ in range(extra):
                rnd.add(self.rng.randrange(edges))
        out = []
        budget = self.max_nodes - n
        for i in range(n):
            out.append(pts[i])
            if i < edges and budget > 0:
                a, b = pts[i], pts[(i + 1) % n]
                if i in rnd or math.dist(a, b) > self.max_edge:
                    out.append([(a[0] + b[0]) * 0.5 + (self.rng.random() - 0.5) * 0.02,
                                (a[1] + b[1]) * 0.5 + (self.rng.random() - 0.5) * 0.02])
                    budget -= 1
        self.pts = out

    def step(self, n=1):
        """n Wachstumsschritte; gibt sich selbst zurück."""
        for _ in range(int(n)):
            self._step()
        return self

    def _step(self):
        try:
            import numpy as np
        except ImportError:
            np = None
        if np is not None and len(self.pts) > 200 and not callable(self.bounds):
            self._step_numpy(np)
        else:
            self._step_python()
        if len(self.pts) < self.max_nodes:
            self._subdivide(extra=max(1, int(len(self.pts) * self.growth)) if self.growth > 0 else 0)
        self.steps += 1

    def _step_numpy(self, np):
        """Same forces as _step_python, vectorised; neighbour pairs via a sweep along x."""
        P = np.asarray(self.pts, dtype=float)
        n = len(P)
        R, rest = self.radius, self.rest
        F = np.zeros_like(P)
        idx = np.arange(n)
        if self.closed:
            prv, nxt = np.roll(idx, 1), np.roll(idx, -1)
            vp = vn = np.ones(n, bool)
        else:
            prv, nxt = np.maximum(idx - 1, 0), np.minimum(idx + 1, n - 1)
            vp, vn = idx > 0, idx < n - 1
        for nb, valid in ((prv, vp), (nxt, vn)):                # springs
            D = P[nb] - P
            d = np.hypot(D[:, 0], D[:, 1])
            m = valid & (d > rest)
            f = np.zeros(n)
            f[m] = (d[m] - rest) / d[m] * self.attraction
            F += D * f[:, None]
        both = vp & vn                                         # smoothing
        F[both] += ((P[prv] + P[nxt]) * 0.5 - P)[both] * self.alignment
        order = np.argsort(P[:, 0])                            # repulsion: sweep along x
        S = P[order]
        for k in range(1, n):
            dx = S[k:, 0] - S[:-k, 0]
            if not (dx < R).any():
                break
            dy = S[k:, 1] - S[:-k, 1]
            d2 = dx * dx + dy * dy
            m = (dx < R) & (d2 < R * R) & (d2 > 1e-12)
            if not m.any():
                continue
            a, b = order[k:][m], order[:-k][m]
            gap = np.abs(a - b)
            keep = (gap != 1) & ~(self.closed & (gap == n - 1))
            a, b = a[keep], b[keep]
            if not len(a):
                continue
            D = P[a] - P[b]
            d = np.sqrt(d2[m][keep])
            f = ((R - d) / (R * d) * self.repulsion)[:, None] * D
            np.add.at(F, a, f)
            np.add.at(F, b, -f)
        mag = np.hypot(F[:, 0], F[:, 1])
        big = mag > self.max_move
        F[big] *= (self.max_move / mag[big])[:, None]
        N = P + F
        b = self.bounds
        if b is not None:
            out = (N[:, 0] < b[0]) | (N[:, 0] > b[2]) | (N[:, 1] < b[1]) | (N[:, 1] > b[3])
            N[out] = P[out]
        if not self.closed:
            N[0], N[-1] = P[0], P[-1]
        self.pts = N.tolist()

    def _step_python(self):
        pts = self.pts
        n = len(pts)
        R = self.radius
        R2 = R * R
        grid = SpatialGrid.of_points(pts, R)
        closed = self.closed
        att, rep, ali, mm, rest = self.attraction, self.repulsion, self.alignment, self.max_move, self.rest
        new = []
        for i in range(n):
            x, y = pts[i]
            fx = fy = 0.0
            prv = i - 1 if (closed or i > 0) else None
            nxt = (i + 1) % n if (closed or i < n - 1) else None
            nb = [k for k in (prv, nxt) if k is not None]
            for k in nb:                                       # springs to the neighbours
                dx, dy = pts[k][0] - x, pts[k][1] - y
                d = math.hypot(dx, dy)
                if d > rest:
                    f = (d - rest) / d * att
                    fx += dx * f
                    fy += dy * f
            if len(nb) == 2:                                   # smoothing towards the neighbours' midpoint
                fx += ((pts[nb[0]][0] + pts[nb[1]][0]) * 0.5 - x) * ali
                fy += ((pts[nb[0]][1] + pts[nb[1]][1]) * 0.5 - y) * ali
            for j in grid.near(x, y, R):                       # repulsion from everything else nearby
                if j == i or j == prv or j == nxt:
                    continue
                dx, dy = x - pts[j][0], y - pts[j][1]
                d2 = dx * dx + dy * dy
                if 1e-12 < d2 < R2:
                    d = math.sqrt(d2)
                    f = (R - d) / (R * d) * rep
                    fx += dx * f
                    fy += dy * f
            m = math.hypot(fx, fy)
            if m > mm:
                fx, fy = fx / m * mm, fy / m * mm
            nx, ny = x + fx, y + fy
            if not self._inside(nx, ny):
                nx, ny = x, y
            new.append([nx, ny])
        if not closed:                                        # open lines: the ends stay put
            new[0], new[-1] = list(pts[0]), list(pts[-1])
        self.pts = new


@tool("Wachstum", needs_rng=True)
def differential_growth(points, steps=150, closed=True, max_edge=6.0, bounds=None, max_nodes=6000, rng=None,
                        **kw):
    """Lässt eine Linie `steps` Schritte wachsen und gibt die Punkte zurück (Standbild-Variante)."""
    g = DifferentialGrowth(points, closed=closed, max_edge=max_edge, bounds=bounds, max_nodes=max_nodes,
                           rng=rng, **kw)
    g.step(steps)
    return g.points


# ---------------------------------------------------------------------------- DLA
@tool("Wachstum", needs_rng=True)
class DLA:
    """Diffusionsbegrenztes Wachstum: Teilchen irren umher und bleiben am Gebilde kleben (Korallen, Frost, Blitze).

    d = DLA(seeds=[(400, 400)], step=3); d.grow(2000); d.particles → [(x, y, eltern_index)].
    bias=(bx, by) gibt den Teilchen eine Drift (z. B. (0, 0.3) = fallen nach unten);
    stickiness < 1 macht das Gebilde dichter, buschiger.
    """

    def __init__(self, seeds=((0.0, 0.0),), step=3.0, stickiness=1.0, bias=(0.0, 0.0), bounds=None, rng=None):
        if rng is None:
            import random
            rng = random.Random(1)
        self.rng = rng
        self.step_len = float(step)
        self.stick = float(stickiness)
        self.bias = (float(bias[0]), float(bias[1]))
        self.bounds = bounds
        self.particles: list = []
        self.grid = SpatialGrid(self.step_len * 2)
        for s in seeds:
            self._add(float(s[0]), float(s[1]), -1)
        self.cx = sum(p[0] for p in self.particles) / len(self.particles)
        self.cy = sum(p[1] for p in self.particles) / len(self.particles)
        self.radius = max(math.dist((self.cx, self.cy), p[:2]) for p in self.particles)

    def _add(self, x, y, parent):
        self.particles.append((x, y, parent))
        self.grid.insert(x, y, len(self.particles) - 1)

    def _nearest(self, x, y, r):
        best, bd = -1, r * r
        for j in self.grid.near(x, y, r):
            px, py, _ = self.particles[j]
            d = (px - x) ** 2 + (py - y) ** 2
            if d <= bd:
                best, bd = j, d
        return best

    def grow(self, n=100, max_walk=20000):
        """Fügt n Teilchen hinzu (jedes wandert, bis es klebt)."""
        rng, s = self.rng, self.step_len
        stick_r = s * 2
        for _ in range(int(n)):
            for _attempt in range(50):
                a = rng.random() * math.tau
                spawn = self.radius + 6 * s
                x, y = self.cx + math.cos(a) * spawn, self.cy + math.sin(a) * spawn
                stuck = False
                for _w in range(max_walk):
                    d = math.hypot(x - self.cx, y - self.cy)
                    if d > spawn * 2 + 50:
                        break                                      # wandered off – start again
                    gap = d - self.radius - 2 * stick_r
                    step = max(s, gap) if gap > 0 else s           # big jumps while far away
                    a = rng.random() * math.tau
                    x += math.cos(a) * step + self.bias[0] * s
                    y += math.sin(a) * step + self.bias[1] * s
                    if self.bounds is not None:
                        b = self.bounds
                        x = min(max(x, b[0]), b[2])
                        y = min(max(y, b[1]), b[3])
                    if gap <= 0:
                        j = self._nearest(x, y, stick_r)
                        if j >= 0 and (self.stick >= 1 or rng.random() < self.stick):
                            px, py, _ = self.particles[j]
                            dd = math.hypot(x - px, y - py) or 1.0
                            x, y = px + (x - px) / dd * s, py + (y - py) / dd * s   # exactly one step away
                            self._add(x, y, j)
                            self.radius = max(self.radius, math.hypot(x - self.cx, y - self.cy))
                            stuck = True
                            break
                if stuck:
                    break
        return self

    @property
    def segments(self):
        """Linien Eltern → Kind: [(x1, y1, x2, y2), …]."""
        p = self.particles
        return [(p[k][0], p[k][1], x, y) for x, y, k in p if k >= 0]

    def depths(self):
        """Generation jedes Teilchens (0 = Keim) – für Farbe oder Strichstärke."""
        out = []
        for x, y, k in self.particles:
            out.append(0 if k < 0 else out[k] + 1)
        return out


@tool("Wachstum", needs_rng=True)
def dla(n=1500, seeds=((0.0, 0.0),), step=3.0, stickiness=1.0, bias=(0.0, 0.0), bounds=None, rng=None):
    """DLA als Standbild: gibt die Linien [(x1, y1, x2, y2), …] des gewachsenen Gebildes zurück."""
    return DLA(seeds, step, stickiness, bias, bounds, rng=rng).grow(n).segments


# ---------------------------------------------------------------------------- space colonization
@tool("Wachstum")
class SpaceColonization:
    """Äste wachsen zu Lichtpunkten hin (Bäume, Adern, Wurzeln, Blitze) – Runions et al.

    sc = SpaceColonization(lichtpunkte, wurzeln=[(400, 780)], segment=6); sc.grow()
    sc.branches → [(x1, y1, x2, y2, dicke)], dicke nach dem Pipe-Modell (dicke Äste an der Wurzel).
    """

    def __init__(self, attractors, roots, segment=6.0, influence=60.0, kill=10.0):
        self.attractors = [(float(a[0]), float(a[1])) for a in attractors]
        self.nodes = [(float(r[0]), float(r[1]), -1) for r in roots]
        self.segment, self.influence, self.kill = float(segment), float(influence), float(kill)
        self.grid = SpatialGrid(self.influence)
        for i, (x, y, _) in enumerate(self.nodes):
            self.grid.insert(x, y, i)
        self.done = False

    def step(self):
        """Ein Wachstumsschritt; False, wenn nichts mehr wächst."""
        if self.done:
            return False
        dirs: dict = {}
        alive = []
        kill2, inf2 = self.kill ** 2, self.influence ** 2
        for ax, ay in self.attractors:
            best, bd = -1, inf2
            reached = False
            for j in self.grid.near(ax, ay, self.influence):
                nx, ny, _ = self.nodes[j]
                d = (nx - ax) ** 2 + (ny - ay) ** 2
                if d < kill2:
                    reached = True
                    break
                if d < bd:
                    best, bd = j, d
            if reached:
                continue
            alive.append((ax, ay))
            if best >= 0:
                nx, ny, _ = self.nodes[best]
                d = math.sqrt(bd) or 1.0
                v = dirs.setdefault(best, [0.0, 0.0])
                v[0] += (ax - nx) / d
                v[1] += (ay - ny) / d
        self.attractors = alive
        if not dirs and alive:
            # trunk phase: nothing in reach yet – grow the closest node straight towards the closest light
            best = None
            for ax, ay in alive[:: max(1, len(alive) // 200)]:
                for j, (nx, ny, _) in enumerate(self.nodes[-50:], max(0, len(self.nodes) - 50)):
                    d = (ax - nx) ** 2 + (ay - ny) ** 2
                    if best is None or d < best[0]:
                        best = (d, j, ax, ay)
            d, j, ax, ay = best
            nx, ny, _ = self.nodes[j]
            d = math.sqrt(d) or 1.0
            dirs[j] = [(ax - nx) / d, (ay - ny) / d]
        grew = False
        for j, (vx, vy) in dirs.items():
            m = math.hypot(vx, vy)
            if m < 1e-9:
                continue
            nx, ny, _ = self.nodes[j]
            x, y = nx + vx / m * self.segment, ny + vy / m * self.segment
            self.nodes.append((x, y, j))
            self.grid.insert(x, y, len(self.nodes) - 1)
            grew = True
        if not grew:
            self.done = True
        return grew

    def grow(self, max_steps=400):
        """Wächst, bis alle Lichtpunkte erreicht sind oder nichts mehr wächst."""
        for _ in range(int(max_steps)):
            if not self.step():
                break
        return self

    @property
    def branches(self):
        """[(x1, y1, x2, y2, dicke)] – dicke = sqrt(Anzahl Spitzen dahinter), ab 1."""
        n = len(self.nodes)
        tips = [0] * n
        children = [0] * n
        for x, y, p in self.nodes:
            if p >= 0:
                children[p] += 1
        for i in range(n - 1, -1, -1):                     # children always come after their parent
            if children[i] == 0:
                tips[i] += 1
            p = self.nodes[i][2]
            if p >= 0:
                tips[p] += tips[i]
        out = []
        for i, (x, y, p) in enumerate(self.nodes):
            if p >= 0:
                px, py, _ = self.nodes[p]
                out.append((px, py, x, y, math.sqrt(tips[i])))
        return out


@tool("Wachstum")
def space_colonization(attractors, roots, segment=6.0, influence=60.0, kill=10.0, max_steps=400):
    """Space Colonization als Standbild → Äste [(x1, y1, x2, y2, dicke)]."""
    return SpaceColonization(attractors, roots, segment, influence, kill).grow(max_steps).branches
