"""Exports of a finished sketch: PNG raster and pen-plotter SVG."""
from __future__ import annotations

import io
import math

from ..core import Drawing
from .color import Color, Gradient
from .core import IDENTITY, Sketch, mat_apply
from .flatten import _scale_of, flatten
from .render_svg import render_svg

MM_PER_PX = 25.4 / 96


def px_per_unit(sk: Sketch, dpi: float = 300) -> float:
    """Default raster scale: 1 px per px, or `dpi` for millimetre sketches."""
    return dpi / 25.4 if sk.unit == "mm" else 1.0


# ---------------------------------------------------------------------------- PNG
def render_png(sk: Sketch, scale: float | None = None, engine: str = "auto") -> bytes:
    """Rasterise the sketch. scale = output pixels per sketch unit.

    engine: "auto" (cairosvg if installed, else Pillow), "cairo" or "pillow".
    """
    scale = scale or px_per_unit(sk)
    W, H = max(1, round(sk.width * scale)), max(1, round(sk.height * scale))
    if engine in ("auto", "cairo"):
        try:
            import cairosvg
            return cairosvg.svg2png(bytestring=render_svg(sk).encode(), output_width=W, output_height=H)
        except ImportError:
            if engine == "cairo":
                raise
    return _render_pillow(sk, scale, W, H)


def _rgba(c: Color):
    return c.rgba


def _gradient_image(g: Gradient, m, S, box, Image):
    """Gradient pixels for the bounding box (needs numpy; else flat average colour)."""
    x0, y0, x1, y1 = box
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    try:
        import numpy as np
    except ImportError:
        return Image.new("RGBA", (w, h), _rgba(g.average()))
    ys, xs = np.mgrid[y0:y0 + h, x0:x0 + w].astype(float) + 0.5
    if g.kind == "linear":
        ax, ay = mat_apply(m, g.coords[0], g.coords[1])
        bx, by = mat_apply(m, g.coords[2], g.coords[3])
        ax, ay, bx, by = ax * S, ay * S, bx * S, by * S
        dx, dy = bx - ax, by - ay
        t = ((xs - ax) * dx + (ys - ay) * dy) / max(dx * dx + dy * dy, 1e-9)
    else:
        cx, cy = mat_apply(m, g.coords[0], g.coords[1])
        r = g.coords[2] * _scale_of(m) * S
        t = np.hypot(xs - cx * S, ys - cy * S) / max(r, 1e-9)
    t = np.clip(t, 0, 1)
    offs = np.array([o for o, _ in g.stops])
    out = np.zeros((h, w, 4))
    for ch, attr in enumerate(("r", "g", "b")):
        out[..., ch] = np.interp(t, offs, [getattr(c, attr) for _, c in g.stops])
    out[..., 3] = np.interp(t, offs, [c.a * 255 for _, c in g.stops])
    return Image.fromarray(out.round().astype("uint8"), "RGBA")


