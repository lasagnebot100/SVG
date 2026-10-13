"""The Sketch: a p5.js/Processing-like drawing API that records a display list.

Every public method marked with @api(...) becomes a global function inside sketch
files (e.g. `circle(100, 100, 50)`), and shows up in the editor's API reference.
"""
from __future__ import annotations

import math
import random as _random
from dataclasses import dataclass, replace

from ..core import PAPER_SIZES
from ..noise import Perlin
from ..params import Param
from .color import PALETTES, Color, Gradient, color_ramp, hsb, lerp_color, to_color
from .png import to_png

IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

CATEGORIES = ["Leinwand", "Farbe & Stil", "Formen", "Eigene Formen", "Transformation",
              "Text & Bild", "Animation", "Zufall & Noise", "Mathe", "Parameter", "Werkzeuge"]


def api(category: str):
    def deco(fn):
        fn._api_category = category
        return fn
    return deco


def mat_mul(m, n):
    a1, b1, c1, d1, e1, f1 = m
    a2, b2, c2, d2, e2, f2 = n
    return (a1 * a2 + c1 * b2, b1 * a2 + d1 * b2,
            a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


def mat_apply(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


@dataclass(frozen=True)
class Style:
    fill: object = Color(255, 255, 255)      # Color | Gradient | None
    stroke: object = Color(0, 0, 0)
    weight: float = 1.0
    cap: str = "round"                       # round | square | project
    join: str = "miter"                      # miter | round | bevel
    blend: str = "normal"
    text_size: float = 16.0
    text_font: str = "Helvetica, Arial, sans-serif"
    text_align: str = "left"
    text_valign: str = "baseline"
    text_style: str = "normal"


class Item:
    """One recorded drawing operation."""
    __slots__ = ("kind", "data", "style", "matrix")

    def __init__(self, kind, data, style, matrix):
        self.kind = kind
        self.data = data
        self.style = style
        self.matrix = matrix


class _PushContext:
    def __init__(self, sketch):
        self.sketch = sketch

    def __enter__(self):
        return self.sketch

    def __exit__(self, *exc):
        self.sketch.pop()
        return False


class SketchError(Exception):
    pass


class Sketch:
    def __init__(self, seed: int = 1, param_values: dict | None = None):
        self.seed = int(seed)
        self.rng = _random.Random(self.seed)
        self._perlin = Perlin(self.seed)
        self._noise_octaves = 4
        self._noise_falloff = 0.5
        self.width = 800.0
        self.height = 800.0
        self.unit = "px"
        self.items: list[Item] = []
        self._style = Style()
        self._matrix = IDENTITY
        self._stack: list[tuple] = []
        self._color_mode = "rgb"
        self._rect_mode = "corner"
        self._ellipse_mode = "center"
        self._shape = None
        self._param_values = param_values or {}
        self.param_specs: list[Param] = []
        self.ns: dict | None = None          # namespace of the running sketch
        # animation settings (used when the sketch defines draw())
        self.anim_frames = 120
        self.anim_fps = 30.0
        self.looping = True

    # ------------------------------------------------------------------ helpers
    def _c(self, args):
        if len(args) == 1 and (args[0] is None or isinstance(args[0], Gradient)):
            return args[0]
        return to_color(args, self._color_mode)

    def _add(self, kind, data, style=None):
        self.items.append(Item(kind, data, style or self._style,
                               None if self._matrix == IDENTITY else self._matrix))

    def _path(self, subpaths, closed, evenodd=False, fill=True):
        style = self._style if fill else replace(self._style, fill=None)
        self._add("path", {"subpaths": subpaths, "closed": closed, "evenodd": evenodd}, style)

    def _update_ns(self, **kw):
        if self.ns is not None:
            self.ns.update(kw)

    # ------------------------------------------------------------------ canvas
    @api("Leinwand")
    def size(self, w, h=None, unit=None, landscape=False):
        """Leinwandgröße: size(800, 600) in Pixel oder size("A3") in Millimeter."""
        if isinstance(w, str):
            if w not in PAPER_SIZES:
                raise SketchError(f"Unbekanntes Format {w!r}. Möglich: {', '.join(PAPER_SIZES)}")
            w, h = PAPER_SIZES[w]
            unit = "mm"
        if h is None:
            h = w
        if landscape and h > w:
            w, h = h, w
        self.width, self.height = float(w), float(h)
        self.unit = unit or "px"
        if self.unit == "mm" and self._style.weight == 1.0:
            self._style = replace(self._style, weight=0.35, text_size=6.0)
        # like p5: whole numbers are ints, so range(0, width, 10) works
        self._update_ns(width=_num(self.width), height=_num(self.height))

    @api("Leinwand")
    def background(self, *c):
        """Füllt die ganze Leinwand mit einer Farbe oder einem Verlauf."""
        paint = self._c(c)
        self._add("background", {"paint": paint}, Style(fill=paint, stroke=None))

    @api("Leinwand")
    def clear(self):
        """Löscht alles bisher Gezeichnete."""
        self.items = []

    # ------------------------------------------------------------------ colour & style
    @api("Farbe & Stil")
    def fill(self, *c):
        """Füllfarbe: fill(255), fill(255, 0, 0), fill("#1f5fbf"), fill("tomato"), fill(verlauf)."""
        self._style = replace(self._style, fill=self._c(c))

    @api("Farbe & Stil")
    def no_fill(self):
        """Formen nicht füllen."""
        self._style = replace(self._style, fill=None)

    @api("Farbe & Stil")
    def stroke(self, *c):
        """Linienfarbe (gleiche Formen wie fill)."""
        self._style = replace(self._style, stroke=self._c(c))

    @api("Farbe & Stil")
    def no_stroke(self):
        """Keine Umrisslinien."""
        self._style = replace(self._style, stroke=None)

    @api("Farbe & Stil")
    def stroke_weight(self, w):
        """Linienstärke (in px bzw. mm)."""
        self._style = replace(self._style, weight=float(w))

    @api("Farbe & Stil")
    def stroke_cap(self, cap):
        """Linienenden: ROUND, SQUARE oder PROJECT."""
        self._style = replace(self._style, cap=cap)

    @api("Farbe & Stil")
    def stroke_join(self, join):
        """Ecken: MITER, ROUND oder BEVEL."""
        self._style = replace(self._style, join=join)

    @api("Farbe & Stil")
    def blend_mode(self, mode="normal"):
        """Mischmodus: NORMAL, MULTIPLY, SCREEN, OVERLAY, DARKEN, LIGHTEN, DIFFERENCE, …"""
        self._style = replace(self._style, blend=str(mode).lower())

    @api("Farbe & Stil")
    def color_mode(self, mode):
        """RGB (0–255, Alpha 0–255) oder HSB (Farbton 0–360, S/B 0–100, Alpha 0–1)."""
        self._color_mode = str(mode).lower()

    @api("Farbe & Stil")
    def color(self, *c) -> Color:
        """Erzeugt ein Farbobjekt (.hex, .alpha(0.5), .lighter(), .darker())."""
        return to_color(c, self._color_mode)

    @api("Farbe & Stil")
    def hsb(self, h, s=100, b=100, a=1.0) -> Color:
        """Farbe aus Farbton (0–360), Sättigung und Helligkeit (0–100)."""
        return hsb(h, s, b, a)

    @api("Farbe & Stil")
    def lerp_color(self, c1, c2, t) -> Color:
        """Mischt zwei Farben (t = 0 … 1)."""
        return lerp_color(c1, c2, t)

    @api("Farbe & Stil")
    def color_ramp(self, colors, t) -> Color:
        """Weicher Farbverlauf durch eine Liste von Farben, abgefragt bei t (0 … 1)."""
        return color_ramp(colors, t)

    @api("Farbe & Stil")
    def palette(self, name=None, shuffle=False) -> list:
        """Kuratierte Palette (Liste von Farben). Ohne Name: zufällige Palette. palettes() listet alle."""
        if name is None:
            name = self.rng.choice(sorted(PALETTES))
        if name not in PALETTES:
            raise SketchError(f"Unbekannte Palette {name!r}. Möglich: {', '.join(PALETTES)}")
        cols = list(PALETTES[name])
        if shuffle:
            self.rng.shuffle(cols)
        return cols

    @api("Farbe & Stil")
    def palettes(self) -> list:
        """Namen aller eingebauten Paletten."""
        return list(PALETTES)

    @api("Farbe & Stil")
    def linear_gradient(self, x0, y0, x1, y1, colors) -> Gradient:
        """Linearer Verlauf von (x0, y0) nach (x1, y1); colors = [farbe, …] oder [(0, farbe), (1, farbe)]."""
        return Gradient("linear", (x0, y0, x1, y1), colors)

    @api("Farbe & Stil")
    def radial_gradient(self, cx, cy, r, colors) -> Gradient:
        """Radialer Verlauf um (cx, cy) mit Radius r."""
        return Gradient("radial", (cx, cy, r), colors)

    # ------------------------------------------------------------------ transforms
    @api("Transformation")
    def push(self):
        """Speichert Stil und Transformation. Auch als `with push(): …` verwendbar."""
        self._stack.append((self._style, self._matrix, self._color_mode, self._rect_mode, self._ellipse_mode))
        return _PushContext(self)

    @api("Transformation")
    def pop(self):
        """Stellt den mit push() gespeicherten Zustand wieder her."""
        if not self._stack:
            raise SketchError("pop() ohne vorheriges push()")
        self._style, self._matrix, self._color_mode, self._rect_mode, self._ellipse_mode = self._stack.pop()

    @api("Transformation")
    def translate(self, x, y=0):
        """Verschiebt den Ursprung."""
        self._matrix = mat_mul(self._matrix, (1, 0, 0, 1, float(x), float(y)))

    @api("Transformation")
    def rotate(self, angle):
        """Dreht um den Ursprung (Winkel im Bogenmaß, z. B. radians(45) oder PI / 4)."""
        c, s = math.cos(angle), math.sin(angle)
        self._matrix = mat_mul(self._matrix, (c, s, -s, c, 0, 0))

    @api("Transformation")
    def scale(self, sx, sy=None):
        """Skaliert (sy optional)."""
        self._matrix = mat_mul(self._matrix, (float(sx), 0, 0, float(sx if sy is None else sy), 0, 0))

    @api("Transformation")
    def shear_x(self, angle):
        """Schert entlang der x-Achse."""
        self._matrix = mat_mul(self._matrix, (1, 0, math.tan(angle), 1, 0, 0))

    @api("Transformation")
    def shear_y(self, angle):
        """Schert entlang der y-Achse."""
        self._matrix = mat_mul(self._matrix, (1, math.tan(angle), 0, 1, 0, 0))

    @api("Transformation")
    def reset_matrix(self):
        """Setzt alle Transformationen zurück."""
        self._matrix = IDENTITY

    # ------------------------------------------------------------------ shapes
    @api("Formen")
    def rect_mode(self, mode):
        """CORNER (x, y, b, h), CENTER (Mitte, b, h) oder CORNERS (x1, y1, x2, y2)."""
        self._rect_mode = mode

    @api("Formen")
    def ellipse_mode(self, mode):
        """CENTER (Standard), CORNER oder RADIUS."""
        self._ellipse_mode = mode

    @api("Formen")
    def point(self, x, y):
        """Punkt in Linienfarbe und -stärke."""
        st = self._style
        if st.stroke is None:
            return
        r = max(st.weight, 0.01) / 2
        self._add("ellipse", {"cx": x, "cy": y, "rx": r, "ry": r}, Style(fill=st.stroke, stroke=None, blend=st.blend))

    @api("Formen")
    def line(self, x1, y1, x2, y2):
        """Linie von (x1, y1) nach (x2, y2)."""
        self._path([[("M", x1, y1), ("L", x2, y2)]], [False], fill=False)

    @api("Formen")
    def rect(self, x, y, w, h, r=0):
        """Rechteck; r = Eckenradius."""
        if self._rect_mode == "center":
            x, y = x - w / 2, y - h / 2
        elif self._rect_mode == "corners":
            x, y, w, h = min(x, w), min(y, h), abs(w - x), abs(h - y)
        if w < 0:
            x, w = x + w, -w
        if h < 0:
            y, h = y + h, -h
        self._add("rect", {"x": x, "y": y, "w": w, "h": h, "r": min(abs(r), w / 2, h / 2)})

    @api("Formen")
    def square(self, x, y, s, r=0):
        """Quadrat mit Seitenlänge s."""
        self.rect(x, y, s, s, r)

    @api("Formen")
    def ellipse(self, x, y, w, h=None):
        """Ellipse mit Breite w und Höhe h (Durchmesser)."""
        h = w if h is None else h
        if self._ellipse_mode == "corner":
            x, y = x + w / 2, y + h / 2
        elif self._ellipse_mode == "radius":
            w, h = w * 2, h * 2
        self._add("ellipse", {"cx": x, "cy": y, "rx": abs(w) / 2, "ry": abs(h) / 2})

    @api("Formen")
    def circle(self, x, y, d):
        """Kreis mit Durchmesser d (wie in p5.js)."""
        self.ellipse(x, y, d, d)

    @api("Formen")
    def arc(self, x, y, w, h, start, stop, mode="open"):
        """Ellipsenbogen von Winkel start bis stop; mode: OPEN, CHORD oder PIE."""
        rx, ry = abs(w) / 2, abs(h) / 2
        span = stop - start
        n = max(4, int(abs(span) / (2 * math.pi) * max(24, int(max(rx, ry) * 1.2))))
        seg = [("M" if i == 0 else "L", x + rx * math.cos(start + span * i / n),
                y + ry * math.sin(start + span * i / n)) for i in range(n + 1)]
        if mode == "pie":
            seg.append(("L", x, y))
            self._path([seg], [True])
        elif mode == "chord":
            self._path([seg], [True])
        else:
            # open arc: filled like a chord, but the outline stays open
            if self._style.fill is not None:
                self._add("path", {"subpaths": [seg], "closed": [True], "evenodd": False},
                          replace(self._style, stroke=None))
            if self._style.stroke is not None:
                self._path([seg], [False], fill=False)

    @api("Formen")
    def triangle(self, x1, y1, x2, y2, x3, y3):
        """Dreieck aus drei Punkten."""
        self._path([[("M", x1, y1), ("L", x2, y2), ("L", x3, y3)]], [True])

    @api("Formen")
    def quad(self, x1, y1, x2, y2, x3, y3, x4, y4):
        """Viereck aus vier Punkten."""
        self._path([[("M", x1, y1), ("L", x2, y2), ("L", x3, y3), ("L", x4, y4)]], [True])

    @api("Formen")
    def polygon(self, points, close=True):
        """Polygon aus einer Liste von (x, y)-Punkten."""
        pts = list(points)
        if len(pts) < 2:
            return
        self._path([[("M", *pts[0])] + [("L", *p) for p in pts[1:]]], [close])

    @api("Formen")
    def polyline(self, points):
        """Offene Linie durch eine Liste von (x, y)-Punkten (ohne Füllung)."""
        pts = list(points)
        if len(pts) < 2:
            return
        self._path([[("M", *pts[0])] + [("L", *p) for p in pts[1:]]], [False], fill=False)

    @api("Formen")
    def bezier(self, x1, y1, cx1, cy1, cx2, cy2, x2, y2):
        """Kubische Bézierkurve mit zwei Kontrollpunkten."""
        self._path([[("M", x1, y1), ("C", cx1, cy1, cx2, cy2, x2, y2)]], [False])

    @api("Formen")
    def curve(self, points, closed=False, tension=0.5):
        """Glatte Kurve durch alle Punkte (Catmull-Rom); tension 0 … 1."""
        pts = [tuple(p) for p in points]
        if len(pts) < 2:
            return
        self._path([_catmull_rom(pts, closed, tension)], [closed])

    # ------------------------------------------------------------------ custom shapes
    @api("Eigene Formen")
    def begin_shape(self, kind=None):
        """Beginnt eine eigene Form; kind: None (Polygon), POINTS oder LINES."""
        self._shape = {"kind": kind, "subpaths": [[]], "curve": [], "contour": False}

    def _flush_curve(self):
        sh = self._shape
        if not sh["curve"]:
            return
        sub = sh["subpaths"][-1]
        pts = sh["curve"]
        sh["curve"] = []
        if len(pts) == 1:
            sub.append(("L" if sub else "M", *pts[0]))
            return
        segs = _catmull_rom(pts, False, 0.5)
        if sub:
            segs[0] = ("L", *pts[0])
        sub.extend(segs)

    def _need_shape(self):
        if self._shape is None:
            raise SketchError("vertex() ohne begin_shape()")
        return self._shape

    @api("Eigene Formen")
    def vertex(self, x, y):
        """Eckpunkt der aktuellen Form."""
        sh = self._need_shape()
        self._flush_curve()
        sub = sh["subpaths"][-1]
        sub.append(("L" if sub else "M", x, y))

    @api("Eigene Formen")
    def curve_vertex(self, x, y):
        """Punkt einer glatten Kurve (alle curve_vertex-Punkte werden weich verbunden)."""
        self._need_shape()["curve"].append((x, y))

    @api("Eigene Formen")
    def bezier_vertex(self, cx1, cy1, cx2, cy2, x, y):
        """Bézier-Segment vom letzten Punkt nach (x, y)."""
        sh = self._need_shape()
        self._flush_curve()
        sh["subpaths"][-1].append(("C", cx1, cy1, cx2, cy2, x, y))

    @api("Eigene Formen")
    def quadratic_vertex(self, cx, cy, x, y):
        """Quadratisches Bézier-Segment vom letzten Punkt nach (x, y)."""
        sh = self._need_shape()
        self._flush_curve()
        sub = sh["subpaths"][-1]
        if not sub:
            raise SketchError("quadratic_vertex() braucht vorher einen vertex()")
        last = sub[-1][-2:]
        c1 = (last[0] + 2 / 3 * (cx - last[0]), last[1] + 2 / 3 * (cy - last[1]))
        c2 = (x + 2 / 3 * (cx - x), y + 2 / 3 * (cy - y))
        sub.append(("C", *c1, *c2, x, y))

    @api("Eigene Formen")
    def begin_contour(self):
        """Beginnt ein Loch innerhalb der Form."""
        sh = self._need_shape()
        self._flush_curve()
        sh["subpaths"].append([])
        sh["contour"] = True

    @api("Eigene Formen")
    def end_contour(self):
        """Beendet das Loch."""
        self._flush_curve()

    @api("Eigene Formen")
    def end_shape(self, close=False):
        """Beendet die Form; end_shape(CLOSE) schließt sie."""
        sh = self._need_shape()
        self._flush_curve()
        self._shape = None
        subs = [s for s in sh["subpaths"] if s]
        if not subs:
            return
        if sh["kind"] == "points":
            for s in subs:
                for seg in s:
                    self.point(*seg[-2:])
            return
        if sh["kind"] == "lines":
            pts = [seg[-2:] for s in subs for seg in s]
            for a, b in zip(pts[::2], pts[1::2]):
                self.line(*a, *b)
            return
        closed = [bool(close)] + [True] * (len(subs) - 1)
        self._path(subs, closed, evenodd=len(subs) > 1, fill=True)

    # ------------------------------------------------------------------ text & image
    @api("Text & Bild")
    def text(self, s, x, y):
        """Schreibt Text an (x, y)."""
        self._add("text", {"s": str(s), "x": x, "y": y})

    @api("Text & Bild")
    def text_size(self, size):
        """Schriftgröße."""
        self._style = replace(self._style, text_size=float(size))

    @api("Text & Bild")
    def text_font(self, font):
        """Schriftart, z. B. "Georgia" oder "monospace"."""
        self._style = replace(self._style, text_font=str(font))

    @api("Text & Bild")
    def text_align(self, h, v=None):
        """Ausrichtung: LEFT/CENTER/RIGHT und optional TOP/CENTER/BOTTOM/BASELINE."""
        self._style = replace(self._style, text_align=h, text_valign=v or self._style.text_valign)

    @api("Text & Bild")
    def text_style(self, style):
        """NORMAL, BOLD, ITALIC oder BOLDITALIC."""
        self._style = replace(self._style, text_style=style)

    @api("Text & Bild")
    def image(self, img, x, y, w=None, h=None, smooth=True):
        """Zeichnet ein Bild: numpy-Array (H×W, H×W×3/4; float 0–1 oder 0–255), PIL-Bild oder Liste."""
        data, iw, ih = to_png(img)
        if w is None and h is None:
            w, h = iw, ih
        elif h is None:
            h = w * ih / iw
        elif w is None:
            w = h * iw / ih
        self._add("image", {"png": data, "x": x, "y": y, "w": w, "h": h, "smooth": smooth})

    # ------------------------------------------------------------------ animation
    @api("Animation")
    def animation(self, frames=None, fps=None):
        """Länge und Tempo der Animation: animation(frames=240, fps=30). Gilt, wenn draw() definiert ist."""
        if frames is not None:
            self.anim_frames = max(1, int(frames))
        if fps is not None:
            self.anim_fps = max(1.0, float(fps))
        self._update_ns(frames=self.anim_frames, fps=self.anim_fps)

    @api("Animation")
    def frame_rate(self, fps):
        """Bilder pro Sekunde (Standard 30)."""
        self.animation(fps=fps)

    @api("Animation")
    def duration(self, seconds):
        """Länge in Sekunden (setzt frames = Sekunden × fps)."""
        self.animation(frames=round(float(seconds) * self.anim_fps))

    @api("Animation")
    def no_loop(self):
        """draw() nur einmal ausführen – die Skizze ist dann ein Standbild."""
        self.looping = False

    @api("Animation")
    def loop(self):
        """draw() wieder für jedes Bild ausführen (Standard)."""
        self.looping = True

    @api("Animation")
    def loop_noise(self, x, y, t, speed=1.0):
        """Noise, das sich bei t = 1 nahtlos wiederholt – ideal für Endlos-Loops (t = 0 … 1)."""
        t = t % 1.0
        return (1 - t) * self.noise(x, y, t * speed) + t * self.noise(x, y, (t - 1) * speed)

    # ------------------------------------------------------------------ randomness
    @api("Zufall & Noise")
    def random(self, a=None, b=None):
        """random() → 0…1, random(10) → 0…10, random(3, 7), random([liste]) → zufälliges Element."""
        if a is None:
            return self.rng.random()
        if isinstance(a, (list, tuple, str, range)):
            return self.rng.choice(a)
        if b is None:
            return self.rng.random() * a
        return a + self.rng.random() * (b - a)

    @api("Zufall & Noise")
    def random_int(self, a, b=None):
        """Ganze Zufallszahl: random_int(6) → 0…5, random_int(1, 6) → 1…6."""
        if b is None:
            return self.rng.randrange(int(a))
        return self.rng.randint(int(a), int(b))

    @api("Zufall & Noise")
    def random_gaussian(self, mean=0.0, sd=1.0):
        """Normalverteilte Zufallszahl."""
        return self.rng.gauss(mean, sd)

    @api("Zufall & Noise")
    def random_choice(self, seq, weights=None):
        """Zufälliges Element, optional gewichtet."""
        if weights is None:
            return self.rng.choice(list(seq))
        return self.rng.choices(list(seq), weights=weights)[0]

    @api("Zufall & Noise")
    def chance(self, p):
        """True mit Wahrscheinlichkeit p (0 … 1)."""
        return self.rng.random() < p

    @api("Zufall & Noise")
    def shuffle(self, seq) -> list:
        """Gibt eine gemischte Kopie der Liste zurück."""
        out = list(seq)
        self.rng.shuffle(out)
        return out

    @api("Zufall & Noise")
    def random_seed(self, n):
        """Setzt den Zufalls-Seed neu."""
        self.rng.seed(n)

    @api("Zufall & Noise")
    def noise(self, x, y=0.0, z=None):
        """Perlin-Noise im Bereich 0 … 1 (1D, 2D oder 3D) – weicher Zufall."""
        total, amp, norm, f = 0.0, 1.0, 0.0, 1.0
        p = self._perlin
        for i in range(self._noise_octaves):
            if z is None:
                v = p.noise2(x * f + i * 17.31, y * f - i * 9.73)
            else:
                v = p.noise3(x * f + i * 17.31, y * f - i * 9.73, z * f + i * 3.7)
            total += v * amp
            norm += amp
            amp *= self._noise_falloff
            f *= 2
        v = 0.5 + 0.5 * total / norm
        return 0.0 if v < 0 else 1.0 if v > 1 else v

    @api("Zufall & Noise")
    def noise_detail(self, octaves=4, falloff=0.5):
        """Detailstufen (Oktaven) und Abfall der Noise-Funktion."""
        self._noise_octaves = max(1, int(octaves))
        self._noise_falloff = float(falloff)

    @api("Zufall & Noise")
    def noise_seed(self, n):
        """Neuer Seed nur für noise()."""
        self._perlin = Perlin(int(n))

    # ------------------------------------------------------------------ parameters
    @api("Parameter")
    def param(self, name, default, min=None, max=None, step=None, options=None, label=None, help=""):
        """Regler im Studio: n = param("Anzahl", 40, 1, 200). Mit options=[…] wird es eine Auswahl."""
        label = label or name
        existing = next((p for p in self.param_specs if p.name == name), None)
        if existing is None:
            if options is not None:
                opts = [o if isinstance(o, (tuple, list)) else (o, o) for o in options]
                opts = [(str(v), str(lab)) for v, lab in opts]
                spec = Param(name, label, str(default), choices=opts, help=help)
            elif isinstance(default, bool) or (isinstance(default, str) and default.startswith("#")):
                spec = Param(name, label, default, help=help)
            elif isinstance(default, (int, float)):
                is_int = isinstance(default, int) and (step is None or float(step).is_integer())
                lo = 0 if min is None else min
                hi = max if max is not None else (builtins_max(10, default * 3) if is_int else builtins_max(1.0, default * 3))
                st = step if step is not None else (1 if is_int else round((hi - lo) / 200, 6) or 0.001)
                spec = Param(name, label, int(default) if is_int else float(default),
                             lo, hi, st, help=help, kind="int" if is_int else "float")
            else:
                spec = Param(name, label, default, help=help)
            self.param_specs.append(spec)
            existing = spec
        raw = self._param_values.get(name)
        value = existing.parse(raw) if raw is not None else existing.default
        if existing.kind == "choice" and options is not None:
            # return the original (possibly non-string) option value
            for o in options:
                ov = o[0] if isinstance(o, (tuple, list)) else o
                if str(ov) == value:
                    return ov
        return value


builtins_max = max


def _num(v: float):
    return int(v) if float(v).is_integer() else v


def _catmull_rom(pts, closed, tension):
    """Catmull-Rom spline through all points → path segments (M + C…).
    tension 0 = straight lines, 0.5 = classic Catmull-Rom, 1 = very round."""
    k = tension / 3
    n = len(pts)
    if closed:
        ext = [pts[-1]] + pts + [pts[0], pts[1 % n]]
    else:
        ext = [pts[0]] + pts + [pts[-1]]
    segs = [("M", *pts[0])]
    count = n if closed else n - 1
    for i in range(count):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        c1 = (p1[0] + (p2[0] - p0[0]) * k, p1[1] + (p2[1] - p0[1]) * k)
        c2 = (p2[0] - (p3[0] - p1[0]) * k, p2[1] - (p3[1] - p1[1]) * k)
        segs.append(("C", *c1, *c2, *p2))
    return segs
