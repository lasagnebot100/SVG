"""Maths helpers and generative-art toolbox available in every sketch (pure Python)."""
from __future__ import annotations

import math

TOOLS: dict[str, tuple] = {}   # name -> (function, category, needs_rng)


def tool(category: str, needs_rng: bool = False):
    def deco(fn):
        TOOLS[fn.__name__] = (fn, category, needs_rng)
        return fn
    return deco


# ---------------------------------------------------------------------------- maths
@tool("Mathe")
def map_range(v, a1, b1, a2, b2, clamp=False):
    """Bildet v von [a1, b1] auf [a2, b2] ab (wie map() in p5)."""
    t = (v - a1) / (b1 - a1) if b1 != a1 else 0.0
    if clamp:
        t = max(0.0, min(1.0, t))
    return a2 + (b2 - a2) * t


@tool("Mathe")
def lerp(a, b, t):
    """Lineare Interpolation zwischen a und b."""
    return a + (b - a) * t


@tool("Mathe")
def constrain(v, lo, hi):
    """Begrenzt v auf [lo, hi]."""
    return lo if v < lo else hi if v > hi else v


@tool("Mathe")
def dist(x1, y1, x2, y2):
    """Abstand zweier Punkte."""
    return math.hypot(x2 - x1, y2 - y1)


@tool("Mathe")
def smoothstep(e0, e1, x):
    """Weicher Übergang 0 → 1 zwischen e0 und e1."""
    t = constrain((x - e0) / (e1 - e0), 0.0, 1.0) if e1 != e0 else 0.0
    return t * t * (3 - 2 * t)


@tool("Mathe")
def ease_in_out(t):
    """Sanftes Beschleunigen und Abbremsen (t = 0 … 1)."""
    return 0.5 - 0.5 * math.cos(math.pi * constrain(t, 0.0, 1.0))


@tool("Animation")
def ping_pong(t):
    """0 → 1 → 0 über t = 0 … 1 (hin und zurück)."""
    t = t % 1.0
    return 1 - abs(2 * t - 1)


@tool("Animation")
def ease_in(t, power=3):
    """Langsam starten (t = 0 … 1)."""
    return constrain(t, 0.0, 1.0) ** power


@tool("Animation")
def ease_out(t, power=3):
    """Langsam auslaufen (t = 0 … 1)."""
    return 1 - (1 - constrain(t, 0.0, 1.0)) ** power


@tool("Animation")
def ease_in_out_cubic(t):
    """Kubisches Ein- und Ausblenden (t = 0 … 1)."""
    t = constrain(t, 0.0, 1.0)
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


@tool("Animation")
def ease_out_elastic(t):
    """Federnd auslaufen (t = 0 … 1)."""
    t = constrain(t, 0.0, 1.0)
    if t in (0.0, 1.0):
        return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1


@tool("Animation")
def wave(t, cycles=1.0, phase=0.0):
    """Weiche Schwingung 0 … 1 … 0 (Kosinus), nahtlos bei ganzen cycles."""
    return 0.5 - 0.5 * math.cos(math.tau * (t * cycles + phase))


@tool("Mathe")
def radians(deg):
    """Grad → Bogenmaß."""
    return math.radians(deg)


@tool("Mathe")
def degrees(rad):
    """Bogenmaß → Grad."""
    return math.degrees(rad)


