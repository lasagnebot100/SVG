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
from .three import (I4, Scene3D, from_2d, geo_box, geo_cylinder, geo_ellipsoid, geo_plane, geo_torus, m4_apply,
                    m4_mul, m4_rot_x, m4_rot_y, m4_rot_z, m4_scale, m4_translate)

IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

OSC_VALUES: dict = {}       # address → list of values (latest message), shared by all sketches

CATEGORIES = ["Leinwand", "Farbe & Stil", "Formen", "Eigene Formen", "Geometrie", "Transformation", "3D",
              "Text & Bild", "Bilder & Daten", "Pixel & Filter", "Shader", "Animation", "Ton & Interaktion", "Wachstum", "Simulation", "Muster", "Mathe-Kunst", "Zufall & Noise", "Mathe",
              "Parameter", "Edition", "Werkzeuge"]


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
        self._param_values = dict(param_values or {})
        # keyframes per slider: {"Name": [[frame, value], …]} – applied per frame by apply_keys()
        self._param_keys = self._param_values.pop("__keys__", None) or {}
        # recorded mouse/keyboard input, one entry per frame (live mode → export)
        self.input_track = self._param_values.pop("__input__", None) or []
        self.param_specs: list[Param] = []
        self.features: dict = {}             # feature("Palette", "nacht") – traits of this variant (editions)
        self.ns: dict | None = None          # namespace of the running sketch
        # 3D state (see three.py) and input (mouse/keyboard/OSC, filled by the runner)
        self._m4 = I4
        self._s3d = None
        self.meshes3d: list = []
        self._orbit = None
        self.input: dict = {}
        self._osc: dict = OSC_VALUES          # shared: filled by the OSC receiver / TouchDesigner
        self._frames_explicit = False
        self.audio_sources: list = []
        self._audio_sync = None
        self._osc_out: list = []
        # animation settings (used when the sketch defines draw())
        self.anim_frames = 120
        self.anim_fps = 30.0
        self.looping = True
        # tempo for VJ work: tempo() sets bpm; in live mode the Studio sends its own clock (tap, Ableton Link)
        self.bpm = 120.0
        self.beats_per_bar = 4
        self.beat = 0.0

    # ------------------------------------------------------------------ helpers
    def _c(self, args):
        if len(args) == 1 and (args[0] is None or isinstance(args[0], Gradient)):
            return args[0]
        return to_color(args, self._color_mode)

    def _add(self, kind, data, style=None):
        if self._s3d is not None and not self._s3d.empty:
            self._flush3d()                   # 2D drawn after 3D lies on top of it
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
    # every transform updates the 2D matrix and the 3D matrix (z = 0 plane = 2D canvas)
    @api("Transformation")
    def push(self):
        """Speichert Stil und Transformation. Auch als `with push(): …` verwendbar."""
        self._stack.append((self._style, self._matrix, self._color_mode, self._rect_mode, self._ellipse_mode,
                            self._m4))
        return _PushContext(self)

    @api("Transformation")
    def pop(self):
        """Stellt den mit push() gespeicherten Zustand wieder her."""
        if not self._stack:
            raise SketchError("pop() ohne vorheriges push()")
        (self._style, self._matrix, self._color_mode, self._rect_mode, self._ellipse_mode,
         self._m4) = self._stack.pop()

    @api("Transformation")
    def translate(self, x, y=0, z=0):
        """Verschiebt den Ursprung (z optional, für 3D)."""
        self._matrix = mat_mul(self._matrix, (1, 0, 0, 1, float(x), float(y)))
        self._m4 = m4_mul(self._m4, m4_translate(float(x), float(y), float(z)))

    @api("Transformation")
    def rotate(self, angle):
        """Dreht um den Ursprung (Winkel im Bogenmaß, z. B. radians(45) oder PI / 4)."""
        c, s = math.cos(angle), math.sin(angle)
        self._matrix = mat_mul(self._matrix, (c, s, -s, c, 0, 0))
        self._m4 = m4_mul(self._m4, m4_rot_z(angle))

    @api("Transformation")
    def scale(self, sx, sy=None, sz=None):
        """Skaliert (sy, sz optional; ein Wert skaliert in 3D alle Achsen)."""
        sy2 = float(sx if sy is None else sy)
        self._matrix = mat_mul(self._matrix, (float(sx), 0, 0, sy2, 0, 0))
        sz2 = float(sx if sy is None else (1.0 if sz is None else sz))
        self._m4 = m4_mul(self._m4, m4_scale(float(sx), sy2, sz2))

    @api("Transformation")
    def shear_x(self, angle):
        """Schert entlang der x-Achse."""
        self._matrix = mat_mul(self._matrix, (1, 0, math.tan(angle), 1, 0, 0))
        self._m4 = m4_mul(self._m4, from_2d((1, 0, math.tan(angle), 1, 0, 0)))

    @api("Transformation")
    def shear_y(self, angle):
        """Schert entlang der y-Achse."""
        self._matrix = mat_mul(self._matrix, (1, math.tan(angle), 0, 1, 0, 0))
        self._m4 = m4_mul(self._m4, from_2d((1, math.tan(angle), 0, 1, 0, 0)))

    @api("Transformation")
    def reset_matrix(self):
        """Setzt alle Transformationen zurück."""
        self._matrix = IDENTITY
        self._m4 = I4

    # ------------------------------------------------------------------ 3D
    def _scene(self) -> Scene3D:
        if self._s3d is None:
            self._s3d = Scene3D(self.width, self.height)
        return self._s3d

    def _mesh(self, name, geo):
        verts, faces, closed = geo
        world = [m4_apply(self._m4, v) for v in verts]
        st = self._style
        fill = st.fill.average() if isinstance(st.fill, Gradient) else st.fill
        stroke = st.stroke.average() if isinstance(st.stroke, Gradient) else st.stroke
        if fill is None and stroke is None:
            return
        # a mirrored transform (negative determinant) turns faces inside out → reverse them
        m = self._m4
        det = m[0] * (m[5] * m[10] - m[6] * m[9]) - m[1] * (m[4] * m[10] - m[6] * m[8]) + m[2] * (m[4] * m[9] - m[5] * m[8])
        if det < 0:
            faces = [list(reversed(f)) for f in faces]
        sc = self._scene()
        mid = len(self.meshes3d)
        for f in faces:
            sc.faces.append(([world[i] for i in f], fill, stroke if st.weight > 0 else None, st.weight,
                             closed and fill is not None, mid))
        self.meshes3d.append({"name": name, "verts": world, "faces": [list(f) for f in faces], "closed": closed,
                              "color": (fill or stroke).rgba if (fill or stroke) else (255, 255, 255, 255)})

    def begin_frame3d(self):
        """Start of draw(): like p5, lights must be set again every frame; the camera persists."""
        if self._s3d is not None:
            self._flush3d()
            self._s3d.lights = []

    def _flush3d(self):
        """Project pending 3D shapes into 2D items (depth sorted)."""
        sc = self._s3d
        if sc is None or sc.empty:
            return
        sc.width, sc.height = self.width, self.height
        for pts, fill, stroke, weight, closed in sc.render():
            style = replace(self._style, fill=fill, stroke=stroke, weight=weight, blend="normal")
            segs = [("M", *pts[0])] + [("L", *p) for p in pts[1:]]
            self.items.append(Item("path", {"subpaths": [segs], "closed": [closed], "evenodd": False,
                                            "from3d": True}, style, None))
        sc.faces.clear()
        sc.lines.clear()

    @api("3D")
    def box(self, w, h=None, d=None):
        """Quader (Würfel mit einer Angabe), Mittelpunkt im Ursprung."""
        h = w if h is None else h
        self._mesh("Quader", geo_box(w, h, w if d is None else d))

    @api("3D")
    def sphere(self, r, detail_x=24, detail_y=16):
        """Kugel mit Radius r."""
        self._mesh("Kugel", geo_ellipsoid(r, r, r, max(3, int(detail_x)), max(2, int(detail_y))))

    @api("3D")
    def ellipsoid(self, rx, ry, rz, detail_x=24, detail_y=16):
        """Ellipsoid mit drei Radien."""
        self._mesh("Ellipsoid", geo_ellipsoid(rx, ry, rz, max(3, int(detail_x)), max(2, int(detail_y))))

    @api("3D")
    def cylinder(self, r, h, detail=24, caps=True):
        """Zylinder entlang der y-Achse."""
        self._mesh("Zylinder", geo_cylinder(r, h, max(3, int(detail)), caps=caps))

    @api("3D")
    def cone(self, r, h, detail=24, cap=True):
        """Kegel entlang der y-Achse (Spitze oben)."""
        self._mesh("Kegel", geo_cylinder(r, h, max(3, int(detail)), top_r=0, caps=cap))

    @api("3D")
    def torus(self, r, tube, detail_x=32, detail_y=16):
        """Torus (Ring) mit Radius r und Rohrdicke tube."""
        self._mesh("Torus", geo_torus(r, tube, max(3, int(detail_x)), max(3, int(detail_y))))

    @api("3D")
    def plane(self, w, h=None, detail_x=1, detail_y=1):
        """Ebene in der xy-Ebene (beidseitig sichtbar)."""
        self._mesh("Ebene", geo_plane(w, w if h is None else h, max(1, int(detail_x)), max(1, int(detail_y))))

    @api("3D")
    def mesh(self, vertices, faces, closed=False):
        """Eigenes Mesh: vertices = [(x, y, z), …], faces = [(i, j, k, …), …]."""
        self._mesh("Mesh", ([tuple(map(float, v)) for v in vertices], [list(f) for f in faces], bool(closed)))

    @api("3D")
    def line3d(self, x1, y1, z1, x2, y2, z2):
        """Linie im Raum."""
        self.polyline3d([(x1, y1, z1), (x2, y2, z2)])

    @api("3D")
    def polyline3d(self, points):
        """Linienzug durch 3D-Punkte (x, y, z)."""
        st = self._style
        if st.stroke is None or st.weight <= 0:
            return
        world = [m4_apply(self._m4, tuple(map(float, p))) for p in points]
        stroke = st.stroke.average() if isinstance(st.stroke, Gradient) else st.stroke
        self._scene().lines.append((world, stroke, st.weight))
        self.meshes3d.append({"name": "Linie", "verts": world, "faces": [], "line": True, "color": stroke.rgba})

    @api("3D")
    def rotate_x(self, angle):
        """Dreht um die x-Achse."""
        self._m4 = m4_mul(self._m4, m4_rot_x(angle))

    @api("3D")
    def rotate_y(self, angle):
        """Dreht um die y-Achse."""
        self._m4 = m4_mul(self._m4, m4_rot_y(angle))

    @api("3D")
    def rotate_z(self, angle):
        """Dreht um die z-Achse (wie rotate())."""
        self.rotate(angle)

    @api("3D")
    def camera(self, ex=None, ey=None, ez=None, tx=None, ty=None, tz=None, dx=0.0, dy=1.0, dz=0.0):
        """Kamera: Augpunkt (ex, ey, ez), Ziel (tx, ty, tz), „unten“-Richtung (dx, dy, dz). Ohne Werte: Standard."""
        sc = self._scene()
        if ex is None:
            sc.reset_camera()
            return
        sc.eye = (float(ex), float(ey), float(ez))
        sc.target = (float(self.width / 2 if tx is None else tx), float(self.height / 2 if ty is None else ty),
                     float(0 if tz is None else tz))
        sc.down = (float(dx), float(dy), float(dz))

    @api("3D")
    def perspective(self, fov=None, near=1.0):
        """Perspektivische Projektion (fov = Blickwinkel, Standard PI / 3)."""
        sc = self._scene()
        sc.ortho = None
        sc.fov = math.pi / 3 if fov is None else float(fov)
        sc.near = float(near)

    @api("3D")
    def ortho(self, zoom=1.0):
        """Orthografische Projektion (ohne Fluchtpunkt)."""
        self._scene().ortho = float(zoom)

    @api("3D")
    def lights(self):
        """Standard-Beleuchtung (Umgebungslicht + Licht von vorne)."""
        sc = self._scene()
        sc.lights = [("ambient", Color(128, 128, 128), None), ("directional", Color(128, 128, 128), (0.0, 0.0, -1.0))]

    @api("3D")
    def no_lights(self):
        """Lichter aus – Flächen in reiner Füllfarbe."""
        self._scene().lights = []

    @api("3D")
    def ambient_light(self, *c):
        """Umgebungslicht (Farbe)."""
        self._scene().lights.append(("ambient", to_color(c, self._color_mode), None))

    @api("3D")
    def directional_light(self, *args):
        """Gerichtetes Licht: directional_light(farbe, dx, dy, dz) oder wie p5 (r, g, b, dx, dy, dz)."""
        col, (dx, dy, dz) = _light_args(args, self._color_mode)
        self._scene().lights.append(("directional", col, _unit((dx, dy, dz))))

    @api("3D")
    def point_light(self, *args):
        """Punktlicht: point_light(farbe, x, y, z) oder wie p5 (r, g, b, x, y, z)."""
        col, pos = _light_args(args, self._color_mode)
        self._scene().lights.append(("point", col, m4_apply(self._m4, pos)))

    @api("3D")
    def orbit_control(self, sensitivity=1.0, zoom=True):
        """Kamera mit der Maus drehen (ziehen) und zoomen (Mausrad) – im Studio im Live-Modus."""
        sc = self._scene()
        o = self._orbit
        if o is None:
            o = self._orbit = {"theta": 0.0, "phi": 0.0, "dist": (self.height / 2) / math.tan(sc.fov / 2)}
        inp = self.input
        if inp.get("mouse_is_pressed"):
            o["theta"] += (inp.get("mouse_x", 0) - inp.get("pmouse_x", 0)) * 0.01 * sensitivity
            o["phi"] = max(-1.5, min(1.5, o["phi"] + (inp.get("mouse_y", 0) - inp.get("pmouse_y", 0)) * 0.01 * sensitivity))
        if zoom and inp.get("wheel"):
            o["dist"] = max(10.0, o["dist"] * (1.0015 ** inp["wheel"]))
        tx, ty, tz = self.width / 2, self.height / 2, 0.0
        sc.target = (tx, ty, tz)
        sc.eye = (tx + o["dist"] * math.sin(o["theta"]) * math.cos(o["phi"]),
                  ty - o["dist"] * math.sin(o["phi"]),
                  tz + o["dist"] * math.cos(o["theta"]) * math.cos(o["phi"]))
        sc.down = (0.0, 1.0, 0.0)

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

    # ------------------------------------------------------------------ images & data
    @api("Bilder & Daten")
    def load_image(self, path):
        """Bild laden (PNG, JPG …) aus dem Skizzen- oder daten/-Ordner, oder "beispiel:kugeln"/"beispiel:portrait"."""
        from .raster import load_image
        return load_image(path)

    @api("Bilder & Daten")
    def load_csv(self, path, delimiter=None, numbers=True):
        """CSV als Liste von Dicts; Zahlen (auch 12,5) werden umgewandelt. Beispiel: "beispiel:temperaturen.csv"."""
        from .data import load_csv
        return load_csv(path, delimiter, numbers)

    @api("Bilder & Daten")
    def load_json(self, path):
        """JSON-Datei laden (Beispiel: "beispiel:zufall.json")."""
        from .data import load_json
        return load_json(path)

    @api("Bilder & Daten")
    def load_text(self, path):
        """Textdatei als String."""
        from .data import load_text
        return load_text(path)

    @api("Bilder & Daten")
    def load_lines(self, path):
        """Textdatei als Liste von Zeilen."""
        from .data import load_lines
        return load_lines(path)

    @api("Bilder & Daten")
    def load_svg(self, path):
        """SVG-Datei laden → Formen mit Punktlisten (.shapes, .width, .height)."""
        from .svgimport import load_svg
        return load_svg(path)

    @api("Bilder & Daten")
    def draw_svg(self, svg, x=0, y=0, w=None, h=None, keep_style=True):
        """Geladene SVG zeichnen (optional auf Breite w / Höhe h skaliert, eigene Farben mit keep_style=False)."""
        from .svgimport import SvgDrawing, load_svg
        if not isinstance(svg, SvgDrawing):
            svg = load_svg(svg)
        sx = (w / svg.width) if w else (h / svg.height if h else 1.0)
        sy = (h / svg.height) if h else sx
        with self.push():
            self.translate(x, y)
            self.scale(sx, sy)
            for shape in svg.shapes:
                if keep_style:
                    self._style = replace(self._style, fill=shape.fill, stroke=shape.stroke,
                                          weight=shape.stroke_width)
                subs = [[("M", *pts[0])] + [("L", *p) for p in pts[1:]] for pts, _ in shape.paths]
                self._path(subs, [cl for _, cl in shape.paths], evenodd=len(subs) > 1)

    @api("Bilder & Daten")
    def text_paths(self, s, x, y, size=None, font=None, align=None):
        """Text als Liste geschlossener Punktlisten (Buchstaben-Umrisse) – ideal für Plotter und Effekte."""
        from .fonts import text_paths
        return text_paths(s, x, y, size or self._style.text_size, self._font_name(font),
                          align or self._style.text_align)

    @api("Bilder & Daten")
    def text_shape(self, s, x, y, size=None, font=None, align=None):
        """Text als echte Form (mit fill/stroke) – erscheint so auch im Plotter-Export und in Blender."""
        polys = self.text_paths(s, x, y, size, font, align)
        if polys:
            subs = [[("M", *p[0])] + [("L", *q) for q in p[1:]] for p in polys]
            self._path(subs, [True] * len(subs), evenodd=True)

    def _font_name(self, font):
        if font:
            return font
        first = self._style.text_font.split(",")[0].strip().strip('"')
        from .fonts import find_font
        from .data import DataError
        try:
            find_font(first)
            return first
        except DataError:
            return None

    # ------------------------------------------------------------------ pixels & filters
    @api("Pixel & Filter")
    def create_image(self, w, h, *c):
        """Neues Bild w × h Pixel (für Pixel-Algorithmen; .pixels, .set_pixels, .get, .set)."""
        from .raster import create_image
        return create_image(w, h, *c)

    @api("Pixel & Filter")
    def snapshot(self, scale=None):
        """Bisher Gezeichnetes als Bild (z. B. für Feedback-Effekte: im nächsten Bild wieder mit image() zeichnen)."""
        from .export import PillowCanvas, px_per_unit
        from .raster import Img, _pil
        _pil()                                   # friendly error if Pillow is missing
        self._flush3d()
        scale = scale or px_per_unit(self, dpi=150)
        canvas = PillowCanvas(self.width, self.height, scale)
        canvas.draw(self.items)
        return Img(canvas.image())

    @api("Pixel & Filter")
    def filter(self, kind, amount=None):
        """Filter auf die ganze Leinwand: BLUR, GRAIN, POSTERIZE, THRESHOLD, INVERT, GRAY, PIXELATE, DITHER, …"""
        if callable(kind) or kind is None:            # Python's built-in filter(function, iterable)
            import builtins
            return builtins.filter(kind, amount)
        img = self.snapshot().filter(kind, amount, seed=self.rng.randrange(1 << 30))
        self.items = []
        data, _, _ = to_png(img)
        self.items.append(Item("image", {"png": data, "x": 0, "y": 0, "w": self.width, "h": self.height,
                                         "smooth": True}, self._style, None))

    # ------------------------------------------------------------------ animation
    @api("Animation")
    def animation(self, frames=None, fps=None):
        """Länge und Tempo der Animation: animation(frames=240, fps=30). Gilt, wenn draw() definiert ist."""
        if frames is not None:
            self.anim_frames = max(1, int(frames))
            self._frames_explicit = True
        if fps is not None:
            self.anim_fps = max(1.0, float(fps))
        self._update_ns(frames=self.anim_frames, fps=self.anim_fps)

    def finalize_timing(self):
        """After setup: a synced sound decides the length (unless frames were set explicitly)."""
        if self._audio_sync is not None and not self._frames_explicit:
            self.anim_frames = self._audio_sync.frames(self.anim_fps)
            self._update_ns(frames=self.anim_frames)

    @api("Animation")
    def frame_rate(self, fps):
        """Bilder pro Sekunde (Standard 30)."""
        self.animation(fps=fps)

    @api("Animation")
    def duration(self, seconds):
        """Länge in Sekunden (setzt frames = Sekunden × fps)."""
        self.animation(frames=round(float(seconds) * self.anim_fps))

    # ------------------------------------------------------------------ geometry (hatching, shapely)
    @api("Geometrie")
    def circle_shape(self, x, y, d, detail=72):
        """Kreis als Punktliste – für Schraffur und shape_union() & Co."""
        r = d / 2
        return [(x + r * math.cos(math.tau * i / detail), y + r * math.sin(math.tau * i / detail))
                for i in range(int(detail))]

    @api("Geometrie")
    def rect_shape(self, x, y, w, h):
        """Rechteck als Punktliste."""
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]

    @api("Geometrie")
    def hatch(self, shape, spacing=4, angle=0.0, offset=0.0):
        """Schraffiert eine Form mit parallelen Linien (Löcher bleiben frei) – ideal für Plotter.
        shape: Punktliste, Liste von Ringen oder shapely-Geometrie. Gibt die Linien zurück."""
        from .geometry2d import hatch_lines
        lines = hatch_lines(shape, float(spacing), float(angle), float(offset))
        if lines and self._style.stroke is not None:
            self._path([[("M", *a), ("L", *b)] for a, b in lines], [False] * len(lines), fill=False)
        return lines

    @api("Geometrie")
    def shape_union(self, *shapes):
        """Vereinigung mehrerer Formen (braucht shapely) → Geometrie für draw_geometry()/hatch()."""
        from .geometry2d import union
        return union(*shapes)

    @api("Geometrie")
    def shape_difference(self, a, b):
        """a ohne b (braucht shapely)."""
        from .geometry2d import difference
        return difference(a, b)

    @api("Geometrie")
    def shape_intersection(self, a, b):
        """Schnittmenge von a und b (braucht shapely)."""
        from .geometry2d import intersection
        return intersection(a, b)

    @api("Geometrie")
    def offset_shape(self, shape, d, join="round"):
        """Form um d vergrößern (d < 0: verkleinern) – für Konturlinien (braucht shapely)."""
        from .geometry2d import offset
        return offset(shape, d, join)

    @api("Geometrie")
    def draw_geometry(self, geom):
        """Zeichnet eine shapely-Geometrie (Flächen mit Löchern, Linien) oder eine Punktliste."""
        from .geometry2d import rings_of, to_geometry
        if not hasattr(geom, "geom_type"):
            geom = to_geometry(geom)
        parts = rings_of(geom)
        areas = [(pts, c) for pts, c in parts if c and len(pts) >= 3]
        lines = [(pts, c) for pts, c in parts if not c and len(pts) >= 2]
        if areas:
            self._path([[("M", *pts[0])] + [("L", *q) for q in pts[1:]] for pts, _ in areas],
                       [True] * len(areas), evenodd=True)
        if lines:
            self._path([[("M", *pts[0])] + [("L", *q) for q in pts[1:]] for pts, _ in lines],
                       [False] * len(lines), fill=False)

    # ------------------------------------------------------------------ GPU shaders
    def _shader_uniforms(self, x, y, w, h, s):
        ns = self.ns or {}
        mx, my = float(ns.get("mouse_x", 0.0)), float(ns.get("mouse_y", 0.0))
        pressed = bool(ns.get("mouse_is_pressed", False))
        fps = float(ns.get("fps", self.anim_fps)) or 30.0
        return {"iTime": float(ns.get("time", 0.0)), "iTimeDelta": 1.0 / fps,
                "iFrame": int(ns.get("frame_count", 1)) - 1,
                "iMouse": ((mx - x) * s, (y + h - my) * s, 1.0 if pressed else 0.0, 0.0)}

    @api("Shader")
    def create_shader(self, source, name="Shader"):
        """GLSL-Fragment-Shader im Shadertoy-Stil: void mainImage(out vec4 fragColor, in vec2 fragCoord).
        Fertige Uniforms: iResolution, iTime, iFrame, iMouse, iChannel0–3. Läuft auf der Grafikkarte."""
        from .shader import Shader
        return Shader(str(source), name)

    @api("Shader")
    def load_shader(self, path):
        """Shader aus einer Datei (.frag/.glsl) im Skizzen- oder daten/-Ordner laden."""
        from .data import read_text
        from .shader import Shader
        return Shader(read_text(path), str(path))

    @api("Shader")
    def shader_image(self, sh, x=0, y=0, w=None, h=None, scale=None, **uniforms):
        """Zeichnet den Shader als Bild (Standard: ganze Leinwand). Eigene Uniforms als Schlüsselwörter:
        shader_image(sh, zoom=2.0, farbe="#ff0080"). Bilder gehen als iChannel0=img hinein."""
        from .export import px_per_unit
        from .shader import render, to_png
        w = self.width - x if w is None else w
        h = self.height - y if h is None else h
        s = float(scale or px_per_unit(self, dpi=96))
        pw, ph = max(1, round(w * s)), max(1, round(h * s))
        rgba = render(sh, pw, ph, {**self._shader_uniforms(x, y, w, h, pw / w), **uniforms})
        self._add("image", {"png": to_png(rgba, pw, ph), "x": x, "y": y, "w": w, "h": h, "smooth": True})

    @api("Shader")
    def apply_shader(self, sh, scale=None, **uniforms):
        """Shader auf die ganze Leinwand anwenden: das bisher Gezeichnete ist iChannel0 (Nachbearbeitung, Feedback)."""
        from .export import px_per_unit
        from .shader import render, to_png
        s = float(scale or px_per_unit(self, dpi=96))
        canvas = self.snapshot(scale=s)
        pw, ph = canvas.width, canvas.height
        rgba = render(sh, pw, ph, {**self._shader_uniforms(0, 0, self.width, self.height, pw / self.width),
                                   "iChannel0": canvas, **uniforms})
        self.items = []
        self.items.append(Item("image", {"png": to_png(rgba, pw, ph), "x": 0, "y": 0, "w": self.width,
                                         "h": self.height, "smooth": True}, self._style, None))

    # ------------------------------------------------------------------ sound & interaction
    @api("Ton & Interaktion")
    def load_audio(self, path, sync=True):
        """Ton laden (WAV, mit ffmpeg auch MP3/OGG/…) → .level(), .spectrum(16), .bass(), .beat(), .waveform().
        sync=True: Animation dauert so lang wie der Ton, und der Ton kommt ins Video. Beispiel: "beispiel:beat.wav"."""
        from .audio import load_audio
        a = load_audio(str(path), self)
        if path not in self.audio_sources:
            self.audio_sources.append(str(path))
        if sync:
            self._audio_sync = a
            self.anim_frames = a.frames(self.anim_fps)
            self._update_ns(frames=self.anim_frames)
        return a

    @api("Ton & Interaktion")
    def tempo(self, bpm, beats_per_bar=4):
        """Tempo für beat, beat_phase und on_beat(): tempo(128). Live gilt der Takt aus dem Studio (Tap, Ableton Link)."""
        bpm = float(bpm)
        if not 1 <= bpm <= 999:
            raise SketchError("tempo(): bpm muss zwischen 1 und 999 liegen")
        self.bpm = bpm
        self.beats_per_bar = max(1, int(beats_per_bar))

    @api("Ton & Interaktion")
    def beat_pulse(self, sharpness=6.0):
        """Lichtblitz im Takt: 1 genau auf dem Schlag, klingt bis zum nächsten ab (größer = kürzer)."""
        return math.exp(-float(sharpness) * (self.beat % 1.0))

    @api("Ton & Interaktion")
    def osc(self, address, default=0.0):
        """Letzter Wert einer OSC-Nachricht (z. B. aus TouchDesigner): osc("/td/level", 0). Studio mit --osc-in starten."""
        v = self._osc.get(address)
        if v is None:
            return default
        return v[0] if len(v) == 1 else list(v)

    @api("Ton & Interaktion")
    def osc_send(self, address, *values):
        """OSC-Nachricht senden (z. B. an TouchDesigner): osc_send("/plotart/x", mouse_x). Studio mit --osc-out starten."""
        self._osc_out.append((str(address), [v if isinstance(v, (int, float, str)) else float(v) for v in values]))

    @api("Ton & Interaktion")
    def midi(self, cc, default=0.0, channel=None):
        """Wert 0–1 eines MIDI-Reglers (Control Change cc) – im Studio-Live-Modus mit angeschlossenem Controller."""
        m = self.input.get("midi") or {}
        v = m.get(f"{channel}:{cc}" if channel is not None else str(cc))
        return default if v is None else float(v)

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
    def apply_keys(self, frame: int):
        """Set slider values from their keyframes for image `frame` (1-based), eased between keys."""
        for name, keys in self._param_keys.items():
            v = keyed_value(keys, frame)
            if v is not None:
                self._param_values[name] = v

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

    # ------------------------------------------------------------------ editions
    @api("Edition")
    def feature(self, name, value):
        """Merkmal dieser Variante für Editionen (wie bei Art Blocks/fxhash): feature("Palette", "nacht").
        Gibt den Wert unverändert zurück. Seltenheiten zeigt das Studio unter „Merkmale“."""
        name = str(name).strip()
        if not name:
            raise SketchError("feature(): Der Name darf nicht leer sein")
        shown = value                        # stored in a readable, JSON-friendly form
        if isinstance(value, bool) or value is None:
            shown = {True: "ja", False: "nein", None: "–"}[value]
        elif isinstance(value, float):
            shown = round(value, 4)
        elif not isinstance(value, (int, str)):
            shown = str(value)
        self.features[name] = shown
        return value


