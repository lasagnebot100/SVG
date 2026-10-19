"""Maths art: curves, function plots & numerical integration, ODEs & attractors, fractals, domain colouring.

Pure Python; numpy speeds up the pixel-based functions (fractals, domain colouring, density) when installed.
Fields are returned as numpy arrays when numpy is available, otherwise as nested lists – image() takes both.
"""
from __future__ import annotations

import cmath
import colorsys
import math

from ..color import color_ramp, hsb, to_color
from ..tools import tool

CAT = "Mathe-Kunst"


def _np():
    try:
        import numpy as np
        return np
    except ImportError:
        return None


def _cplx(v) -> complex:
    if isinstance(v, (tuple, list)):
        return complex(float(v[0]), float(v[1]))
    return complex(v)


# ---------------------------------------------------------------------------- curves
@tool(CAT)
def lissajous(a=3, b=2, delta=math.pi / 2, cx=0, cy=0, rx=100, ry=None, n=1000):
    """Lissajous-Figur x = sin(a·t + δ), y = sin(b·t) → Punktliste (ganzzahlige a, b ergeben eine geschlossene Kurve)."""
    ry = rx if ry is None else ry
    return [(cx + rx * math.sin(a * t + delta), cy + ry * math.sin(b * t))
            for t in (math.tau * i / n for i in range(n + 1))]


@tool(CAT)
def rose(n=5, d=1, cx=0, cy=0, r=100, steps=1000):
    """Rosenkurve r = cos(n/d · θ): 5/1 → fünf Blätter, 2/1 → vier, 7/3 → verschlungen."""
    period = 2 * math.pi * d
    if float(n).is_integer() and float(d).is_integer():
        g = math.gcd(int(n), int(d)) or 1
        n2, d2 = int(n) // g, int(d) // g
        period = math.pi * d2 if (n2 * d2) % 2 else 2 * math.pi * d2
    k = n / d
    return [(cx + r * math.cos(k * th) * math.cos(th), cy + r * math.cos(k * th) * math.sin(th))
            for th in (period * i / steps for i in range(steps + 1))]


@tool(CAT, needs_rng=True)
def harmonograph(cx=0, cy=0, size=100, pendulums=None, duration=100, steps=8000, rng=None):
    """Harmonograph: gedämpfte Pendel zeichnen verschlungene Spiralen → Punktliste.

    pendulums: Liste von (Achse "x"/"y", Amplitude, Frequenz, Phase, Dämpfung). Ohne Angabe wird zufällig
    gewählt: Frequenzen nahe kleiner ganzer Zahlen, leicht verstimmt – das ergibt die typischen Muster.
    """
    if pendulums is None:
        pendulums = [(axis, rng.uniform(0.4, 1.0), rng.choice((1, 2, 2, 3, 3)) + rng.uniform(-0.012, 0.012),
                      rng.uniform(0, math.tau), rng.uniform(0.004, 0.02)) for axis in ("x", "x", "y", "y")]
    total = {ax: sum(p[1] for p in pendulums if p[0] == ax) or 1.0 for ax in ("x", "y")}
    pts = []
    for i in range(steps + 1):
        t = duration * i / steps
        v = {"x": 0.0, "y": 0.0}
        for axis, amp, freq, phase, damp in pendulums:
            v[axis] += amp * math.sin(freq * t + phase) * math.exp(-damp * t)
        pts.append((cx + size * v["x"] / total["x"], cy + size * v["y"] / total["y"]))
    return pts


@tool(CAT)
def spirograph(R=100, r=37, d=60, cx=0, cy=0, kind="hypo", steps_per_turn=120):
    """Spirograph: Rad (Radius r) rollt im Ring R (kind="hypo") oder außen herum ("epi"); d = Abstand des Stifts."""
    if kind not in ("hypo", "innen", "epi", "aussen", "außen"):
        raise ValueError('spirograph(): kind ist "hypo" (innen) oder "epi" (außen)')
    turns = 20
    if float(R).is_integer() and float(r).is_integer() and r:
        turns = int(r) // math.gcd(int(R), int(r))
    turns = max(1, min(turns, 200))
    n = turns * int(steps_per_turn)
    outer = kind in ("epi", "aussen", "außen")
    pts = []
    for i in range(n + 1):
        t = math.tau * turns * i / n
        if outer:
            x = (R + r) * math.cos(t) - d * math.cos((R + r) / r * t)
            y = (R + r) * math.sin(t) - d * math.sin((R + r) / r * t)
        else:
            x = (R - r) * math.cos(t) + d * math.cos((R - r) / r * t)
            y = (R - r) * math.sin(t) - d * math.sin((R - r) / r * t)
        pts.append((cx + x, cy + y))
    return pts


@tool(CAT)
def superformula(m=6, n1=1, n2=1, n3=1, a=1, b=1, cx=0, cy=0, r=100, steps=720):
    """Superformel nach Gielis: vom Kreis über Sterne bis zu Blüten (m = Symmetrie, n1–n3 = Form) → Polygon."""
    raw = []
    for i in range(steps):
        phi = math.tau * i / steps
        s = abs(math.cos(m * phi / 4) / a) ** n2 + abs(math.sin(m * phi / 4) / b) ** n3
        try:
            rad = s ** (-1.0 / n1) if s > 0 else math.inf
        except OverflowError:
            rad = math.inf
        raw.append((rad, phi))
    finite = [v for v, _ in raw if math.isfinite(v)]
    top = max(finite) if finite else 1.0
    return [(cx + r * min(v, top) / top * math.cos(phi), cy + r * min(v, top) / top * math.sin(phi)) for v, phi in raw]


def _resample_closed(points, n):
    pts = [(float(p[0]), float(p[1])) for p in points]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    if len(pts) < 2:
        raise ValueError("Es braucht mindestens zwei Punkte")
    ring = pts + [pts[0]]
    seg = [math.dist(ring[i], ring[i + 1]) for i in range(len(pts))]
    total = sum(seg)
    if total == 0:
        return [pts[0]] * n
    out, i, acc = [], 0, 0.0
    for k in range(n):
        target = total * k / n
        while acc + seg[i] < target and i < len(seg) - 1:
            acc += seg[i]
            i += 1
        f = (target - acc) / seg[i] if seg[i] else 0.0
        (x0, y0), (x1, y1) = ring[i], ring[i + 1]
        out.append((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f))
    return out


