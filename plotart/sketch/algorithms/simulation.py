"""Simulations: Verlet physics (particles, springs, cloth), boids, cellular automata, reaction–diffusion."""
from __future__ import annotations

import math

from ..tools import tool
from ._grid import SpatialGrid


# ---------------------------------------------------------------------------- Verlet physics
class Particle:
    __slots__ = ("x", "y", "px", "py", "pinned", "mass")

    def __init__(self, x, y, pinned=False, mass=1.0):
        self.x = self.px = float(x)
        self.y = self.py = float(y)
        self.pinned = bool(pinned)
        self.mass = float(mass)

    @property
    def pos(self):
        return (self.x, self.y)

    @property
    def velocity(self):
        return (self.x - self.px, self.y - self.py)

    def __iter__(self):
        yield self.x
        yield self.y

    def __repr__(self):
        return f"Particle({self.x:.1f}, {self.y:.1f}{', fest' if self.pinned else ''})"


@tool("Simulation")
class Physics:
    """Partikel-Physik (Verlet): Teilchen, Federn, Schwerkraft, Anziehung – für Seile, Stoff, Netze.

    w = Physics(gravity=(0, 0.3)); a = w.add(100, 100, pinned=True); b = w.add(150, 100)
    w.spring(a, b); w.step()  ·  w.particles, w.springs  ·  w.cloth(x, y, spalten, zeilen, abstand)
    """

    def __init__(self, gravity=(0.0, 0.0), drag=0.01, bounds=None, iterations=4):
        self.particles: list[Particle] = []
        self.springs: list = []                        # [a, b, ruhelänge, steifigkeit, reißt_ab]
        self.gravity = (float(gravity[0]), float(gravity[1]))
        self.drag = float(drag)
        self.bounds = bounds
        self.iterations = int(iterations)
        self.forces: list = []

    def add(self, x, y, pinned=False, mass=1.0) -> int:
        """Neues Teilchen → Index."""
        self.particles.append(Particle(x, y, pinned, mass))
        return len(self.particles) - 1

    def spring(self, a, b, length=None, stiffness=1.0, tear=None):
        """Feder zwischen Teilchen a und b (Ruhelänge = aktueller Abstand). tear: reißt ab dieser Dehnung (z. B. 2.5)."""
        pa, pb = self.particles[a], self.particles[b]
        L = math.hypot(pb.x - pa.x, pb.y - pa.y) if length is None else float(length)
        self.springs.append([a, b, L, float(stiffness), tear])
        return len(self.springs) - 1

    def attract(self, x, y, strength=1.0, radius=100.0):
        """Anziehung (negativ: Abstoßung) zu (x, y) für den nächsten Schritt – z. B. zur Maus."""
        self.forces.append((float(x), float(y), float(strength), float(radius)))

    def rope(self, x1, y1, x2, y2, segments=20, pin_start=True, pin_end=False, stiffness=1.0):
        """Seil aus Teilchen und Federn → Liste der Indizes."""
        ids = []
        for i in range(segments + 1):
            t = i / segments
            ids.append(self.add(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t,
                                pinned=(i == 0 and pin_start) or (i == segments and pin_end)))
            if i:
                self.spring(ids[-2], ids[-1], stiffness=stiffness)
        return ids

    def cloth(self, x, y, cols, rows, spacing, pin="top", stiffness=1.0, tear=None):
        """Stoff-Gitter → 2D-Liste der Indizes [zeile][spalte]. pin: "top", "corners", "none"."""
        grid = []
        for r in range(rows):
            row = []
            for c in range(cols):
                pinned = (pin == "top" and r == 0) or \
                         (pin == "corners" and r == 0 and c in (0, cols - 1))
                i = self.add(x + c * spacing, y + r * spacing, pinned=pinned)
                if c:
                    self.spring(row[-1], i, stiffness=stiffness, tear=tear)
                if r:
                    self.spring(grid[-1][c], i, stiffness=stiffness, tear=tear)
                row.append(i)
            grid.append(row)
        return grid

    def step(self, n=1):
        """n Zeitschritte rechnen."""
        for _ in range(int(n)):
            self._step()
        return self

    def _step(self):
        gx, gy = self.gravity
        keep = 1.0 - self.drag
        forces, self.forces = self.forces, []
        for p in self.particles:
            if p.pinned:
                continue
            ax, ay = gx, gy
            for fx, fy, s, r in forces:
                dx, dy = fx - p.x, fy - p.y
                d = math.hypot(dx, dy)
                if 1e-9 < d < r:
                    k = s * (1 - d / r) / d
                    ax += dx * k
                    ay += dy * k
            vx, vy = (p.x - p.px) * keep, (p.y - p.py) * keep
            p.px, p.py = p.x, p.y
            p.x += vx + ax / p.mass
            p.y += vy + ay / p.mass
        parts = self.particles
        for _ in range(self.iterations):
            broken = False
            for s in self.springs:
                a, b, L, k, tear = s
                pa, pb = parts[a], parts[b]
                dx, dy = pb.x - pa.x, pb.y - pa.y
                d = math.hypot(dx, dy) or 1e-9
                if tear is not None and d > L * tear:
                    s[3] = -1.0                                  # marked as broken
                    broken = True
                    continue
                diff = (d - L) / d * 0.5 * k
                wa = 0.0 if pa.pinned else (1.0 if pb.pinned else 1.0)
                wb = 0.0 if pb.pinned else (1.0 if pa.pinned else 1.0)
                tot = wa + wb
                if tot == 0:
                    continue
                pa.x += dx * diff * 2 * wa / tot
                pa.y += dy * diff * 2 * wa / tot
                pb.x -= dx * diff * 2 * wb / tot
                pb.y -= dy * diff * 2 * wb / tot
            if broken:
                self.springs = [s for s in self.springs if s[3] >= 0]
            b = self.bounds
            if b is not None:
                for p in parts:
                    if not p.pinned:
                        p.x = min(max(p.x, b[0]), b[2])
                        p.y = min(max(p.y, b[1]), b[3])

    @property
    def lines(self):
        """Federn als Linien [(x1, y1, x2, y2)]."""
        P = self.particles
        return [(P[a].x, P[a].y, P[b].x, P[b].y) for a, b, *_ in self.springs]