class PillowCanvas:
    """Persistent raster canvas (Pillow, 2× supersampled). draw() adds items on top of
    what is already there – so animation frames can accumulate like in p5."""

    def __init__(self, width: float, height: float, scale: float, ss: int = 2):
        try:
            from PIL import Image, ImageChops
        except ImportError:
            raise ImportError("PNG-Export braucht Pillow: pip install Pillow") from None
        self.width, self.height = width, height
        self.W, self.H = max(1, round(width * scale)), max(1, round(height * scale))
        self.ss = ss
        self.S = scale * ss
        self.size = (self.W * ss, self.H * ss)
        self.img = Image.new("RGBA", self.size, (0, 0, 0, 0))
        self.ops = {"multiply": ImageChops.multiply, "screen": ImageChops.screen,
                    "darken": ImageChops.darker, "lighten": ImageChops.lighter,
                    "difference": ImageChops.difference, "plus-lighter": ImageChops.add}
        self.fonts: dict = {}
        self._solids: dict = {}

    def clear(self):
        from PIL import Image
        self.img = Image.new("RGBA", self.size, (0, 0, 0, 0))

    def _font(self, sz):
        from PIL import ImageFont
        sz = max(1, int(round(sz)))
        if sz not in self.fonts:
            f = None
            for name in ("DejaVuSans.ttf", "Arial.ttf", "Helvetica.ttc", "arial.ttf"):
                try:
                    f = ImageFont.truetype(name, sz)
                    break
                except OSError:
                    continue
            self.fonts[sz] = f or ImageFont.load_default(size=sz)
        return self.fonts[sz]

    def _draw_item(self, target, it, subs, ox, oy):
        """Draw one item onto `target`, whose top-left corner sits at (ox, oy) in the full image."""
        from PIL import Image, ImageChops, ImageDraw
        st, m = it.style, it.matrix or IDENTITY
        tsize = target.size
        draw = ImageDraw.Draw(target, "RGBA")
        if it.kind == "image":
            d = it.data
            pic = Image.open(io.BytesIO(d["png"])).convert("RGBA")
            if abs(m[1]) > 1e-9 or abs(m[2]) > 1e-9 or m[0] < 0 or m[3] < 0:
                self._draw_image_affine(target, pic, d, m, ox, oy)   # rotated / sheared / mirrored
                return
            x, y = mat_apply(m, d["x"], d["y"])
            w, h = max(1, round(d["w"] * m[0] * self.S)), max(1, round(d["h"] * m[3] * self.S))
            pic = pic.resize((w, h), Image.LANCZOS if d["smooth"] else Image.NEAREST)
            _paste_clipped(target, pic, round(x * self.S) - ox, round(y * self.S) - oy)
            return
        if it.kind == "text":
            d = it.data
            x, y = mat_apply(m, d["x"], d["y"])
            anchor = {"left": "l", "center": "m", "right": "r"}.get(st.text_align, "l") + \
                {"baseline": "s", "top": "a", "center": "m", "bottom": "d"}.get(st.text_valign, "s")
            paint = st.fill.average() if isinstance(st.fill, Gradient) else st.fill
            if paint is None:
                return
            fnt = self._font(st.text_size * _scale_of(m) * self.S)
            angle = math.degrees(math.atan2(m[1], m[0]))
            if abs(angle) < 0.05:
                draw.text((x * self.S - ox, y * self.S - oy), d["s"], fill=_rgba(paint), font=fnt, anchor=anchor)
                return
            # rotated text: draw on a tile centred on the anchor, rotate, composite
            l, t, r, b = fnt.getbbox(d["s"], anchor=anchor)
            half = int(math.hypot(max(abs(l), abs(r)), max(abs(t), abs(b)))) + 2
            tile = Image.new("RGBA", (2 * half, 2 * half), (0, 0, 0, 0))
            ImageDraw.Draw(tile).text((half, half), d["s"], fill=_rgba(paint), font=fnt, anchor=anchor)
            tile = tile.rotate(-angle, resample=Image.BICUBIC, center=(half, half))
            _paste_clipped(target, tile, round(x * self.S) - ox - half, round(y * self.S) - oy - half)
            return
        subs = [([(x - ox, y - oy) for x, y in pts], closed) for pts, closed in subs]
        if st.fill is not None:
            polys = [p for p, _ in subs if len(p) >= 3]   # open paths are filled too (like p5)
            if polys:
                if isinstance(st.fill, Gradient) or len(polys) > 1:
                    pb = _bbox_of([pt for p in polys for pt in p], 1, tsize)
                    if pb:
                        msize = (pb[2] - pb[0], pb[3] - pb[1])
                        mask = Image.new("1", msize, 0)
                        for p in polys:          # holes via even-odd (XOR)
                            one = Image.new("1", msize, 0)
                            ImageDraw.Draw(one).polygon([(x - pb[0], y - pb[1]) for x, y in p], fill=1)
                            mask = ImageChops.logical_xor(mask, one)
                        mask = mask.convert("L")
                        if isinstance(st.fill, Gradient):
                            absbox = (pb[0] + ox, pb[1] + oy, pb[2] + ox, pb[3] + oy)
                            fill_img = _gradient_image(st.fill, it.matrix or IDENTITY, self.S, absbox, Image)
                        else:
                            fill_img = Image.new("RGBA", msize, _rgba(st.fill))
                        fill_img.putalpha(ImageChops.multiply(fill_img.getchannel("A"), mask))
                        target.alpha_composite(fill_img, pb[:2])
                else:
                    draw.polygon(polys[0], fill=_rgba(st.fill))
        if st.stroke is not None and st.weight > 0:
            paint = st.stroke.average() if isinstance(st.stroke, Gradient) else st.stroke
            width = max(1, round(st.weight * _scale_of(m) * self.S))
            col = _rgba(paint)
            for pts, closed in subs:
                line = pts + [pts[0]] if closed else pts
                if len(line) == 1:
                    line = line * 2
                draw.line(line, fill=col, width=width, joint="curve")
                if not closed and st.cap == "round" and width >= 3:
                    r = width / 2
                    for px, py in (line[0], line[-1]):
                        draw.ellipse((px - r, py - r, px + r, py + r), fill=col)

    def _draw_image_affine(self, target, pic, d, m, ox, oy):
        """Full affine image drawing: image pixels → sketch units → matrix → device pixels."""
        from PIL import Image
        from .core import mat_mul
        iw, ih = pic.size
        place = (d["w"] / iw, 0, 0, d["h"] / ih, d["x"], d["y"])
        T = mat_mul((self.S, 0, 0, self.S, -ox, -oy), mat_mul(m, place))
        corners = [mat_apply(T, u, v) for u, v in ((0, 0), (iw, 0), (iw, ih), (0, ih))]
        box = _bbox_of(corners, 1, target.size)
        if box is None:
            return
        a, b, c, dd, e, f = mat_mul((1, 0, 0, 1, -box[0], -box[1]), T)
        det = a * dd - b * c
        if abs(det) < 1e-12:
            return
        inv = (dd / det, -c / det, (c * f - dd * e) / det, -b / det, a / det, (b * e - a * f) / det)
        out = pic.transform((box[2] - box[0], box[3] - box[1]), Image.AFFINE, inv,
                            resample=Image.BICUBIC if d["smooth"] else Image.NEAREST, fillcolor=(0, 0, 0, 0))
        target.alpha_composite(out, box[:2])

    def draw(self, items):
        from PIL import Image
        img, S, size = self.img, self.S, self.size
        for it in items:
            st = it.style
            m = it.matrix or IDENTITY
            if it.kind == "background" and isinstance(st.fill, Color) and st.blend in ("normal", "blend"):
                # fast path, e.g. background(0, 20) for trails: one composite of a cached solid
                rgba = st.fill.rgba
                if rgba[3] >= 255:
                    img.paste(rgba, (0, 0, *size))
                elif rgba[3] > 0:
                    solid = self._solids.get(rgba)
                    if solid is None:
                        solid = self._solids[rgba] = Image.new("RGBA", size, rgba)
                    img.alpha_composite(solid)
                continue
            subs = None
            if it.kind not in ("image", "text"):
                subs = flatten(it, self.width, self.height, tol=0.3, scale=S)
                if not subs:
                    continue
            op = self.ops.get(st.blend)
            if not op and not _translucent(it):
                self._draw_item(img, it, subs, 0, 0)     # opaque: direct drawing is exact
                continue
            # blend modes and transparency: draw the item on its own layer (only its bounding
            # box), then mix/composite it with what is below. Pillow's ImageDraw would
            # *replace* RGBA pixels instead of blending them.
            if subs is not None:
                pad = (st.weight * _scale_of(m) * S if st.stroke is not None else 0) + 2
                box = _bbox_of([pt for pts, _ in subs for pt in pts], pad, size)
            else:
                box = (0, 0, *size)
            if box is None:
                continue
            layer = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
            self._draw_item(layer, it, subs, box[0], box[1])
            region = img.crop(box)
            if op:
                mixed = op(region.convert("RGB"), layer.convert("RGB")).convert("RGBA")
                mixed.putalpha(layer.getchannel("A"))
                region.alpha_composite(mixed)
            else:
                region.alpha_composite(layer)
            img.paste(region, box[:2])

    def image(self):
        """Current canvas at output resolution (RGBA).

        Box-averaging the 2× supersampled canvas is the classic anti-aliasing filter and
        ~15× faster than Lanczos – it matters for animations (one call per frame).
        """
        from PIL import Image
        img = self.img.reduce(self.ss) if self.ss > 1 else self.img
        if img.size != (self.W, self.H):
            img = img.resize((self.W, self.H), Image.BILINEAR)
        return img


