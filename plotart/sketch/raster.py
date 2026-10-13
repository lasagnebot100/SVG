"""Raster images in sketches: load, inspect pixels, filters, dithering, built-in sample images.

Needs Pillow; numpy makes `pixels` and several filters available/faster.
"""
from __future__ import annotations

import math
import random

from .color import Color, to_color
from .data import SAMPLE_PREFIX, DataError, resolve

FILTERS = ["blur", "sharpen", "edges", "emboss", "gray", "invert", "posterize", "threshold", "contrast",
           "brightness", "saturation", "pixelate", "grain", "dither", "sepia", "levels"]


def _pil():
    try:
        from PIL import Image
        return Image
    except ImportError as exc:  # pragma: no cover
        raise DataError("Für Bilder wird Pillow benötigt: pip install Pillow") from exc


class Img:
    """Raster image. Coordinates in pixels, (0, 0) = top left.

    img.width, img.height · img.get(x, y) → Color · img.brightness(x, y) → 0…1
    img.sample(u, v) (0…1) · img.pixels → numpy array H×W×4 (0…1)
    img.filter("blur", 3) · img.resize(w) · img.crop(x, y, w, h) · img.dither()
    """

    def __init__(self, pil_image):
        self._pil = pil_image.convert("RGBA")
        self._luma = None

    # ------------------------------------------------------------- basics
    @property
    def width(self) -> int:
        return self._pil.width

    @property
    def height(self) -> int:
        return self._pil.height

    @property
    def size(self):
        return self._pil.size

    def __repr__(self):
        return f"Img({self.width}×{self.height})"

    def copy(self) -> "Img":
        return Img(self._pil.copy())

    def to_pil(self):
        return self._pil.copy()

    def save(self, fp, format=None):
        self._pil.save(fp, format=format)

    # ------------------------------------------------------------- pixel access
    def _xy(self, x, y):
        return (min(self.width - 1, max(0, int(x))), min(self.height - 1, max(0, int(y))))

    def get(self, x, y) -> Color:
        """Farbe des Pixels (x, y)."""
        r, g, b, a = self._pil.getpixel(self._xy(x, y))
        return Color(r, g, b, a / 255)

    def set(self, x, y, *c):
        """Pixel setzen (langsam – für viele Pixel lieber img.pixels verwenden)."""
        col = to_color(c)
        self._pil.putpixel(self._xy(x, y), col.rgba)
        self._luma = None

    def brightness(self, x, y) -> float:
        """Helligkeit 0 (schwarz) … 1 (weiß) an (x, y)."""
        if self._luma is None:
            self._luma = self._pil.convert("L")
        return self._luma.getpixel(self._xy(x, y)) / 255

    def sample(self, u, v) -> Color:
        """Farbe an relativer Position u, v (0 … 1)."""
        return self.get(u * (self.width - 1), v * (self.height - 1))

    def brightness_at(self, u, v) -> float:
        """Helligkeit an relativer Position u, v (0 … 1)."""
        return self.brightness(u * (self.width - 1), v * (self.height - 1))

    @property
    def pixels(self):
        """numpy-Array H × W × 4 mit Werten 0 … 1 (Kopie; zurückschreiben mit set_pixels)."""
        import numpy as np
        return np.asarray(self._pil, dtype=np.float32) / 255.0

    def set_pixels(self, arr) -> "Img":
        """Pixel aus einem numpy-Array (H×W, H×W×3 oder H×W×4; 0 … 1 oder 0 … 255) übernehmen."""
        from .png import to_png
        import io
        data, _, _ = to_png(arr)
        self._pil = _pil().open(io.BytesIO(data)).convert("RGBA")
        self._luma = None
        return self

    def grid(self, cols, rows=None) -> list[list[float]]:
        """Mittlere Helligkeit pro Rasterzelle: grid[zeile][spalte] (0 … 1)."""
        rows = rows or max(1, round(cols * self.height / self.width))
        small = self._pil.convert("L").resize((cols, rows), _pil().BOX)
        return [[small.getpixel((c, r)) / 255 for c in range(cols)] for r in range(rows)]

    # ------------------------------------------------------------- transforms
    def resize(self, w, h=None, smooth=True) -> "Img":
        """Neue Größe (h optional: Seitenverhältnis bleibt)."""
        h = h or max(1, round(w * self.height / self.width))
        return Img(self._pil.resize((int(w), int(h)), _pil().LANCZOS if smooth else _pil().NEAREST))

    def crop(self, x, y, w, h) -> "Img":
        return Img(self._pil.crop((int(x), int(y), int(x + w), int(y + h))))

    def rotate(self, degrees, expand=True) -> "Img":
        return Img(self._pil.rotate(-degrees, resample=_pil().BICUBIC, expand=expand))

    def flip(self, horizontal=True) -> "Img":
        from PIL import ImageOps
        return Img(ImageOps.mirror(self._pil) if horizontal else ImageOps.flip(self._pil))

    # ------------------------------------------------------------- filters
    def filter(self, kind: str, amount=None, seed: int = 1) -> "Img":
        """Neues, gefiltertes Bild. Filter: blur, sharpen, edges, emboss, gray, invert, posterize,
        threshold, contrast, brightness, saturation, pixelate, grain, dither, sepia, levels."""
        return Img(apply_filter(self._pil, kind, amount, seed))

    def dither(self, levels: int = 2) -> "Img":
        """Floyd-Steinberg-Dithering in Graustufen (levels = Anzahl Töne)."""
        return self.filter("dither", levels)


