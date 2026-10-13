"""2D geometry helpers: hatching (pure Python) and boolean operations via shapely.

shapely (https://shapely.readthedocs.io) is optional – `pip install shapely`; in the
browser version it is loaded automatically. Shapes can be point lists
[(x, y), …], lists of such rings (with holes), or shapely geometries.
"""
from __future__ import annotations

import math


class GeometryError(Exception):
    pass


def _shapely():
    try:
        import shapely
        from shapely import geometry
        return shapely, geometry
    except ImportError:
        raise GeometryError("Für diese Funktion wird shapely gebraucht: pip install shapely "
                            "(https://shapely.readthedocs.io)") from None


def _is_point(p) -> bool:
    return isinstance(p, (tuple, list)) and len(p) >= 2 and all(isinstance(v, (int, float)) for v in p[:2])


def to_geometry(shape):
    """Point list / list of rings / shapely geometry → shapely geometry."""
    shapely, g = _shapely()
    if hasattr(shape, "geom_type"):
        return shape
    shape = list(shape)
    if shape and _is_point(shape[0]):
        return g.Polygon([tuple(p[:2]) for p in shape]).buffer(0)
    rings = [[tuple(p[:2]) for p in r] for r in shape if len(r) >= 3]
    if not rings:
        return g.GeometryCollection()
    out = g.Polygon(rings[0]).buffer(0)                  # even-odd: later rings toggle
    for r in rings[1:]:
        out = out.symmetric_difference(g.Polygon(r).buffer(0))
    return out


def rings_of(geom) -> list[tuple[list, bool]]:
    """shapely geometry → [(points, closed)] for drawing."""
    t = geom.geom_type
    if geom.is_empty:
        return []
    if t == "Polygon":
        return [(list(geom.exterior.coords)[:-1], True)] + [(list(i.coords)[:-1], True) for i in geom.interiors]
    if t in ("LineString", "LinearRing"):
        return [(list(geom.coords), t == "LinearRing")]
    if t == "Point":
        return []
    if hasattr(geom, "geoms"):
        out = []
        for part in geom.geoms:
            out += rings_of(part)
        return out
    return []


def union(*shapes):
    shapely, _ = _shapely()
    return shapely.union_all([to_geometry(s) for s in shapes])


def difference(a, b):
    return to_geometry(a).difference(to_geometry(b))


def intersection(a, b):
    return to_geometry(a).intersection(to_geometry(b))


def offset(shape, d, join="round", resolution=8):
    joins = {"round": 1, "mitre": 2, "miter": 2, "bevel": 3}
    return to_geometry(shape).buffer(float(d), quad_segs=int(resolution), join_style=joins.get(join, 1))


# ------------------------------------------------------------------------ hatching (pure Python)
def _rings_any(shape) -> list[list[tuple[float, float]]]:
    if hasattr(shape, "geom_type"):
        return [pts for pts, closed in rings_of(shape) if closed and len(pts) >= 3]
    shape = list(shape)
    if shape and _is_point(shape[0]):
        return [[tuple(p[:2]) for p in shape]]
    return [[tuple(p[:2]) for p in r] for r in shape if len(r) >= 3]


def hatch_lines(shape, spacing: float, angle: float = 0.0, offset_: float = 0.0) -> list:
    """Parallel lines filling a shape (even-odd, holes respected) → [((x1, y1), (x2, y2)), …]."""
    rings = _rings_any(shape)
    if not rings or spacing <= 0:
        return []
    c, s = math.cos(-angle), math.sin(-angle)
    rot = [[(x * c - y * s, x * s + y * c) for x, y in r] for r in rings]   # rotate so hatching is horizontal
    ys = [p[1] for r in rot for p in r]
    y0, y1 = min(ys), max(ys)
    edges = [(r[i], r[(i + 1) % len(r)]) for r in rot for i in range(len(r))]
    out = []
    y = y0 + (offset_ % spacing or spacing / 2)
    flip = False
    ci, si = math.cos(angle), math.sin(angle)
    while y < y1:
        xs = []
        for (ax, ay), (bx, by) in edges:
            if (ay <= y) != (by <= y):
                xs.append(ax + (y - ay) * (bx - ax) / (by - ay))
        xs.sort()
        segs = [(xs[k], xs[k + 1]) for k in range(0, len(xs) - 1, 2)]
        if flip:                                     # boustrophedon: less pen travel
            segs = [(b, a) for a, b in reversed(segs)]
        for a, b in segs:
            out.append(((a * ci - y * si, a * si + y * ci), (b * ci - y * si, b * si + y * ci)))
        flip = not flip
        y += spacing
    return out