@tool(CAT)
class Epicycles:
    """Fourier-Epizykel: zerlegt eine geschlossene Zeichnung in rotierende Kreise.

    e = Epicycles(punkte, terms=60) · e.circles(t) → [(x, y, r), …] für t = 0 … 1 · e.point(t) · e.path(t)
    (Spur von 0 bis t) · weniger terms = weichere Näherung (Fourier-Reihe).
    """

    def __init__(self, points, terms=None, samples=256):
        z = [complex(x, y) for x, y in _resample_closed(points, int(samples))]
        n = len(z)
        coeffs = []
        for k in range(-(n // 2), n - n // 2):
            w = cmath.exp(-2j * math.pi * k / n)
            acc, wk = 0j, 1 + 0j
            for v in z:
                acc += v * wk
                wk *= w
            coeffs.append((k, acc / n))
        center = next(c for k, c in coeffs if k == 0)
        rest = sorted(((k, c) for k, c in coeffs if k != 0), key=lambda kc: -abs(kc[1]))
        self.center = center
        self.terms = rest[:terms] if terms else rest

    def __len__(self):
        return len(self.terms)

    def circles(self, t):
        """Kreise (Mittelpunkt x, y und Radius) zum Zeitpunkt t (0 … 1)."""
        out, p = [], self.center
        for k, c in self.terms:
            out.append((p.real, p.imag, abs(c)))
            p += c * cmath.exp(2j * math.pi * k * t)
        return out

    def point(self, t):
        """Spitze der Kreiskette zum Zeitpunkt t (0 … 1)."""
        p = self.center
        for k, c in self.terms:
            p += c * cmath.exp(2j * math.pi * k * t)
        return (p.real, p.imag)

    def path(self, t=1.0, steps=400):
        """Gezeichnete Spur von 0 bis t (steps Punkte für einen ganzen Umlauf)."""
        n = max(1, int(steps * t))
        return [self.point(t * i / n) for i in range(n + 1)]


@tool(CAT)
def fourier_approx(points, terms=8, steps=400):
    """Fourier-Reihe einer geschlossenen Form: nur die terms stärksten Schwingungen → weiche Näherung."""
    return Epicycles(points, terms).path(1.0, steps)


# ---------------------------------------------------------------------------- coordinate system & formulas
def _nice_step(span, target=8):
    raw = abs(span) / target or 1.0
    mag = 10 ** math.floor(math.log10(raw))
    return next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)


@tool(CAT)
class Graph:
    """Koordinatensystem: Mathe-Koordinaten (y nach oben) ↔ Leinwand.

    g = Graph(-1, 7, -2, 2, 50, 50, 700, 400)   # x-Bereich, y-Bereich, Rechteck auf der Leinwand
    g.curve(sin) · g.area(sin, 0, pi) · g.axes() · g.grid() · g.labels() · g.pt(x, y) · g.pts(liste)
    """

    def __init__(self, x0=-1, x1=1, y0=-1, y1=1, left=0, top=0, w=400, h=300):
        if x1 == x0 or y1 == y0:
            raise ValueError("Graph(): der x- und der y-Bereich dürfen nicht leer sein")
        self.x0, self.x1, self.y0, self.y1 = float(x0), float(x1), float(y0), float(y1)
        self.left, self.top, self.w, self.h = float(left), float(top), float(w), float(h)

    def px(self, x):
        """x in Mathe-Koordinaten → Leinwand."""
        return self.left + (x - self.x0) / (self.x1 - self.x0) * self.w

    def py(self, y):
        """y in Mathe-Koordinaten → Leinwand (y zeigt nach oben)."""
        return self.top + (self.y1 - y) / (self.y1 - self.y0) * self.h

    def pt(self, x, y):
        return (self.px(x), self.py(y))

    def pts(self, points):
        """Punktliste (oder Polygon) in Leinwand-Koordinaten."""
        return [self.pt(p[0], p[1]) for p in points]

    def curve(self, f, a=None, b=None, steps=400):
        """Funktionsgraph als Liste von Linienstücken (Polstellen und Lücken werden ausgelassen)."""
        a = self.x0 if a is None else a
        b = self.x1 if b is None else b
        span = self.y1 - self.y0
        lo, hi = min(self.y0, self.y1) - 2 * abs(span), max(self.y0, self.y1) + 2 * abs(span)
        pieces, cur = [], []
        for i in range(steps + 1):
            x = a + (b - a) * i / steps
            y = _safe_call(f, x)
            if y is None or not lo <= y <= hi:
                if len(cur) > 1:
                    pieces.append(cur)
                cur = []
                continue
            cur.append(self.pt(x, y))
        if len(cur) > 1:
            pieces.append(cur)
        return pieces

    def area(self, f, a, b, steps=200):
        """Fläche zwischen Graph und x-Achse von a bis b als Polygon (Leinwand-Koordinaten)."""
        pts = [(a, 0.0)]
        for i in range(steps + 1):
            x = a + (b - a) * i / steps
            y = _safe_call(f, x)
            pts.append((x, y if y is not None else 0.0))
        pts.append((b, 0.0))
        return self.pts(pts)

    def _steps(self, ticks):
        if ticks is None:
            return _nice_step(self.x1 - self.x0), _nice_step(self.y1 - self.y0)
        return (ticks, ticks) if not isinstance(ticks, (tuple, list)) else tuple(ticks)

    @staticmethod
    def _range(lo, hi, step):
        lo, hi = min(lo, hi), max(lo, hi)
        k, out = math.ceil(lo / step - 1e-9), []
        while k * step <= hi + 1e-9 and len(out) < 1000:
            out.append(round(k * step, 10))
            k += 1
        return out

    def _origin(self):
        ax = 0.0 if min(self.y0, self.y1) <= 0 <= max(self.y0, self.y1) else min(self.y0, self.y1)
        ay = 0.0 if min(self.x0, self.x1) <= 0 <= max(self.x0, self.x1) else min(self.x0, self.x1)
        return ax, ay

    def axes(self, ticks=None, tick_size=5):
        """Achsen mit Teilstrichen als Linienliste (ticks: Abstand oder (dx, dy); ohne Angabe automatisch)."""
        dx, dy = self._steps(ticks)
        ax, ay = self._origin()
        lines = [[self.pt(self.x0, ax), self.pt(self.x1, ax)], [self.pt(ay, self.y0), self.pt(ay, self.y1)]]
        for x in self._range(self.x0, self.x1, dx):
            if x != ay:
                lines.append([(self.px(x), self.py(ax) - tick_size), (self.px(x), self.py(ax) + tick_size)])
        for y in self._range(self.y0, self.y1, dy):
            if y != ax:
                lines.append([(self.px(ay) - tick_size, self.py(y)), (self.px(ay) + tick_size, self.py(y))])
        return lines

    def grid(self, dx=None, dy=None):
        """Gitterlinien als Linienliste."""
        sx, sy = self._steps(None)
        dx, dy = dx or sx, dy or dx or sy
        lines = [[self.pt(x, self.y0), self.pt(x, self.y1)] for x in self._range(self.x0, self.x1, dx)]
        lines += [[self.pt(self.x0, y), self.pt(self.x1, y)] for y in self._range(self.y0, self.y1, dy)]
        return lines

    def labels(self, ticks=None, offset=14):
        """Beschriftung der Teilstriche: Liste von (x, y, Text) für text()."""
        dx, dy = self._steps(ticks)
        ax, ay = self._origin()
        out = [(self.px(x), self.py(ax) + offset, f"{x:g}") for x in self._range(self.x0, self.x1, dx) if x != ay]
        out += [(self.px(ay) - offset, self.py(y), f"{y:g}") for y in self._range(self.y0, self.y1, dy) if y != ax]
        return out


def _safe_call(f, x):
    try:
        y = f(x)
    except (ValueError, ZeroDivisionError, OverflowError, TypeError):
        return None
    if isinstance(y, complex):
        if abs(y.imag) > 1e-12:
            return None
        y = y.real
    try:
        y = float(y)
    except (TypeError, ValueError):
        return None
    return y if math.isfinite(y) else None


_MATH_NAMES = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
_CMATH_NAMES = {k: getattr(cmath, k) for k in dir(cmath) if not k.startswith("_")}
_COMMON = {"abs": abs, "min": min, "max": max, "round": round, "ln": math.log}


@tool(CAT)
def formula(text, var="x"):
    """Formel als Text → Funktion: f = formula("sin(3*x) * exp(-x/4)"); ^ = Potenz. Mit var="z" komplex (cmath, i = √-1)."""
    src = str(text).replace("^", "**").strip()
    names = dict(_COMMON)
    names.update(_CMATH_NAMES if var == "z" else _MATH_NAMES)
    if var == "z":
        names.update({"i": 1j, "ln": cmath.log, "conj": lambda z: z.conjugate(), "re": lambda z: z.real,
                      "im": lambda z: z.imag, "arg": cmath.phase})
    try:
        code = compile(src, "<formel>", "eval")
    except SyntaxError as exc:
        raise ValueError(f"Formel {text!r} ist ungültig: {exc.msg}") from None
    unknown = [n for n in code.co_names if n not in names and n != var]
    if unknown:
        raise ValueError(f"Unbekannter Name in der Formel {text!r}: {', '.join(unknown)}")
    fn = eval(f"lambda {var}: ({src})", {"__builtins__": {}, **names})
    fn.__doc__ = src
    return fn


# ---------------------------------------------------------------------------- numerical integration
_RULES = {"links": "left", "left": "left", "rechts": "right", "right": "right", "mitte": "mid", "mid": "mid",
          "midpoint": "mid", "trapez": "trap", "trapezoid": "trap", "simpson": "simpson"}


def _rule(rule):
    key = _RULES.get(str(rule).lower())
    if key is None:
        raise ValueError('Regel unbekannt – möglich: "links", "rechts", "mitte", "trapez", "simpson"')
    return key


@tool(CAT)
def integrate(f, a, b, n=1000, rule="simpson"):
    """Bestimmtes Integral von a bis b numerisch (Regeln: links, rechts, mitte, trapez, simpson)."""
    return riemann(f, a, b, n, rule, samples=0).value


class RiemannSum:
    """Ergebnis von riemann(): value, exact, error, shapes, error_shapes, n, rule."""

    def __init__(self, value, exact, shapes, error_shapes, n, rule):
        self.value, self.exact, self.shapes, self.error_shapes = value, exact, shapes, error_shapes
        self.n, self.rule = n, rule
        self.error = None if exact is None else value - exact

    def __repr__(self):
        return f"RiemannSum(rule={self.rule!r}, n={self.n}, value={self.value:.6g}, error={self.error})"


@tool(CAT)
def riemann(f, a, b, n=10, rule="mitte", samples=16):
    """Numerische Integration als Bild: Rechtecke (links/mitte/rechts), Trapeze oder Simpson-Parabeln.

    r = riemann(sin, 0, pi, 8, "trapez") → r.value (Näherung), r.exact (Vergleichswert), r.error,
    r.shapes (Flächen in Mathe-Koordinaten, mit Graph.pts() zeichnen), r.error_shapes (Abweichung).
    Simpson braucht eine gerade Anzahl Streifen; n wird bei Bedarf aufgerundet.
    """
    kind = _rule(rule)
    n = max(1, int(n))
    if kind == "simpson" and n % 2:
        n += 1
    h = (b - a) / n

    def fx(x):
        y = _safe_call(f, x)
        if y is None:
            raise ValueError(f"riemann(): die Funktion ist bei x = {x:g} nicht definiert")
        return y

    xs = [a + h * i for i in range(n + 1)]
    shapes, approx = [], []                         # approx: (x_start, x_end, Näherungsfunktion)
    if kind == "simpson":
        value = 0.0
        for i in range(0, n, 2):
            x0, x1, x2 = xs[i], xs[i + 1], xs[i + 2]
            y0, y1, y2 = fx(x0), fx(x1), fx(x2)
            value += h / 3 * (y0 + 4 * y1 + y2)

            def par(x, x0=x0, x1=x1, x2=x2, y0=y0, y1=y1, y2=y2):
                return (y0 * (x - x1) * (x - x2) / ((x0 - x1) * (x0 - x2)) + y1 * (x - x0) * (x - x2) /
                        ((x1 - x0) * (x1 - x2)) + y2 * (x - x0) * (x - x1) / ((x2 - x0) * (x2 - x1)))
            approx.append((x0, x2, par))
    else:
        value = 0.0
        for i in range(n):
            x0, x1 = xs[i], xs[i + 1]
            if kind == "trap":
                y0, y1 = fx(x0), fx(x1)
                value += h * (y0 + y1) / 2
                approx.append((x0, x1, lambda x, x0=x0, y0=y0, s=(y1 - y0) / h: y0 + s * (x - x0)))
            else:
                y = fx({"left": x0, "right": x1, "mid": (x0 + x1) / 2}[kind])
                value += h * y
                approx.append((x0, x1, lambda x, y=y: y))
    error_shapes = []
    if samples:
        k = max(2, int(samples))
        for x0, x1, g in approx:
            top = [(x0 + (x1 - x0) * j / k, g(x0 + (x1 - x0) * j / k)) for j in range(k + 1)]
            if kind in ("left", "right", "mid", "trap"):
                top = [top[0], top[-1]]
            shapes.append([(x0, 0.0)] + top + [(x1, 0.0)])
            curve = [(x0 + (x1 - x0) * j / k, fx(x0 + (x1 - x0) * j / k)) for j in range(k + 1)]
            error_shapes.append(curve + top[::-1])
    exact = None
    if samples:
        ref_n = 2000
        hr = (b - a) / ref_n
        exact = hr / 3 * sum((1 if j in (0, ref_n) else 4 if j % 2 else 2) * fx(a + hr * j) for j in range(ref_n + 1))
    return RiemannSum(value, exact, shapes, error_shapes, n, kind)


# ---------------------------------------------------------------------------- differential equations
def _vec(y):
    return (float(y),) if isinstance(y, (int, float)) else tuple(float(v) for v in y)


def _rk4_step(f, t, y, dt, scalar):
    def call(tt, yy):
        r = f(tt, yy[0] if scalar else yy)
        return _vec(r)
    k1 = call(t, y)
    k2 = call(t + dt / 2, tuple(a + dt / 2 * b for a, b in zip(y, k1)))
    k3 = call(t + dt / 2, tuple(a + dt / 2 * b for a, b in zip(y, k2)))
    k4 = call(t + dt, tuple(a + dt * b for a, b in zip(y, k3)))
    return tuple(a + dt / 6 * (p + 2 * q + 2 * r + s) for a, p, q, r, s in zip(y, k1, k2, k3, k4))


@tool(CAT)
def rk4(f, y0, t0=0.0, t1=10.0, dt=0.01):
    """Runge-Kutta 4. Ordnung: löst y' = f(t, y). y darf eine Zahl oder ein Tupel sein → [(t, y), …]."""
    scalar = isinstance(y0, (int, float))
    if dt == 0:
        raise ValueError("rk4(): dt darf nicht 0 sein")
    y, t = _vec(y0), float(t0)
    steps = max(1, int(round(abs(t1 - t0) / abs(dt))))
    dt = (t1 - t0) / steps
    out = [(t, y[0] if scalar else y)]
    for i in range(steps):
        y = _rk4_step(f, t, y, dt, scalar)
        t = t0 + dt * (i + 1)
        if not all(math.isfinite(v) for v in y):
            break
        out.append((t, y[0] if scalar else y))
    return out


@tool(CAT)
def phase_portrait(f, x0=-3, x1=3, y0=-3, y1=3, n=12, steps=300, dt=0.02, both=True):
    """Phasenporträt eines 2D-Systems (x', y') = f(x, y): Bahnen ab einem n × n-Raster von Startpunkten.

    → Liste von Bahnen in Mathe-Koordinaten (mit Graph.pts() auf die Leinwand). both=True rechnet auch
    rückwärts in der Zeit. Eine Bahn endet am Rand des Bereichs oder in einem Ruhepunkt.
    """
    mx, my = (x1 - x0) * 0.05, (y1 - y0) * 0.05

    def g(_t, p):
        return f(p[0], p[1])

    def trace(start, direction):
        p, path = (float(start[0]), float(start[1])), [start]
        for _ in range(int(steps)):
            q = _rk4_step(g, 0.0, p, dt * direction, False)
            if not (x0 - mx <= q[0] <= x1 + mx and y0 - my <= q[1] <= y1 + my) or math.dist(p, q) < 1e-9:
                break
            path.append(q)
            p = q
        return path

    out = []
    for i in range(int(n)):
        for j in range(int(n)):
            s = (x0 + (x1 - x0) * (i + 0.5) / n, y0 + (y1 - y0) * (j + 0.5) / n)
            fwd = trace(s, 1)
            if both:
                back = trace(s, -1)
                fwd = back[::-1] + fwd[1:]
            if len(fwd) > 1:
                out.append(fwd)
    return out


# name → (kind, default parameters, start point, dt for continuous systems)
ATTRACTORS = {
    "lorenz": ("ode", {"sigma": 10.0, "rho": 28.0, "beta": 8 / 3}, (0.1, 0.0, 0.0), 0.005),
    "rossler": ("ode", {"a": 0.2, "b": 0.2, "c": 5.7}, (0.1, 0.0, 0.0), 0.01),
    "aizawa": ("ode", {"a": 0.95, "b": 0.7, "c": 0.6, "d": 3.5, "e": 0.25, "f": 0.1}, (0.1, 0.0, 0.0), 0.01),
    "thomas": ("ode", {"b": 0.208186}, (0.1, 0.0, 0.0), 0.05),
    "halvorsen": ("ode", {"a": 1.89}, (-1.48, -1.51, 2.04), 0.005),
    "clifford": ("map", {"a": -1.4, "b": 1.6, "c": 1.0, "d": 0.7}, (0.1, 0.1), None),
    "de_jong": ("map", {"a": 1.4, "b": -2.3, "c": 2.4, "d": -2.1}, (0.1, 0.1), None),
    "svensson": ("map", {"a": 1.5, "b": -1.8, "c": 1.6, "d": 0.9}, (0.1, 0.1), None),
    "henon": ("map", {"a": 1.4, "b": 0.3}, (0.1, 0.1), None),
    "ikeda": ("map", {"u": 0.918}, (0.1, 0.1), None),
    "tinkerbell": ("map", {"a": 0.9, "b": -0.6013, "c": 2.0, "d": 0.5}, (-0.72, -0.64), None),
}


def _attractor_step(name, p):
    """Right-hand side (ode) or next point (map) for the named attractor with parameters p."""
    s, sin, cos = math.sqrt, math.sin, math.cos
    if name == "lorenz":
        return lambda _t, v: (p["sigma"] * (v[1] - v[0]), v[0] * (p["rho"] - v[2]) - v[1], v[0] * v[1] - p["beta"] * v[2])
    if name == "rossler":
        return lambda _t, v: (-v[1] - v[2], v[0] + p["a"] * v[1], p["b"] + v[2] * (v[0] - p["c"]))
    if name == "aizawa":
        return lambda _t, v: ((v[2] - p["b"]) * v[0] - p["d"] * v[1], p["d"] * v[0] + (v[2] - p["b"]) * v[1],
                              p["c"] + p["a"] * v[2] - v[2] ** 3 / 3 - (v[0] ** 2 + v[1] ** 2) * (1 + p["e"] * v[2])
                              + p["f"] * v[2] * v[0] ** 3)
    if name == "thomas":
        return lambda _t, v: (sin(v[1]) - p["b"] * v[0], sin(v[2]) - p["b"] * v[1], sin(v[0]) - p["b"] * v[2])
    if name == "halvorsen":
        a = p["a"]
        return lambda _t, v: (-a * v[0] - 4 * v[1] - 4 * v[2] - v[1] ** 2, -a * v[1] - 4 * v[2] - 4 * v[0] - v[2] ** 2,
                              -a * v[2] - 4 * v[0] - 4 * v[1] - v[0] ** 2)
    if name == "clifford":
        return lambda x, y: (sin(p["a"] * y) + p["c"] * cos(p["a"] * x), sin(p["b"] * x) + p["d"] * cos(p["b"] * y))
    if name == "de_jong":
        return lambda x, y: (sin(p["a"] * y) - cos(p["b"] * x), sin(p["c"] * x) - cos(p["d"] * y))
    if name == "svensson":
        return lambda x, y: (p["d"] * sin(p["a"] * x) - sin(p["b"] * y), p["c"] * cos(p["a"] * x) + cos(p["b"] * y))
    if name == "henon":
        return lambda x, y: (1 - p["a"] * x * x + y, p["b"] * x)
    if name == "ikeda":
        def ikeda(x, y):
            t = 0.4 - 6 / (1 + x * x + y * y)
            return 1 + p["u"] * (x * cos(t) - y * sin(t)), p["u"] * (x * sin(t) + y * cos(t))
        return ikeda
    if name == "tinkerbell":
        return lambda x, y: (x * x - y * y + p["a"] * x + p["b"] * y, 2 * x * y + p["c"] * x + p["d"] * y)
    raise KeyError(name)


@tool(CAT)
def attractor(name="lorenz", n=20000, dt=None, start=None, skip=None, **params):
    """Seltsamer Attraktor als Punktliste.

    Kontinuierlich, 3D-Punkte (x, y, z), gelöst mit RK4: lorenz, rossler, aizawa, thomas, halvorsen.
    Iterierte Abbildungen, 2D-Punkte (x, y): clifford, de_jong, svensson, henon, ikeda, tinkerbell.
    Parameter überschreiben: attractor("clifford", a=-1.7, b=1.3). Mit fit_points() auf die Leinwand bringen.
    skip: Einschwing-Schritte, die nicht ausgegeben werden (Standard 1000 bzw. 100 bei Abbildungen).
    """
    if name not in ATTRACTORS:
        raise ValueError(f"Unbekannter Attraktor {name!r}. Möglich: {', '.join(ATTRACTORS)}")
    kind, defaults, p0, ddt = ATTRACTORS[name]
    skip = (1000 if kind == "ode" else 100) if skip is None else skip
    unknown = set(params) - set(defaults)
    if unknown:
        raise ValueError(f"{name} kennt die Parameter {', '.join(defaults)} – nicht {', '.join(sorted(unknown))}")
    step = _attractor_step(name, {**defaults, **params})
    v = tuple(float(c) for c in (start or p0))
    out = []
    for i in range(int(n) + int(skip)):
        if kind == "ode":
            v = _rk4_step(step, 0.0, v, dt or ddt, False)
        else:
            v = step(v[0], v[1])
        if not all(math.isfinite(c) and abs(c) < 1e12 for c in v):
            break
        if i >= skip:
            out.append(v)
    return out


@tool(CAT)
def fit_points(points, x=0, y=0, w=400, h=400, margin=0, keep_aspect=True, flip_y=False):
    """Skaliert Punkte ins Rechteck (x, y, w, h); weitere Werte je Punkt (z. B. z) bleiben erhalten.

    flip_y=True für Mathe-Koordinaten (y nach oben), z. B. bei ifs().
    """
    if not points:
        return []
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
    iw, ih = w - 2 * margin, h - 2 * margin
    sx = iw / (bx1 - bx0) if bx1 > bx0 else 1.0
    sy = ih / (by1 - by0) if by1 > by0 else 1.0
    if keep_aspect:
        sx = sy = min(sx, sy)
    ox = x + margin + (iw - (bx1 - bx0) * sx) / 2
    oy = y + margin + (ih - (by1 - by0) * sy) / 2
    if flip_y:
        return [(ox + (p[0] - bx0) * sx, oy + (by1 - p[1]) * sy, *p[2:]) for p in points]
    return [(ox + (p[0] - bx0) * sx, oy + (p[1] - by0) * sy, *p[2:]) for p in points]


@tool(CAT)
def density(points, w, h, gamma=0.5):
    """Dichte-Feld (h × w, Werte 0 … 1, logarithmisch) aus Punkten in Pixel-Koordinaten – für image()."""
    w, h = int(w), int(h)
    np = _np()
    if np is not None:
        a = np.asarray([(p[0], p[1]) for p in points], dtype=float).reshape(-1, 2)
        ix, iy = a[:, 0].astype(int), a[:, 1].astype(int)
        ok = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
        cnt = np.zeros((h, w))
        np.add.at(cnt, (iy[ok], ix[ok]), 1)
        top = cnt.max()
        return (np.log1p(cnt) / math.log1p(top)) ** gamma if top > 0 else cnt
    cnt = [[0] * w for _ in range(h)]
    for p in points:
        ix, iy = int(p[0]), int(p[1])
        if 0 <= ix < w and 0 <= iy < h:
            cnt[iy][ix] += 1
    top = max(map(max, cnt))
    if top == 0:
        return [[0.0] * w for _ in range(h)]
    lt = math.log1p(top)
    return [[(math.log1p(c) / lt) ** gamma for c in row] for row in cnt]


# ---------------------------------------------------------------------------- fractals
def _plane(w, h, center, zoom, span=3.0):
    """Pixel-centre coordinates: x list and y list (y up) of a view span/zoom wide on the short side."""
    c = _cplx(center)
    s = span / max(float(zoom), 1e-12) / min(w, h)
    xs = [c.real + (i - w / 2 + 0.5) * s for i in range(w)]
    ys = [c.imag - (j - h / 2 + 0.5) * s for j in range(h)]
    return xs, ys


def _escape_np(np, z, c, max_iter, power):
    out = np.ones(z.shape)
    alive = np.ones(z.shape, bool)
    c_is_field = np.ndim(c) > 0
    lp = math.log(power)
    with np.errstate(all="ignore"):
        for i in range(int(max_iter)):
            idx = np.nonzero(alive)
            zz = z[idx]
            zz = zz * zz + (c[idx] if c_is_field else c) if power == 2 else zz ** power + (c[idx] if c_is_field else c)
            z[idx] = zz
            esc = np.abs(zz) > 256.0
            if esc.any():
                ei = tuple(a[esc] for a in idx)
                mu = i + 1 - np.log(np.log(np.abs(zz[esc]))) / lp
                out[ei] = np.clip(mu / max_iter, 0.0, 0.9999)
                alive[ei] = False
            if not alive.any():
                break
    return out


def _escape(z, c, max_iter, power, lp):
    for i in range(max_iter):
        z = z * z + c if power == 2 else z ** power + c
        if z.real * z.real + z.imag * z.imag > 65536.0:
            mu = i + 1 - math.log(math.log(abs(z))) / lp
            return min(max(mu / max_iter, 0.0), 0.9999)
    return 1.0


@tool(CAT)
def mandelbrot(w=400, h=300, center=(-0.6, 0), zoom=1, max_iter=200, power=2):
    """Mandelbrot-Menge als Feld (h × w): Werte 0 … 1 = wie schnell der Punkt entkommt, 1 = in der Menge.

    Mit colorize(feld, farben) einfärben und mit image() zeichnen. center und zoom wählen den Ausschnitt.
    """
    w, h, max_iter = int(w), int(h), int(max_iter)
    xs, ys = _plane(w, h, center, zoom)
    np = _np()
    if np is not None:
        c = np.asarray(xs)[None, :] + 1j * np.asarray(ys)[:, None]
        return _escape_np(np, np.zeros_like(c), c, max_iter, power)
    lp = math.log(power)
    rows = []
    for y in ys:
        row = []
        for x in xs:
            if power == 2:                                  # skip the main cardioid and the period-2 bulb
                q = (x - 0.25) ** 2 + y * y
                if q * (q + x - 0.25) <= 0.25 * y * y or (x + 1) ** 2 + y * y <= 0.0625:
                    row.append(1.0)
                    continue
            row.append(_escape(0j, complex(x, y), max_iter, power, lp))
        rows.append(row)
    return rows


@tool(CAT)
def julia(w=400, h=300, c=(-0.8, 0.156), center=(0, 0), zoom=1, max_iter=200, power=2):
    """Julia-Menge zum Parameter c als Feld (h × w, 0 … 1, 1 = in der Menge). Schöne c: (-0.8, 0.156),
    (0.285, 0.01), (-0.4, 0.6), (-0.70176, -0.3842)."""
    w, h, max_iter = int(w), int(h), int(max_iter)
    xs, ys = _plane(w, h, center, zoom)
    cc = _cplx(c)
    np = _np()
    if np is not None:
        z = np.asarray(xs)[None, :] + 1j * np.asarray(ys)[:, None]
        return _escape_np(np, z, cc, max_iter, power)
    lp = math.log(power)
    return [[_escape(complex(x, y), cc, max_iter, power, lp) for x in xs] for y in ys]


def _rgb_list(colors):
    return [tuple(v / 255 for v in to_color((col,)).rgba[:3]) for col in colors]


@tool(CAT)
def newton_fractal(w=400, h=400, roots=3, colors=None, center=(0, 0), zoom=1, max_iter=40):
    """Newton-Fraktal: Jeder Punkt bekommt die Farbe der Nullstelle, zu der das Newton-Verfahren läuft.

    roots: Anzahl (Nullstellen von zⁿ − 1) oder Liste komplexer Zahlen / (x, y)-Paare. Helligkeit = Tempo.
    → RGB-Feld (h × w × 3) für image().
    """
    w, h, max_iter = int(w), int(h), int(max_iter)
    if isinstance(roots, int):
        rs = [cmath.exp(2j * math.pi * k / roots) for k in range(roots)]
    else:
        rs = [_cplx(r) for r in roots]
    if not rs:
        raise ValueError("newton_fractal(): es braucht mindestens eine Nullstelle")
    cols = _rgb_list(colors) if colors else [tuple(v / 255 for v in hsb(360 * k / len(rs), 70, 95).rgba[:3])
                                             for k in range(len(rs))]
    xs, ys = _plane(w, h, center, zoom)
    np = _np()
    if np is not None:
        z = np.asarray(xs)[None, :] + 1j * np.asarray(ys)[:, None]
        r_arr = np.asarray(rs)
        it = np.full(z.shape, max_iter, float)
        with np.errstate(all="ignore"):
            for i in range(max_iter):
                s = np.zeros_like(z)
                for r in rs:
                    s += 1 / (z - r)
                z = z - 1 / s
                near = np.min(np.abs(z[..., None] - r_arr), axis=-1) < 1e-6
                it = np.where(near & (it == max_iter), i, it)
        which = np.argmin(np.abs(z[..., None] - r_arr), axis=-1)
        which = np.where(np.isfinite(z), which, 0)
        shade = (1 - it / max_iter) ** 0.6
        shade = np.where(np.isfinite(z), shade, 0.0)
        return np.asarray(cols)[which] * (0.25 + 0.75 * shade)[..., None]
    rows = []
    for y in ys:
        row = []
        for x in xs:
            z, it = complex(x, y), max_iter
            try:
                for i in range(max_iter):
                    z -= 1 / sum(1 / (z - r) for r in rs)
                    if min(abs(z - r) for r in rs) < 1e-6:
                        it = i
                        break
            except ZeroDivisionError:
                row.append((0.0, 0.0, 0.0))
                continue
            k = min(range(len(rs)), key=lambda q: abs(z - rs[q]))
            s = 0.25 + 0.75 * (1 - it / max_iter) ** 0.6
            row.append(tuple(v * s for v in cols[k]))
        rows.append(row)
    return rows


@tool(CAT)
def colorize(field, colors, cycles=1, inside=None):
    """Färbt ein Feld (Werte 0 … 1) mit einem Farbverlauf → RGB-Feld für image().

    cycles > 1 wiederholt den Verlauf hin und zurück (feine Bänder bei Fraktalen); inside färbt Werte ≥ 1
    (z. B. die Mandelbrot-Menge selbst).
    """
    lut = [tuple(v / 255 for v in color_ramp(colors, i / 255).rgba[:3]) for i in range(256)]
    ins = tuple(v / 255 for v in to_color((inside,)).rgba[:3]) if inside is not None else None

    def t_of(v):
        if cycles == 1:
            return min(max(v, 0.0), 1.0)
        u = (v * cycles) % 2.0
        return 2.0 - u if u > 1 else u

    np = _np()
    if np is not None and hasattr(field, "shape"):
        a = np.asarray(field, float)
        if cycles == 1:
            t = np.clip(a, 0, 1)
        else:
            u = np.mod(a * cycles, 2.0)
            t = np.where(u > 1, 2.0 - u, u)
        rgb = np.asarray(lut)[(t * 255).astype(int)]
        if ins is not None:
            rgb[a >= 1] = ins
        return rgb
    return [[ins if (ins is not None and v >= 1) else lut[int(t_of(v) * 255)] for v in row] for row in field]


_IFS = {
    "farn": [(0, 0, 0, 0.16, 0, 0, 0.01), (0.85, 0.04, -0.04, 0.85, 0, 1.6, 0.85),
             (0.2, -0.26, 0.23, 0.22, 0, 1.6, 0.07), (-0.15, 0.28, 0.26, 0.24, 0, 0.44, 0.07)],
    "sierpinski": [(0.5, 0, 0, 0.5, 0, 0, 1), (0.5, 0, 0, 0.5, 0.5, 0, 1), (0.5, 0, 0, 0.5, 0.25, 0.433, 1)],
    "drache": [(0.5, -0.5, 0.5, 0.5, 0, 0, 1), (-0.5, -0.5, 0.5, -0.5, 1, 0, 1)],
    "baum": [(0, 0, 0, 0.5, 0, 0, 0.05), (0.42, -0.42, 0.42, 0.42, 0, 0.2, 0.4),
             (0.42, 0.42, -0.42, 0.42, 0, 0.2, 0.4), (0.1, 0, 0, 0.1, 0, 0.2, 0.15)],
    "koch": [(1 / 3, 0, 0, 1 / 3, 0, 0, 1), (1 / 6, -0.288675, 0.288675, 1 / 6, 1 / 3, 0, 1),
             (1 / 6, 0.288675, -0.288675, 1 / 6, 0.5, 0.288675, 1), (1 / 3, 0, 0, 1 / 3, 2 / 3, 0, 1)],
    "kristall": [(0.255, 0, 0, 0.255, 0.3726, 0.6714, 1), (0.255, 0, 0, 0.255, 0.1146, 0.2232, 1),
                 (0.255, 0, 0, 0.255, 0.6306, 0.2232, 1), (0.37, -0.642, 0.642, 0.37, 0.6356, -0.0061, 1)],
}


@tool(CAT, needs_rng=True)
def ifs(name="farn", n=50000, rng=None):
    """Iteriertes Funktionensystem (Chaos-Spiel) → Punkte (x, y, k); k = Nummer der Abbildung (zum Färben).

    Vorlagen: farn, sierpinski, drache, baum, koch, kristall – oder eigene Liste von (a, b, c, d, e, f, p):
    x' = a·x + b·y + e, y' = c·x + d·y + f, p = Gewicht. Mathe-Koordinaten: fit_points(…, flip_y=True).
    """
    maps = _IFS.get(name) if isinstance(name, str) else [tuple(m) for m in name]
    if not maps:
        raise ValueError(f"Unbekannte IFS-Vorlage {name!r}. Möglich: {', '.join(_IFS)}")
    weights = [m[6] if len(m) > 6 else 1.0 for m in maps]
    x = y = 0.0
    out = []
    for i in range(int(n) + 20):
        k = rng.choices(range(len(maps)), weights)[0]
        a, b, c, d, e, f = maps[k][:6]
        x, y = a * x + b * y + e, c * x + d * y + f
        if i >= 20:
            out.append((x, y, k))
    return out


def _variations(rng):
    def r2(x, y):
        return x * x + y * y + 1e-12
    return {
        "linear": lambda x, y: (x, y),
        "sinus": lambda x, y: (math.sin(x), math.sin(y)),
        "kugel": lambda x, y: (x / r2(x, y), y / r2(x, y)),
        "wirbel": lambda x, y: (x * math.sin(r2(x, y)) - y * math.cos(r2(x, y)),
                                x * math.cos(r2(x, y)) + y * math.sin(r2(x, y))),
        "hufeisen": lambda x, y: ((x - y) * (x + y) / math.sqrt(r2(x, y)), 2 * x * y / math.sqrt(r2(x, y))),
        "polar": lambda x, y: (math.atan2(x, y) / math.pi, math.sqrt(r2(x, y)) - 1),
        "herz": lambda x, y: (math.sqrt(r2(x, y)) * math.sin(math.atan2(x, y) * math.sqrt(r2(x, y))),
                              -math.sqrt(r2(x, y)) * math.cos(math.atan2(x, y) * math.sqrt(r2(x, y)))),
        "scheibe": lambda x, y: (math.atan2(x, y) / math.pi * math.sin(math.pi * math.sqrt(r2(x, y))),
                                 math.atan2(x, y) / math.pi * math.cos(math.pi * math.sqrt(r2(x, y)))),
        "spirale": lambda x, y: ((math.cos(math.atan2(x, y)) + math.sin(math.sqrt(r2(x, y)))) / math.sqrt(r2(x, y)),
                                 (math.sin(math.atan2(x, y)) - math.cos(math.sqrt(r2(x, y)))) / math.sqrt(r2(x, y))),
        "hyperbel": lambda x, y: (math.sin(math.atan2(x, y)) / math.sqrt(r2(x, y)),
                                  math.sqrt(r2(x, y)) * math.cos(math.atan2(x, y))),
        "julia": lambda x, y: tuple(math.sqrt(math.sqrt(r2(x, y))) * fn(math.atan2(x, y) / 2 + rng.choice((0, math.pi)))
                                    for fn in (math.cos, math.sin)),
    }


FLAME_VARIATIONS = ["linear", "sinus", "kugel", "wirbel", "hufeisen", "polar", "herz", "scheibe", "spirale",
                    "hyperbel", "julia"]


@tool(CAT, needs_rng=True)
def fractal_flame(w=400, h=400, n=200000, maps=3, variations=None, colors=None, gamma=2.2, rng=None):
    """Fractal Flame (nach Scott Draves): zufällige Abbildungen mit Verzerrungen, Dichte als Licht.

    variations: Liste aus linear, sinus, kugel, wirbel, hufeisen, polar, herz, scheibe, spirale, hyperbel,
    julia (ohne Angabe zufällig zwei bis drei). → RGBA-Feld (h × w × 4) für image(); der Hintergrund bleibt frei.
    """
    w, h = int(w), int(h)
    vfun = _variations(rng)
    names = variations or rng.sample(FLAME_VARIATIONS, rng.randint(2, 3))
    bad = [v for v in names if v not in vfun]
    if bad:
        raise ValueError(f"Unbekannte Variation {bad[0]!r}. Möglich: {', '.join(FLAME_VARIATIONS)}")
    lut = [tuple(v / 255 for v in color_ramp(colors or ["#3a0ca3", "#f72585", "#ffd166", "#ffffff"], i / 255).rgba[:3])
           for i in range(256)]
    fs = []
    for k in range(int(maps)):
        coef = tuple(rng.uniform(-1, 1) for _ in range(6))
        vw = [rng.random() for _ in names]
        tot = sum(vw) or 1.0
        fs.append((coef, [v / tot for v in vw], k / max(1, int(maps) - 1), rng.uniform(0.5, 1.5)))
    weights = [f[3] for f in fs]

    def run(count, emit):
        x, y, c = rng.uniform(-1, 1), rng.uniform(-1, 1), rng.random()
        for i in range(count):
            (a, b, cc, d, e, f), vw, col, _ = fs[rng.choices(range(len(fs)), weights)[0]]
            ax, ay = a * x + b * y + e, cc * x + d * y + f
            nx = ny = 0.0
            for name, wt in zip(names, vw):
                try:
                    vx, vy = vfun[name](ax, ay)
                except (OverflowError, ValueError, ZeroDivisionError):
                    vx, vy = 0.0, 0.0
                nx += wt * vx
                ny += wt * vy
            if not (math.isfinite(nx) and math.isfinite(ny)) or abs(nx) > 1e6 or abs(ny) > 1e6:
                nx, ny = rng.uniform(-1, 1), rng.uniform(-1, 1)
            x, y, c = nx, ny, (c + col) / 2
            if i >= 20:
                emit(x, y, c)

    probe = []
    run(4000, lambda x, y, c: probe.append((x, y)))
    if not probe:
        raise ValueError("fractal_flame(): die Abbildungen laufen auseinander – anderen Seed probieren")
    px = sorted(p[0] for p in probe)
    py = sorted(p[1] for p in probe)
    lo_x, hi_x = px[int(len(px) * 0.02)], px[int(len(px) * 0.98) - 1]
    lo_y, hi_y = py[int(len(py) * 0.02)], py[int(len(py) * 0.98) - 1]
    span = max(hi_x - lo_x, hi_y - lo_y, 1e-9) * 1.15
    mx, my = (lo_x + hi_x) / 2, (lo_y + hi_y) / 2
    scale = min(w, h) / span
    cnt = [0] * (w * h)
    acc = [[0.0, 0.0, 0.0] for _ in range(w * h)]

    def plot(x, y, c):
        ix, iy = int((x - mx) * scale + w / 2), int((my - y) * scale + h / 2)
        if 0 <= ix < w and 0 <= iy < h:
            k = iy * w + ix
            cnt[k] += 1
            r, g, b = lut[int(c * 255)]
            s = acc[k]
            s[0] += r
            s[1] += g
            s[2] += b

    run(int(n), plot)
    top = max(cnt)
    lt = math.log1p(top) if top else 1.0
    inv_g = 1.0 / gamma
    rows = []
    for j in range(h):
        row = []
        for i in range(w):
            k = j * w + i
            m = cnt[k]
            if not m:
                row.append((0.0, 0.0, 0.0, 0.0))
                continue
            alpha = (math.log1p(m) / lt) ** inv_g
            s = acc[k]
            row.append((s[0] / m, s[1] / m, s[2] / m, alpha))
        rows.append(row)
    np = _np()
    return np.asarray(rows) if np is not None else rows


# ---------------------------------------------------------------------------- complex functions
def _hsv_np(np, hh, s, v):
    i = np.floor(hh * 6).astype(int) % 6
    f = hh * 6 - np.floor(hh * 6)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1)


