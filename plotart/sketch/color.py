"""Colours, colour modes, gradients and curated palettes for sketches."""
from __future__ import annotations

import colorsys
from dataclasses import dataclass

CSS_COLORS = {
    "black": "#000000", "white": "#ffffff", "gray": "#808080", "grey": "#808080",
    "silver": "#c0c0c0", "red": "#ff0000", "crimson": "#dc143c", "tomato": "#ff6347",
    "coral": "#ff7f50", "orange": "#ffa500", "gold": "#ffd700", "yellow": "#ffff00",
    "khaki": "#f0e68c", "olive": "#808000", "lime": "#00ff00", "green": "#008000",
    "forestgreen": "#228b22", "seagreen": "#2e8b57", "teal": "#008080", "cyan": "#00ffff",
    "turquoise": "#40e0d0", "skyblue": "#87ceeb", "steelblue": "#4682b4", "blue": "#0000ff",
    "royalblue": "#4169e1", "navy": "#000080", "indigo": "#4b0082", "purple": "#800080",
    "violet": "#ee82ee", "magenta": "#ff00ff", "pink": "#ffc0cb", "hotpink": "#ff69b4",
    "brown": "#a52a2a", "chocolate": "#d2691e", "tan": "#d2b48c", "beige": "#f5f5dc",
    "ivory": "#fffff0", "linen": "#faf0e6", "salmon": "#fa8072", "maroon": "#800000",
    "slategray": "#708090", "darkslategray": "#2f4f4f", "lightgray": "#d3d3d3",
    "transparent": "#00000000",
}

# Curated palettes (first entry is usually a good background)
PALETTES: dict[str, list[str]] = {
    "kobalt": ["#f4f1ea", "#1f5fbf", "#163a7a", "#7fa6e0", "#0d1b3d"],
    "bauhaus": ["#f2ebdd", "#e63a2e", "#f5b700", "#1d4e9e", "#111111"],
    "sonnenuntergang": ["#2b1d3a", "#f25f5c", "#ffe066", "#f7a072", "#7b2d5b"],
    "risograph": ["#f6f1e7", "#ff48b0", "#0078bf", "#ffe800", "#00a95c"],
    "pastell": ["#fbf8f3", "#f6bd60", "#f28482", "#84a59d", "#f5cac3"],
    "wald": ["#eef0e5", "#2d4a3e", "#5f7f5b", "#a3b18a", "#d4a373"],
    "ozean": ["#e9f1f2", "#05445e", "#189ab4", "#75e6da", "#d4f1f4"],
    "neon": ["#0b0b12", "#ff2e88", "#20e3ff", "#c6ff3d", "#8a5cff"],
    "erde": ["#efe6d8", "#8c5a3c", "#c98b4f", "#4f3b2b", "#a3a380"],
    "terrakotta": ["#f3e9dc", "#c8553d", "#f28f3b", "#588b8b", "#2f2d2e"],
    "nacht": ["#0f1020", "#2c2f5b", "#e0e1f5", "#f2c14e", "#5b6ee1"],
    "mint": ["#f7fff7", "#2ec4b6", "#cbf3f0", "#ff9f1c", "#1a535c"],
    "herbst": ["#f4ede1", "#9e2a2b", "#e09f3e", "#540b0e", "#335c67"],
    "eis": ["#f8fbff", "#bde0fe", "#a2d2ff", "#5a7d9a", "#22333b"],
    "candy": ["#fff5fb", "#ff99c8", "#fcf6bd", "#d0f4de", "#a9def9"],
    "mono": ["#f5f5f2", "#1a1a1a", "#555555", "#999999", "#d0d0d0"],
}


@dataclass(frozen=True)
class Color:
    """RGBA colour; r, g, b in 0–255, a in 0–1."""
    r: float
    g: float
    b: float
    a: float = 1.0

    @property
    def hex(self) -> str:
        return "#{:02x}{:02x}{:02x}".format(*(int(round(max(0, min(255, v)))) for v in (self.r, self.g, self.b)))

    @property
    def rgba(self) -> tuple[int, int, int, int]:
        return (*(int(round(max(0, min(255, v)))) for v in (self.r, self.g, self.b)),
                int(round(max(0, min(1, self.a)) * 255)))

    def alpha(self, a: float) -> "Color":
        """Same colour with a new alpha (0–1)."""
        return Color(self.r, self.g, self.b, a)

    def lighter(self, amount: float = 0.2) -> "Color":
        return lerp_color(self, Color(255, 255, 255, self.a), amount)

    def darker(self, amount: float = 0.2) -> "Color":
        return lerp_color(self, Color(0, 0, 0, self.a), amount)

    def __str__(self):
        return self.hex