# ---------------------------------------------------------------------------- boids
class Boid:
    __slots__ = ("x", "y", "vx", "vy")

    def __init__(self, x, y, vx, vy):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy

    @property
    def angle(self):
        return math.atan2(self.vy, self.vx)

    @property
    def speed(self):
        return math.hypot(self.vx, self.vy)

    def __iter__(self):
        yield self.x
        yield self.y


@tool("Simulation", needs_rng=True)
class Flock:
    """Schwarm (Boids nach Reynolds): Trennung, Ausrichtung, Zusammenhalt – Vögel, Fische, Partikelströme.

    f = Flock(200, width, height); f.step(); for b in f.boids: … b.x, b.y, b.angle
    f.target = (x, y) zieht den Schwarm an; edges="wrap" (Ränder verbinden) oder "bounce".
    """

    def __init__(self, n, width, height, max_speed=3.0, perception=40.0, separation=1.5, alignment=1.0,
                 cohesion=1.0, edges="wrap", rng=None):
        if rng is None:
            import random
            rng = random.Random(1)
        self.w, self.h = float(width), float(height)
        self.max_speed, self.perception = float(max_speed), float(perception)
        self.separation, self.alignment, self.cohesion = float(separation), float(alignment), float(cohesion)
        self.edges = edges
        self.target = None
        self.target_strength = 0.5
        self.boids = []
        for _ in range(int(n)):
            a = rng.random() * math.tau
            s = self.max_speed * (0.5 + 0.5 * rng.random())
            self.boids.append(Boid(rng.random() * self.w, rng.random() * self.h, math.cos(a) * s, math.sin(a) * s))

    def step(self, n=1):
        for _ in range(int(n)):
            self._step()
        return self

    def _step(self):
        r = self.perception
        r2, sep2 = r * r, (r * 0.45) ** 2
        grid = SpatialGrid(r)
        for i, b in enumerate(self.boids):
            grid.insert(b.x, b.y, i)
        boids, ms = self.boids, self.max_speed
        acc = []
        for i, b in enumerate(boids):
            ax = ay = cx = cy = vx = vy = sx = sy = 0.0
            cnt = 0
            for j in grid.near(b.x, b.y, r):
                if j == i:
                    continue
                o = boids[j]
                dx, dy = o.x - b.x, o.y - b.y
                d2 = dx * dx + dy * dy
                if d2 > r2:
                    continue
                cnt += 1
                cx += o.x
                cy += o.y
                vx += o.vx
                vy += o.vy
                if d2 < sep2 and d2 > 1e-9:
                    sx -= dx / d2
                    sy -= dy / d2
            if cnt:
                ax += ((cx / cnt - b.x) * 0.01) * self.cohesion
                ay += ((cy / cnt - b.y) * 0.01) * self.cohesion
                ax += ((vx / cnt - b.vx) * 0.05) * self.alignment
                ay += ((vy / cnt - b.vy) * 0.05) * self.alignment
                ax += sx * 1.5 * self.separation
                ay += sy * 1.5 * self.separation
            if self.target is not None:
                dx, dy = self.target[0] - b.x, self.target[1] - b.y
                d = math.hypot(dx, dy) or 1.0
                ax += dx / d * 0.05 * self.target_strength
                ay += dy / d * 0.05 * self.target_strength
            if self.edges == "bounce":
                m = r
                if b.x < m: ax += 0.2
                if b.x > self.w - m: ax -= 0.2
                if b.y < m: ay += 0.2
                if b.y > self.h - m: ay -= 0.2
            acc.append((ax, ay))
        for b, (ax, ay) in zip(boids, acc):
            b.vx += ax
            b.vy += ay
            s = math.hypot(b.vx, b.vy)
            if s > ms:
                b.vx, b.vy = b.vx / s * ms, b.vy / s * ms
            elif s < ms * 0.3:
                k = ms * 0.3 / (s or 1.0)
                b.vx, b.vy = b.vx * k, b.vy * k
            b.x += b.vx
            b.y += b.vy
            if self.edges == "wrap":
                b.x %= self.w
                b.y %= self.h