builtins_max = max


def _unit(v):
    ln = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) or 1.0
    return (v[0] / ln, v[1] / ln, v[2] / ln)


def _light_args(args, mode):
    """(colour, (x, y, z)) from either (colour, x, y, z) or p5-style (r, g, b, x, y, z)."""
    if len(args) == 6 and all(isinstance(a, (int, float)) for a in args):
        return to_color(args[:3], mode), tuple(float(a) for a in args[3:])
    if len(args) == 4:
        return to_color((args[0],), mode), tuple(float(a) for a in args[1:])
    if len(args) == 3:
        return Color(255, 255, 255), tuple(float(a) for a in args)
    raise SketchError("Licht: (farbe, x, y, z) oder (r, g, b, x, y, z) angeben")


def keyed_value(keys, frame):
    """Value of a keyframed slider at `frame`: smooth (ease in/out) between numeric keys, else stepped."""
    pts = sorted((float(f), v) for f, v in keys if v is not None)
    if not pts:
        return None
    if frame <= pts[0][0]:
        return pts[0][1]
    for (f0, v0), (f1, v1) in zip(pts, pts[1:]):
        if f0 <= frame <= f1:
            if not isinstance(v0, (int, float)) or isinstance(v0, bool) or not isinstance(v1, (int, float)):
                return v0 if frame < f1 else v1
            t = (frame - f0) / (f1 - f0) if f1 > f0 else 1.0
            t = t * t * (3 - 2 * t)
            v = v0 + (v1 - v0) * t
            return round(v) if isinstance(v0, int) and isinstance(v1, int) else v
    return pts[-1][1]


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
