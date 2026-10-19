"""Minimal TrueType reader: glyph outlines as polylines (no dependencies).

Supports .ttf and .ttc (first font), cmap formats 4 and 12, simple and composite glyphs.
CFF-based .otf fonts are not supported (no 'glyf' table).
"""
from __future__ import annotations

import os
import struct
import sys
from functools import lru_cache
from pathlib import Path

from .data import DataError, resolve

FONT_DIRS = [
    "/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
    os.path.expanduser("~/.local/share/fonts"),
    "/System/Library/Fonts", "/System/Library/Fonts/Supplemental", "/Library/Fonts",
    os.path.expanduser("~/Library/Fonts"),
    os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"),  # per-user fonts (Windows)
]
DEFAULT_FONTS = ["DejaVuSans", "Arial", "Helvetica", "LiberationSans-Regular", "NotoSans-Regular",
                 "Roboto-Regular", "Verdana", "SegoeUI", "FreeSans"]
# Windows file names in brackets: arialbd = Arial Bold, verdanab = Verdana Bold, segoeuib = Segoe UI Bold
DEFAULT_BOLD_FONTS = ["DejaVuSans-Bold", "arialbd", "Arial Bold", "LiberationSans-Bold", "NotoSans-Bold",
                      "Roboto-Bold", "verdanab", "segoeuib", "FreeSansBold"]
# Portable names that pick a font available on this system
FONT_ALIASES = {"sans": DEFAULT_FONTS, "sans-bold": DEFAULT_BOLD_FONTS}


@lru_cache(maxsize=1)
def _font_index() -> dict[str, str]:
    """stem (lower case) → path for all .ttf/.ttc files in the usual folders."""
    idx: dict[str, str] = {}
    for base in FONT_DIRS:
        if not os.path.isdir(base):
            continue
        for root, _, files in os.walk(base):
            for f in files:
                if f.lower().endswith((".ttf", ".ttc")):
                    idx.setdefault(Path(f).stem.lower(), os.path.join(root, f))
    return idx


def find_font(name: str | None = None) -> str:
    """Path of a font: a file path, a font name such as "DejaVuSans-Bold"/"Arial", "sans"/"sans-bold"
    (whatever this system has) or None (default)."""
    if name and name.strip().lower() in FONT_ALIASES:
        idx = _font_index()
        for cand in FONT_ALIASES[name.strip().lower()]:
            if cand.lower() in idx:
                return idx[cand.lower()]
        name = None                                  # nothing suitable installed → default font
    if name:
        p = Path(os.path.expanduser(name))
        if p.suffix.lower() in (".ttf", ".ttc", ".otf"):
            try:
                return str(resolve(str(p)))
            except DataError:
                pass
        idx = _font_index()
        key = Path(name).stem.lower().replace(" ", "")
        if key in idx:
            return idx[key]
        matches = sorted((k for k in idx if key in k.replace(" ", "")), key=len)
        if matches:
            return idx[matches[0]]
        raise DataError(f"Schrift '{name}' nicht gefunden. Gib einen Pfad zu einer .ttf-Datei an "
                        f"oder lege sie in den Ordner daten/.")
    idx = _font_index()
    for cand in DEFAULT_FONTS:
        if cand.lower() in idx:
            return idx[cand.lower()]
    if idx:
        return next(iter(sorted(idx.values())))
    raise DataError("Keine TrueType-Schrift gefunden – bitte eine .ttf-Datei angeben.")