class CairoCanvas:
    """Same interface as PillowCanvas, rendering each batch exactly via cairosvg."""

    def __init__(self, sk: Sketch, scale: float):
        from PIL import Image
        self.sk = sk
        self.W, self.H = max(1, round(sk.width * scale)), max(1, round(sk.height * scale))
        self.img = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))

    def clear(self):
        from PIL import Image
        self.img = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))

    def draw(self, items):
        import cairosvg
        from PIL import Image
        png = cairosvg.svg2png(bytestring=render_svg(self.sk, items=items).encode(),
                               output_width=self.W, output_height=self.H)
        self.img.alpha_composite(Image.open(io.BytesIO(png)).convert("RGBA"))

    def image(self):
        return self.img.copy()


def make_canvas(sk: Sketch, scale: float, engine: str = "auto"):
    """Raster canvas for a sketch: cairosvg (exact) if available, else Pillow."""
    if engine in ("auto", "cairo"):
        try:
            import cairosvg  # noqa: F401
            return CairoCanvas(sk, scale)
        except ImportError:
            if engine == "cairo":
                raise
    return PillowCanvas(sk.width, sk.height, scale)


def _translucent(it) -> bool:
    """True if the item paints with partial alpha (needs real compositing)."""
    st = it.style
    if it.kind == "image":
        return False                      # images are already alpha-composited
    for paint in (st.fill, st.stroke):
        if isinstance(paint, Color) and paint.a < 0.999:
            return True
    return False