class Vector:
    """2D-Vektor: Vector(x, y); +, -, * Zahl, .mag(), .normalize(), .heading(), .rotate(a)."""
    __slots__ = ("x", "y")

    def __init__(self, x=0.0, y=0.0):
        self.x, self.y = float(x), float(y)

    @staticmethod
    def from_angle(a, length=1.0):
        return Vector(math.cos(a) * length, math.sin(a) * length)

    def __add__(self, o):
        return Vector(self.x + o[0], self.y + o[1])

    def __sub__(self, o):
        return Vector(self.x - o[0], self.y - o[1])

    def __mul__(self, k):
        return Vector(self.x * k, self.y * k)

    __rmul__ = __mul__

    def __truediv__(self, k):
        return Vector(self.x / k, self.y / k)

    def __neg__(self):
        return Vector(-self.x, -self.y)

    def __getitem__(self, i):
        return (self.x, self.y)[i]

    def __iter__(self):
        yield self.x
        yield self.y

    def __len__(self):
        return 2

    def __repr__(self):
        return f"Vector({self.x:.3f}, {self.y:.3f})"

    def copy(self):
        return Vector(self.x, self.y)

    def mag(self):
        return math.hypot(self.x, self.y)

    def normalize(self):
        m = self.mag()
        return Vector(self.x / m, self.y / m) if m else Vector()

    def limit(self, m):
        return self.normalize() * m if self.mag() > m else self.copy()

    def set_mag(self, m):
        return self.normalize() * m

    def heading(self):
        return math.atan2(self.y, self.x)

    def rotate(self, a):
        c, s = math.cos(a), math.sin(a)
        return Vector(self.x * c - self.y * s, self.x * s + self.y * c)

    def dot(self, o):
        return self.x * o[0] + self.y * o[1]

    def dist(self, o):
        return math.hypot(self.x - o[0], self.y - o[1])

    def lerp(self, o, t):
        return Vector(self.x + (o[0] - self.x) * t, self.y + (o[1] - self.y) * t)


TOOLS["Vector"] = (Vector, "Mathe", False)


# ---------------------------------------------------------------------------- geometry
@tool("Werkzeuge")
def polygon_area(poly):
    """Fläche eines Polygons (positiv)."""
    a = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        a += x0 * y1 - x1 * y0
    return abs(a) / 2


@tool("Werkzeuge")
def centroid(poly):
    """Schwerpunkt eines Polygons."""
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        cr = x0 * y1 - x1 * y0
        a += cr
        cx += (x0 + x1) * cr
        cy += (y0 + y1) * cr
    if abs(a) < 1e-12:
        n = len(poly)
        return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)
    return (cx / (3 * a), cy / (3 * a))


@tool("Werkzeuge")
def point_in_polygon(x, y, poly):
    """True, wenn (x, y) im Polygon liegt."""
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            inside = not inside
    return inside