class Font:
    def __init__(self, path: str):
        self.path = path
        data = Path(path).read_bytes()
        off = 0
        if data[:4] == b"ttcf":
            off = struct.unpack(">I", data[12:16])[0]
        self.data = data
        n = struct.unpack(">H", data[off + 4:off + 6])[0]
        self.tables = {}
        for i in range(n):
            rec = off + 12 + i * 16
            tag = data[rec:rec + 4].decode("latin-1")
            t_off, t_len = struct.unpack(">II", data[rec + 8:rec + 16])
            self.tables[tag] = (t_off, t_len)
        if "glyf" not in self.tables:
            raise DataError(f"{os.path.basename(path)}: nur TrueType-Schriften (glyf) werden unterstützt, "
                            "keine CFF/OpenType-Schriften.")
        head = self.tables["head"][0]
        self.units = struct.unpack(">H", data[head + 18:head + 20])[0]
        self.loc_long = struct.unpack(">h", data[head + 50:head + 52])[0] == 1
        self.num_glyphs = struct.unpack(">H", data[self.tables["maxp"][0] + 4:self.tables["maxp"][0] + 6])[0]
        hhea = self.tables["hhea"][0]
        self.ascent, self.descent = struct.unpack(">hh", data[hhea + 4:hhea + 8])
        self.num_hmetrics = struct.unpack(">H", data[hhea + 34:hhea + 36])[0]
        self.cmap = self._read_cmap()
        self._cache: dict = {}

    # ------------------------------------------------------------- tables
    def _u16(self, o):
        return struct.unpack(">H", self.data[o:o + 2])[0]

    def _read_cmap(self) -> dict[int, int]:
        d = self.data
        base = self.tables["cmap"][0]
        n = self._u16(base + 2)
        best = None
        for i in range(n):
            pid, eid, off = struct.unpack(">HHI", d[base + 4 + i * 8:base + 12 + i * 8])
            fmt = self._u16(base + off)
            score = {(3, 10): 4, (0, 4): 4, (3, 1): 3, (0, 3): 3}.get((pid, eid), 1 if pid == 0 else 0)
            if fmt in (4, 12) and (best is None or score > best[0]):
                best = (score, base + off, fmt)
        if best is None:
            raise DataError("Schrift ohne nutzbare Zeichentabelle (cmap)")
        _, o, fmt = best
        cmap: dict[int, int] = {}
        if fmt == 4:
            segx2 = self._u16(o + 6)
            ends = o + 14
            starts = ends + segx2 + 2
            deltas = starts + segx2
            ranges = deltas + segx2
            for s in range(segx2 // 2):
                end, start = self._u16(ends + 2 * s), self._u16(starts + 2 * s)
                delta = struct.unpack(">h", d[deltas + 2 * s:deltas + 2 * s + 2])[0]
                ro = self._u16(ranges + 2 * s)
                for c in range(start, end + 1):
                    if c == 0xFFFF:
                        continue
                    if ro == 0:
                        g = (c + delta) & 0xFFFF
                    else:
                        g = self._u16(ranges + 2 * s + ro + 2 * (c - start))
                        g = (g + delta) & 0xFFFF if g else 0
                    if g:
                        cmap[c] = g
        else:
            n_groups = struct.unpack(">I", d[o + 12:o + 16])[0]
            for k in range(n_groups):
                sc, ec, sg = struct.unpack(">III", d[o + 16 + 12 * k:o + 28 + 12 * k])
                for c in range(sc, ec + 1):
                    cmap[c] = sg + c - sc
        return cmap

    def advance(self, gid: int) -> int:
        hmtx = self.tables["hmtx"][0]
        i = min(gid, self.num_hmetrics - 1)
        return self._u16(hmtx + 4 * i)

    def _glyph_range(self, gid):
        loca = self.tables["loca"][0]
        if self.loc_long:
            a, b = struct.unpack(">II", self.data[loca + 4 * gid:loca + 4 * gid + 8])
        else:
            a, b = (2 * v for v in struct.unpack(">HH", self.data[loca + 2 * gid:loca + 2 * gid + 4]))
        return a, b

    # ------------------------------------------------------------- outlines
    def contours(self, gid: int, depth: int = 0) -> list[list[tuple[float, float, bool]]]:
        """Contours as lists of (x, y, on_curve) in font units (y up)."""
        if gid in self._cache:
            return self._cache[gid]
        a, b = self._glyph_range(gid)
        if b <= a or depth > 8:
            return []
        d = self.data
        o = self.tables["glyf"][0] + a
        n_contours = struct.unpack(">h", d[o:o + 2])[0]
        p = o + 10
        out: list = []
        if n_contours >= 0:
            ends = list(struct.unpack(f">{n_contours}H", d[p:p + 2 * n_contours]))
            p += 2 * n_contours
            n_pts = ends[-1] + 1 if ends else 0
            ilen = self._u16(p)
            p += 2 + ilen
            flags = []
            while len(flags) < n_pts:
                f = d[p]
                p += 1
                flags.append(f)
                if f & 8:
                    rep = d[p]
                    p += 1
                    flags.extend([f] * rep)
            coords = []
            for axis in (0, 1):
                short, same = (2, 16) if axis == 0 else (4, 32)
                val, vals = 0, []
                for f in flags[:n_pts]:
                    if f & short:
                        dv = d[p]
                        p += 1
                        val += dv if f & same else -dv
                    elif not f & same:
                        val += struct.unpack(">h", d[p:p + 2])[0]
                        p += 2
                    vals.append(val)
                coords.append(vals)
            start = 0
            for e in ends:
                out.append([(coords[0][i], coords[1][i], bool(flags[i] & 1)) for i in range(start, e + 1)])
                start = e + 1
        else:                                   # composite glyph
            more = True
            while more:
                flags, comp = struct.unpack(">HH", d[p:p + 4])
                p += 4
                if flags & 1:
                    dx, dy = struct.unpack(">hh", d[p:p + 4])
                    p += 4
                else:
                    dx, dy = struct.unpack(">bb", d[p:p + 2])
                    p += 2
                xx, xy, yx, yy = 1.0, 0.0, 0.0, 1.0

                def f2d14(o_):
                    return struct.unpack(">h", d[o_:o_ + 2])[0] / 16384
                if flags & 8:
                    xx = yy = f2d14(p)
                    p += 2
                elif flags & 0x40:
                    xx, yy = f2d14(p), f2d14(p + 2)
                    p += 4
                elif flags & 0x80:
                    xx, xy, yx, yy = f2d14(p), f2d14(p + 2), f2d14(p + 4), f2d14(p + 6)
                    p += 8
                if not flags & 2:
                    dx = dy = 0          # point matching – rare, ignored
                for c in self.contours(comp, depth + 1):
                    out.append([(x * xx + y * yx + dx, x * xy + y * yy + dy, on) for x, y, on in c])
                more = bool(flags & 0x20)
        self._cache[gid] = out
        return out


def _flatten_contour(c, steps=6):
    """Quadratic TrueType contour → polyline (implied on-curve points handled)."""
    pts = list(c)
    if not pts:
        return []
    if not pts[0][2]:                       # start on an on-curve point
        k = next((i for i, p in enumerate(pts) if p[2]), None)
        if k is None:
            a, b = pts[0], pts[1] if len(pts) > 1 else pts[0]
            pts.insert(0, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, True))
        else:
            pts = pts[k:] + pts[:k]
    out = [pts[0][:2]]
    n = len(pts)
    i = 1
    prev = pts[0]
    while i <= n:
        p = pts[i % n]
        if p[2]:
            out.append(p[:2])
            prev = p
            i += 1
            continue
        nxt = pts[(i + 1) % n]
        end = nxt[:2] if nxt[2] else ((p[0] + nxt[0]) / 2, (p[1] + nxt[1]) / 2)
        for s in range(1, steps + 1):
            t = s / steps
            out.append(((1 - t) ** 2 * prev[0] + 2 * (1 - t) * t * p[0] + t * t * end[0],
                        (1 - t) ** 2 * prev[1] + 2 * (1 - t) * t * p[1] + t * t * end[1]))
        prev = (end[0], end[1], True)
        i += 2 if nxt[2] else 1
    if len(out) > 1 and out[-1] == out[0]:
        out.pop()
    return out