def _dc_pixel(w, style):
    if w is None or not cmath.isfinite(w):
        return (1.0, 1.0, 1.0)
    hue = (cmath.phase(w) / math.tau) % 1.0
    m = abs(w)
    if style == "phase":
        return colorsys.hsv_to_rgb(hue, 0.85, 0.95)
    light = 0.75 + 0.25 * (math.log2(m) % 1.0) if m > 0 else 0.0
    sat = 0.9
    if style == "raster":
        gx, gy = abs(w.real) % 1.0, abs(w.imag) % 1.0
        if min(gx, 1 - gx) < 0.04 or min(gy, 1 - gy) < 0.04:
            light *= 0.55
    elif style != "klassisch":
        raise ValueError('domain_coloring(): style ist "klassisch", "phase" oder "raster"')
    return colorsys.hsv_to_rgb(hue, sat, light * (2 / math.pi * math.atan(m) * 0.6 + 0.4))


@tool(CAT)
def domain_coloring(f, w=400, h=400, x0=-2, x1=2, y0=-2, y1=2, style="klassisch"):
    """Domain Coloring einer komplexen Funktion: Farbton = Winkel, Helligkeit = Betrag → RGB-Feld (h × w × 3).

    f nimmt eine komplexe Zahl, z. B. lambda z: (z**3 - 1) / (z**2 + 1) oder formula("z^3 - 1", "z").
    style: "klassisch" (Höhenringe des Betrags), "phase" (nur Farbe), "raster" (Gitter von Real- und Imaginärteil).
    """
    w, h = int(w), int(h)
    if style not in ("klassisch", "phase", "raster"):
        raise ValueError('domain_coloring(): style ist "klassisch", "phase" oder "raster"')
    xs = [x0 + (x1 - x0) * (i + 0.5) / w for i in range(w)]
    ys = [y1 - (y1 - y0) * (j + 0.5) / h for j in range(h)]
    np = _np()
    if np is not None:
        z = np.asarray(xs)[None, :] + 1j * np.asarray(ys)[:, None]
        with np.errstate(all="ignore"):
            try:
                out = np.asarray(f(z), dtype=complex)
                if out.shape != z.shape:
                    raise TypeError
            except Exception:
                def one(v):
                    try:
                        return complex(f(complex(v)))
                    except (ZeroDivisionError, OverflowError, ValueError):
                        return complex(math.nan, math.nan)
                out = np.vectorize(one, otypes=[complex])(z)
            bad = ~np.isfinite(out)
            out = np.where(bad, 0, out)
            hue = np.mod(np.angle(out) / math.tau, 1.0)
            m = np.abs(out)
            if style == "phase":
                rgb = _hsv_np(np, hue, np.full(m.shape, 0.85), np.full(m.shape, 0.95))
            else:
                light = np.where(m > 0, 0.75 + 0.25 * np.mod(np.log2(np.where(m > 0, m, 1)), 1.0), 0.0)
                if style == "raster":
                    gx, gy = np.mod(np.abs(out.real), 1.0), np.mod(np.abs(out.imag), 1.0)
                    line = (np.minimum(gx, 1 - gx) < 0.04) | (np.minimum(gy, 1 - gy) < 0.04)
                    light = np.where(line, light * 0.55, light)
                val = light * (2 / math.pi * np.arctan(m) * 0.6 + 0.4)
                rgb = _hsv_np(np, hue, np.full(m.shape, 0.9), val)
            rgb[bad] = 1.0
        return rgb

    def safe(v):
        try:
            return complex(f(v))
        except (ZeroDivisionError, OverflowError, ValueError):
            return None
    return [[_dc_pixel(safe(complex(x, y)), style) for x in xs] for y in ys]