# ---------------------------------------------------------------------------- cellular automata
@tool("Simulation", needs_rng=True)
def elementary_ca(rule=30, width=101, steps=100, start="mitte", wrap=True, rng=None):
    """Elementarer Zellautomat (Wolfram): Liste von Zeilen mit 0/1. start: "mitte", "zufall" oder eine Liste."""
    rule = int(rule) & 255
    if isinstance(start, (list, tuple)):
        row = [1 if v else 0 for v in start][:width] + [0] * max(0, width - len(start))
    elif start == "zufall":
        row = [1 if rng.random() < 0.5 else 0 for _ in range(width)]
    else:
        row = [0] * width
        row[width // 2] = 1
    rows = [row]
    for _ in range(int(steps) - 1):
        n = len(row)
        new = []
        for i in range(n):
            l = row[i - 1] if (i > 0 or wrap) else 0
            r = row[(i + 1) % n] if (i < n - 1 or wrap) else 0
            new.append((rule >> (l << 2 | row[i] << 1 | r)) & 1)
        row = new
        rows.append(row)
    return rows


def _parse_life_rule(rule: str):
    rule = rule.upper().replace(" ", "")
    if "/" in rule and rule[0].isdigit():                    # "23/3" (S/B notation)
        s, b = rule.split("/")
        return {int(c) for c in b}, {int(c) for c in s}
    born = survive = ""
    for part in rule.split("/"):
        if part.startswith("B"):
            born = part[1:]
        elif part.startswith("S"):
            survive = part[1:]
    return {int(c) for c in born}, {int(c) for c in survive}


@tool("Simulation", needs_rng=True)
class Life:
    """Game of Life und verwandte Regeln: lf = Life(80, 60, dichte=0.3, regel="B3/S23"); lf.step(); lf.cells[y][x].

    Andere Regeln: "B36/S23" (HighLife), "B3678/S34678" (Tag & Nacht), "B2/S" (Samen).
    lf.age[y][x] zählt, wie lange eine Zelle schon lebt – schön für Farben.
    """

    def __init__(self, cols, rows, density=0.3, rule="B3/S23", wrap=True, cells=None, rng=None):
        self.cols, self.rows = int(cols), int(rows)
        self.born, self.survive = _parse_life_rule(rule)
        self.wrap = wrap
        if cells is not None:
            self.cells = [[1 if v else 0 for v in r] for r in cells]
        else:
            if rng is None:
                import random
                rng = random.Random(1)
            self.cells = [[1 if rng.random() < density else 0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.age = [[c for c in r] for r in self.cells]
        self.generation = 0

    def step(self, n=1):
        for _ in range(int(n)):
            self._step()
        return self

    def _step(self):
        try:
            import numpy as np
        except ImportError:
            np = None
        if np is not None:
            a = np.array(self.cells, dtype=np.uint8)
            if self.wrap:
                nb = sum(np.roll(np.roll(a, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                         if dx or dy)
            else:
                p = np.pad(a, 1)
                nb = sum(p[1 + dy:1 + dy + a.shape[0], 1 + dx:1 + dx + a.shape[1]]
                         for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)
            born = np.isin(nb, list(self.born)) & (a == 0)
            surv = np.isin(nb, list(self.survive)) & (a == 1)
            new = (born | surv).astype(np.uint8)
            age = (np.array(self.age) + 1) * new
            self.cells, self.age = new.tolist(), age.tolist()
        else:
            R, C, cells = self.rows, self.cols, self.cells
            new = [[0] * C for _ in range(R)]
            for y in range(R):
                for x in range(C):
                    n = 0
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dx or dy:
                                yy, xx = y + dy, x + dx
                                if self.wrap:
                                    n += cells[yy % R][xx % C]
                                elif 0 <= yy < R and 0 <= xx < C:
                                    n += cells[yy][xx]
                    alive = cells[y][x]
                    new[y][x] = 1 if (n in self.survive if alive else n in self.born) else 0
            self.age = [[(self.age[y][x] + 1) if new[y][x] else 0 for x in range(C)] for y in range(R)]
            self.cells = new
        self.generation += 1

    @property
    def population(self):
        return sum(map(sum, self.cells))


# ---------------------------------------------------------------------------- reaction–diffusion
@tool("Simulation", needs_rng=True)
def reaction_diffusion(cols=200, rows=200, steps=3000, feed=0.055, kill=0.062, da=1.0, db=0.5, spots=8,
                       rng=None):
    """Gray-Scott-Reaktion-Diffusion (Turing-Muster) → 2D-Feld 0–1 (numpy-Array, sonst Liste).

    feed/kill bestimmen das Muster: 0.055/0.062 Korallen, 0.035/0.065 Punkte, 0.022/0.051 Labyrinth,
    0.014/0.054 Wellen. Mit image(feld, …) zeichnen oder mit contour_lines() in Linien verwandeln.
    """
    try:
        import numpy as np
    except ImportError:
        raise ValueError("reaction_diffusion() braucht numpy: pip install numpy") from None
    A = np.ones((rows, cols))
    B = np.zeros((rows, cols))
    for _ in range(int(spots)):
        cy, cx = rng.randrange(rows), rng.randrange(cols)
        r = max(2, min(rows, cols) // 25)
        B[max(0, cy - r):cy + r, max(0, cx - r):cx + r] = 1.0
    for _ in range(int(steps)):
        lapA = (np.roll(A, 1, 0) + np.roll(A, -1, 0) + np.roll(A, 1, 1) + np.roll(A, -1, 1)) * 0.2 + \
               (np.roll(np.roll(A, 1, 0), 1, 1) + np.roll(np.roll(A, 1, 0), -1, 1) +
                np.roll(np.roll(A, -1, 0), 1, 1) + np.roll(np.roll(A, -1, 0), -1, 1)) * 0.05 - A
        lapB = (np.roll(B, 1, 0) + np.roll(B, -1, 0) + np.roll(B, 1, 1) + np.roll(B, -1, 1)) * 0.2 + \
               (np.roll(np.roll(B, 1, 0), 1, 1) + np.roll(np.roll(B, 1, 0), -1, 1) +
                np.roll(np.roll(B, -1, 0), 1, 1) + np.roll(np.roll(B, -1, 0), -1, 1)) * 0.05 - B
        abb = A * B * B
        A += da * lapA - abb + feed * (1 - A)
        B += db * lapB + abb - (kill + feed) * B
        np.clip(A, 0, 1, out=A)
        np.clip(B, 0, 1, out=B)
    return np.clip(A - B, 0, 1)