def _bbox_of(points, pad, limit):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x0 = max(0, int(min(xs) - pad))
    y0 = max(0, int(min(ys) - pad))
    x1 = min(limit[0], int(max(xs) + pad) + 1)
    y1 = min(limit[1], int(max(ys) + pad) + 1)
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def _render_pillow(sk: Sketch, scale: float, W: int, H: int) -> bytes:
    canvas = PillowCanvas(sk.width, sk.height, scale)
    canvas.draw(sk.items)
    buf = io.BytesIO()
    canvas.image().save(buf, format="PNG")
    return buf.getvalue()


def _paste_clipped(target, pic, x, y):
    """alpha_composite of `pic` at (x, y), cropped to the target on all sides."""
    l, t = max(0, -x), max(0, -y)
    r = min(pic.width, target.width - x)
    b = min(pic.height, target.height - y)
    if r > l and b > t:
        target.alpha_composite(pic.crop((l, t, r, b)), (max(0, x), max(0, y)))


# ---------------------------------------------------------------------------- plotter
def _opaque(paint) -> bool:
    if isinstance(paint, Gradient):
        return all(c.a >= 0.999 for _, c in paint.stops)
    return isinstance(paint, Color) and paint.a >= 0.999


def to_plotter(sk: Sketch, pen_width: float = 0.45, outline_fills: bool = True,
               optimize: bool = True, hidden_lines: bool = False) -> Drawing:
    """Stroke geometry as a plotter Drawing (mm), one layer per colour.

    Fills are not hatched – shapes without outline get their outline drawn
    (outline_fills). By default a plotter draws everything, overlaps included;
    hidden_lines=True removes lines covered by later opaque fills (3D, overlapping shapes).
    """
    f = 1.0 if sk.unit == "mm" else MM_PER_PX
    d = Drawing(sk.width * f, sk.height * f, margin=0, pen_width=pen_width)
    layers: dict[str, int] = {}
    occ = None
    if hidden_lines:
        from .occlusion import Occluder
        occ = Occluder(sk.width * f, sk.height * f)
    for it in sk.items:
        if it.kind == "background" and occ is not None and _opaque(it.style.fill) and it.style.blend in ("normal", "blend"):
            occ.clear()
        if it.kind in ("background", "image", "text"):
            continue
        st = it.style
        subs = None
        if occ is not None and _opaque(st.fill) and st.blend in ("normal", "blend"):
            subs = flatten(it, sk.width, sk.height, tol=0.05 / f, scale=f)
            occ.occlude([pts for pts, _ in subs], evenodd=bool(it.data.get("evenodd")))
        paint = st.stroke if st.stroke is not None and st.weight > 0 else (st.fill if outline_fills else None)
        if paint is None:
            continue
        if isinstance(paint, Gradient):
            paint = paint.average()
        if paint.a <= 0:
            continue
        layer = layers.setdefault(paint.hex, len(layers) + 1)
        for pts, closed in subs if subs is not None else flatten(it, sk.width, sk.height, tol=0.05 / f, scale=f):
            line = pts + [pts[0]] if closed else pts
            if occ is not None:
                occ.add_line(line, layer)
            else:
                d.add(line, layer)
    if occ is not None:
        for line, layer in occ.polylines():
            d.add(line, layer)
    d.colors = {layer: col for col, layer in layers.items()}
    d.clip_to_box()
    if optimize:
        d.optimize(merge_tol=max(0.02, pen_width * 0.1))
    return d