@lru_cache(maxsize=16)
def get_font(name: str | None = None) -> Font:
    return Font(find_font(name))


def text_paths(s: str, x: float, y: float, size: float, font: str | None = None, align: str = "left",
               line_height: float = 1.25, steps: int = 6) -> list[list[tuple[float, float]]]:
    """Text as closed polylines (outlines of the letters); (x, y) = baseline of the first line."""
    f = get_font(font)
    k = size / f.units
    out = []
    for li, line in enumerate(str(s).split("\n")):
        gids = [f.cmap.get(ord(ch), 0) for ch in line]
        width = sum(f.advance(g) for g in gids) * k
        cx = x - (width / 2 if align == "center" else width if align == "right" else 0)
        by = y + li * size * line_height
        for g in gids:
            for c in f.contours(g):
                poly = _flatten_contour(c, steps)
                if len(poly) >= 3:
                    out.append([(cx + px * k, by - py * k) for px, py in poly])
            cx += f.advance(g) * k
    return out


def text_width(s: str, size: float, font: str | None = None) -> float:
    f = get_font(font)
    return max((sum(f.advance(f.cmap.get(ord(ch), 0)) for ch in line) for line in str(s).split("\n")),
               default=0) * size / f.units


if __name__ == "__main__":  # pragma: no cover
    print(find_font(sys.argv[1] if len(sys.argv) > 1 else None))