def apply_filter(im, kind: str, amount=None, seed: int = 1):
    from PIL import ImageEnhance, ImageFilter, ImageOps
    Image = _pil()
    kind = str(kind).lower()
    alpha = im.getchannel("A")
    rgb = im.convert("RGB")
    if kind == "blur":
        out = rgb.filter(ImageFilter.GaussianBlur(amount if amount is not None else 2))
        alpha = alpha.filter(ImageFilter.GaussianBlur(amount if amount is not None else 2))
    elif kind == "sharpen":
        out = rgb.filter(ImageFilter.UnsharpMask(radius=amount or 2, percent=160, threshold=2))
    elif kind == "edges":
        out = ImageOps.invert(rgb.convert("L").filter(ImageFilter.FIND_EDGES)).convert("RGB") \
            if amount != "raw" else rgb.filter(ImageFilter.FIND_EDGES)
    elif kind == "emboss":
        out = rgb.filter(ImageFilter.EMBOSS)
    elif kind in ("gray", "grey", "grau"):
        out = rgb.convert("L").convert("RGB")
    elif kind == "invert":
        out = ImageOps.invert(rgb)
    elif kind == "posterize":
        levels = max(2, int(amount or 4))
        bits = max(1, min(8, math.ceil(math.log2(levels))))
        out = ImageOps.posterize(rgb, bits)
    elif kind == "threshold":
        t = 0.5 if amount is None else float(amount)
        out = rgb.convert("L").point(lambda v: 255 if v >= t * 255 else 0).convert("RGB")
    elif kind == "contrast":
        out = ImageEnhance.Contrast(rgb).enhance(1.5 if amount is None else float(amount))
    elif kind == "brightness":
        out = ImageEnhance.Brightness(rgb).enhance(1.2 if amount is None else float(amount))
    elif kind == "saturation":
        out = ImageEnhance.Color(rgb).enhance(1.5 if amount is None else float(amount))
    elif kind == "pixelate":
        n = max(1, int(amount or 8))
        small = rgb.resize((max(1, rgb.width // n), max(1, rgb.height // n)), Image.BOX)
        out = small.resize(rgb.size, Image.NEAREST)
        alpha = alpha.resize(small.size, Image.BOX).resize(rgb.size, Image.NEAREST)
    elif kind == "grain":
        out = _grain(rgb, 0.12 if amount is None else float(amount), seed)
    elif kind == "dither":
        out = _dither(rgb, int(amount or 2))
    elif kind == "sepia":
        g = rgb.convert("L")
        out = ImageOps.colorize(g, (40, 26, 13), (255, 240, 205))
    elif kind == "levels":
        lo, hi = amount if isinstance(amount, (tuple, list)) else (0.1, 0.9)
        out = rgb.point(lambda v: max(0, min(255, int((v / 255 - lo) / max(1e-6, hi - lo) * 255))))
    else:
        raise DataError(f"Unbekannter Filter '{kind}'. Möglich: {', '.join(FILTERS)}")
    out = out.convert("RGBA")
    out.putalpha(alpha)
    return out


def _grain(rgb, amount, seed):
    try:
        import numpy as np
    except ImportError:                       # without numpy: Pillow noise (not seeded)
        from PIL import Image, ImageChops
        noise = Image.effect_noise(rgb.size, 255 * amount)          # centred on 128
        return ImageChops.add(rgb, Image.merge("RGB", [noise] * 3), 1.0, -128)
    arr = np.asarray(rgb, dtype=np.float32)
    noise = np.random.default_rng(seed).normal(0, 255 * amount, arr.shape[:2])[..., None]
    from PIL import Image
    return Image.fromarray(np.clip(arr + noise, 0, 255).astype(np.uint8), "RGB")


def _dither(rgb, levels):
    """Floyd–Steinberg error diffusion (numpy row loop; pure Python fallback via Pillow)."""
    from PIL import Image
    levels = max(2, levels)
    gray = rgb.convert("L")
    if levels == 2:
        return gray.convert("1").convert("RGB")       # Pillow's built-in Floyd–Steinberg
    try:
        import numpy as np
    except ImportError:
        pal = Image.new("P", (1, 1))
        steps = [round(i * 255 / (levels - 1)) for i in range(levels)]
        pal.putpalette([v for s in steps for v in (s, s, s)] + [0] * (768 - 3 * levels))
        return gray.convert("RGB").quantize(palette=pal, dither=Image.Dither.FLOYDSTEINBERG).convert("RGB")
    a = np.asarray(gray, dtype=np.float32) / 255
    h, w = a.shape
    q = levels - 1
    for y in range(h):
        row = a[y]
        for x in range(w):
            old = row[x]
            new = round(old * q) / q
            row[x] = new
            err = old - new
            if x + 1 < w:
                row[x + 1] += err * 7 / 16
            if y + 1 < h:
                nxt = a[y + 1]
                if x > 0:
                    nxt[x - 1] += err * 3 / 16
                nxt[x] += err * 5 / 16
                if x + 1 < w:
                    nxt[x + 1] += err / 16
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "L").convert("RGB")


# ------------------------------------------------------------------------ loading & creating
SAMPLE_IMAGES = ["kugeln", "verlauf", "portrait", "schrift"]


def load_image(path: str) -> Img:
    """Bild laden (PNG, JPG, …) – oder eingebaut: "beispiel:kugeln", "beispiel:portrait", …"""
    Image = _pil()
    p = str(path)
    if p.startswith(SAMPLE_PREFIX):
        return Img(sample_image(p[len(SAMPLE_PREFIX):]))
    im = Image.open(resolve(p))
    im.load()
    return Img(im)


def create_image(w, h, *c) -> Img:
    """Neues Bild w × h Pixel (optional mit Füllfarbe, sonst transparent)."""
    Image = _pil()
    col = to_color(c).rgba if c else (0, 0, 0, 0)
    return Img(Image.new("RGBA", (int(w), int(h)), col))


def sample_image(name: str, size: int = 512):
    """Procedural sample images (no files needed)."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    s = size
    if name == "verlauf":
        im = Image.linear_gradient("L").resize((s, s))           # dark at the top → bright at the bottom
        return im.convert("RGBA")
    if name == "kugeln":
        rng = random.Random(3)
        balls = sorted(((rng.uniform(0.15, 0.85), rng.uniform(0.15, 0.85), rng.uniform(0.07, 0.2))
                        for _ in range(7)), key=lambda b: b[2])
        try:
            import numpy as np
        except ImportError:
            np = None
            s = min(s, 192)                   # pure Python is slow – smaller image
        if np is not None:
            ys, xs = np.mgrid[0:s, 0:s].astype(np.float32)
            out = np.full((s, s), 30.0, np.float32)
            for cx, cy, r in balls:
                dx, dy = (xs - cx * s) / (r * s), (ys - cy * s) / (r * s)
                d2 = dx * dx + dy * dy
                nz = np.sqrt(np.clip(1 - d2, 0, 1))
                light = np.clip(-0.45 * dx - 0.55 * dy + 0.7 * nz, 0, 1) ** 0.9
                out = np.where(d2 <= 1, 40 + 215 * light, out)
            return Image.fromarray(out.astype(np.uint8), "L").convert("RGBA")
        im = Image.new("L", (s, s), 30)
        px = im.load()
        for y in range(s):
            for x in range(s):
                for cx, cy, r in balls:
                    dx, dy = (x - cx * s) / (r * s), (y - cy * s) / (r * s)
                    d2 = dx * dx + dy * dy
                    if d2 <= 1:
                        light = max(0.0, -0.45 * dx - 0.55 * dy + 0.7 * math.sqrt(1 - d2)) ** 0.9
                        px[x, y] = int(40 + 215 * light)
        return im.convert("RGBA")
    if name == "portrait":
        # abstract head silhouette with soft shading – handy for stippling / hatching demos
        im = Image.new("L", (s, s), 235)
        d = ImageDraw.Draw(im)
        d.ellipse((s * 0.3, s * 0.12, s * 0.7, s * 0.62), fill=70)            # head
        d.rectangle((s * 0.43, s * 0.55, s * 0.57, s * 0.72), fill=90)         # neck
        d.ellipse((s * 0.12, s * 0.66, s * 0.88, s * 1.25), fill=60)           # shoulders
        d.ellipse((s * 0.38, s * 0.18, s * 0.6, s * 0.4), fill=150)            # light on face
        im = im.filter(ImageFilter.GaussianBlur(s * 0.03))
        return im.convert("RGBA")
    if name == "schrift":
        im = Image.new("L", (s * 2, s), 245)
        d = ImageDraw.Draw(im)
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(s * 0.42))
        except OSError:
            font = ImageFont.load_default(size=int(s * 0.42))
        d.text((s, s / 2), "plotart", fill=20, font=font, anchor="mm")
        return im.convert("RGBA")
    raise DataError(f"Unbekanntes Beispielbild '{name}'. Möglich: "
                    + ", ".join(SAMPLE_PREFIX + n for n in SAMPLE_IMAGES))