def _clip_halfplane(poly, nx, ny, c):
    """Keep the part of a convex polygon where nx*x + ny*y <= c."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        dp = nx * p[0] + ny * p[1] - c
        dq = nx * q[0] + ny * q[1] - c
        if dp <= 0:
            out.append(p)
        if (dp < 0 < dq) or (dq < 0 < dp):
            t = dp / (dp - dq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


@tool("Werkzeuge")
def voronoi_cells(points, x0=0, y0=0, x1=None, y1=None):
    """Voronoi-Zellen (Liste von Polygonen, gleiche Reihenfolge wie points) im Rechteck."""
    pts = [tuple(p[:2]) for p in points]
    if x1 is None or y1 is None:
        raise ValueError("voronoi_cells(points, x0, y0, x1, y1): Rechteck angeben, z. B. 0, 0, width, height")
    # grid acceleration: only nearby sites can bound a cell
    n = len(pts)
    cell = math.sqrt((x1 - x0) * (y1 - y0) / max(n, 1)) * 1.5 or 1.0
    grid: dict[tuple[int, int], list[int]] = {}
    for i, (x, y) in enumerate(pts):
        grid.setdefault((int((x - x0) // cell), int((y - y0) // cell)), []).append(i)
    cells = []
    for i, (px, py) in enumerate(pts):
        poly = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        gx, gy = int((px - x0) // cell), int((py - y0) // cell)
        r = 0
        while poly:
            ring = [(gx + dx, gy + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1)
                    if max(abs(dx), abs(dy)) == r]
            for key in ring:
                for j in grid.get(key, ()):
                    if j == i or not poly:
                        continue
                    qx, qy = pts[j]
                    if qx == px and qy == py:
                        continue
                    c = (qx * qx + qy * qy - px * px - py * py) / 2
                    poly = _clip_halfplane(poly, qx - px, qy - py, c)
            if not poly:
                break
            # a site can only cut the cell if it is closer than twice the cell's radius;
            # unvisited sites are at least r * cell away
            reach = 2 * max(math.hypot(qx - px, qy - py) for qx, qy in poly)
            if r * cell >= reach:
                break
            r += 1
        cells.append(poly)
    return cells


@tool("Werkzeuge", needs_rng=True)
def poisson_disc(w, h, r, k=30, x0=0.0, y0=0.0, rng=None):
    """Gleichmäßig-zufällige Punkte mit Mindestabstand r im Rechteck w × h (Bridson)."""
    cs = r / math.sqrt(2)
    gw, gh = int(math.ceil(w / cs)), int(math.ceil(h / cs))
    grid = [[None] * gw for _ in range(gh)]
    pts, active = [], []

    def add(p):
        pts.append(p)
        active.append(p)
        grid[int(p[1] / cs)][int(p[0] / cs)] = p

    add((rng.random() * w, rng.random() * h))
    while active:
        i = rng.randrange(len(active))
        px, py = active[i]
        for _ in range(k):
            a = rng.random() * math.tau
            d = r * (1 + rng.random())
            x, y = px + math.cos(a) * d, py + math.sin(a) * d
            if not (0 <= x < w and 0 <= y < h):
                continue
            gx, gy = int(x / cs), int(y / cs)
            ok = True
            for yy in range(max(0, gy - 2), min(gh, gy + 3)):
                for xx in range(max(0, gx - 2), min(gw, gx + 3)):
                    q = grid[yy][xx]
                    if q and (q[0] - x) ** 2 + (q[1] - y) ** 2 < r * r:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                add((x, y))
                break
        else:
            active.pop(i)
    return [(x + x0, y + y0) for x, y in pts]


@tool("Werkzeuge")
def relax(points, x0, y0, x1, y1, iterations=2):
    """Lloyd-Relaxation: verschiebt Punkte in die Mitte ihrer Voronoi-Zelle (gleichmäßiger)."""
    pts = [tuple(p[:2]) for p in points]
    for _ in range(iterations):
        pts = [centroid(c) if len(c) >= 3 else p for p, c in zip(pts, voronoi_cells(pts, x0, y0, x1, y1))]
    return pts


@tool("Werkzeuge")
def chaikin(points, iterations=2, closed=False):
    """Glättet eine Punktliste (Chaikin-Ecken-Abschneiden)."""
    pts = [tuple(p[:2]) for p in points]
    for _ in range(iterations):
        out = [] if closed else [pts[0]]
        pairs = zip(pts, pts[1:] + pts[:1]) if closed else zip(pts, pts[1:])
        for (ax, ay), (bx, by) in pairs:
            out.append((0.75 * ax + 0.25 * bx, 0.75 * ay + 0.25 * by))
            out.append((0.25 * ax + 0.75 * bx, 0.25 * ay + 0.75 * by))
        if not closed:
            out.append(pts[-1])
        pts = out
    return pts


@tool("Werkzeuge")
def resample(points, spacing):
    """Verteilt Punkte gleichmäßig im Abstand spacing entlang einer Linie."""
    pts = [tuple(p[:2]) for p in points]
    if len(pts) < 2:
        return pts
    out = [pts[0]]
    carry = 0.0
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        seg = math.hypot(bx - ax, by - ay)
        d = spacing - carry
        while d <= seg:
            t = d / seg
            out.append((ax + (bx - ax) * t, ay + (by - ay) * t))
            d += spacing
        carry = seg - (d - spacing)
    if out[-1] != pts[-1]:
        out.append(pts[-1])
    return out


@tool("Werkzeuge")
def hatch_polygon(poly, spacing, angle=0.0):
    """Schraffur-Linien ((x1, y1), (x2, y2)) innerhalb eines Polygons."""
    ca, sa = math.cos(-angle), math.sin(-angle)
    rot = [(x * ca - y * sa, x * sa + y * ca) for x, y in poly]
    ys = [p[1] for p in rot]
    lines = []
    y = min(ys) + spacing / 2
    n = len(rot)
    while y < max(ys):
        xs = []
        for i in range(n):
            (x0, y0), (x1, y1) = rot[i], rot[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for xa, xb in zip(xs[::2], xs[1::2]):
            # rotate back
            a = (xa * ca + y * sa, -xa * sa + y * ca)
            b = (xb * ca + y * sa, -xb * sa + y * ca)
            lines.append((a, b))
        y += spacing
    return lines


@tool("Werkzeuge")
def grid(cols, rows, x0=0.0, y0=0.0, w=1.0, h=1.0):
    """Liste von Rasterzellen (x, y, b, h, spalte, zeile)."""
    cw, ch = w / cols, h / rows
    return [(x0 + c * cw, y0 + r * ch, cw, ch, c, r) for r in range(rows) for c in range(cols)]