def _parse_hex(s: str) -> Color:
    h = s.lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    if len(h) not in (6, 8):
        raise ValueError(f"Ungültige Farbe: {s!r}")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return Color(r, g, b, a)


def to_color(args, mode: str = "rgb") -> Color:
    """Accepts the many p5-style colour forms:
    gray | gray, alpha | r, g, b | r, g, b, a | '#hex' | 'name' | Color | (r, g, b[, a]).
    In RGB mode alpha is 0–255 (like p5); in HSB mode h 0–360, s/b 0–100, alpha 0–1."""
    if len(args) == 1:
        v = args[0]
        if isinstance(v, Color):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            if s.startswith("#"):
                return _parse_hex(s)
            if s in CSS_COLORS:
                return _parse_hex(CSS_COLORS[s])
            raise ValueError(f"Unbekannte Farbe: {v!r}")
        if isinstance(v, (tuple, list)):
            return to_color(tuple(v), mode)
        args = (v,)
    nums = [float(x) for x in args]
    if mode == "hsb":
        if len(nums) == 1:
            return Color(nums[0] * 2.55, nums[0] * 2.55, nums[0] * 2.55)
        h, s, b = nums[0], nums[1] if len(nums) > 1 else 100, nums[2] if len(nums) > 2 else 100
        a = nums[3] if len(nums) > 3 else 1.0
        r, g, bb = colorsys.hsv_to_rgb((h % 360) / 360, s / 100, b / 100)
        return Color(r * 255, g * 255, bb * 255, a)
    if len(nums) == 1:
        return Color(nums[0], nums[0], nums[0])
    if len(nums) == 2:
        return Color(nums[0], nums[0], nums[0], nums[1] / 255)
    if len(nums) == 3:
        return Color(*nums)
    return Color(nums[0], nums[1], nums[2], nums[3] / 255)


def lerp_color(c1, c2, t: float) -> Color:
    a, b = to_color((c1,)), to_color((c2,))
    return Color(a.r + (b.r - a.r) * t, a.g + (b.g - a.g) * t,
                 a.b + (b.b - a.b) * t, a.a + (b.a - a.a) * t)


def hsb(h: float, s: float = 100, b: float = 100, a: float = 1.0) -> Color:
    """Colour from hue (0–360), saturation and brightness (0–100), alpha (0–1)."""
    return to_color((h, s, b, a), "hsb")


def color_ramp(colors, t: float) -> Color:
    """Sample a smooth colour ramp through a list of colours at t (0–1)."""
    cols = [to_color((c,)) for c in colors]
    if len(cols) == 1:
        return cols[0]
    t = max(0.0, min(1.0, t)) * (len(cols) - 1)
    i = min(int(t), len(cols) - 2)
    return lerp_color(cols[i], cols[i + 1], t - i)


class Gradient:
    """Linear or radial gradient usable as fill() or stroke() paint."""

    def __init__(self, kind: str, coords: tuple, stops):
        self.kind = kind
        self.coords = coords
        stops = list(stops)
        if len(stops) < 1:
            raise ValueError("Ein Verlauf braucht mindestens eine Farbe")

        def is_stop(s):  # (offset, colour) pair
            return (isinstance(s, (tuple, list)) and len(s) == 2
                    and isinstance(s[0], (int, float)) and not isinstance(s[1], (int, float)))

        if not all(is_stop(s) for s in stops):  # plain colours → evenly spaced
            n = len(stops)
            stops = [(i / max(1, n - 1), c) for i, c in enumerate(stops)]
        self.stops = sorted(((float(o), to_color((c,))) for o, c in stops), key=lambda s: s[0])

    def color_at(self, t: float) -> Color:
        st = self.stops
        if t <= st[0][0]:
            return st[0][1]
        for (o0, c0), (o1, c1) in zip(st, st[1:]):
            if t <= o1:
                return lerp_color(c0, c1, (t - o0) / (o1 - o0) if o1 > o0 else 0)
        return st[-1][1]

    def average(self) -> Color:
        cs = [c for _, c in self.stops]
        n = len(cs)
        return Color(sum(c.r for c in cs) / n, sum(c.g for c in cs) / n,
                     sum(c.b for c in cs) / n, sum(c.a for c in cs) / n)
