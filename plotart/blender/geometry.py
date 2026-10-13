"""Mesh helpers (pure Python): flat stroke ribbons and extruded polygons.

All functions return (verts, faces) with verts as (x, y, z) and faces as index tuples.
"""
from __future__ import annotations

import math


def _disc(cx, cy, r, z, segments):
    return [(cx + r * math.cos(math.tau * i / segments), cy + r * math.sin(math.tau * i / segments), z)
            for i in range(segments)]


def ribbon(points, closed: bool, width: float, z: float, round_joins: bool = True,
           canvas_size: float = 10.0):
    """A stroke as flat geometry: one quad per segment + round joins/caps (discs).

    The joins make thick lines look like p5's round joins without self-intersection
    trouble; `canvas_size` only controls how many segments the discs get.
    """
    pts = [(float(p[0]), float(p[1])) for p in points]
    # drop consecutive duplicates
    clean = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, clean[-1]) > 1e-12:
            clean.append(p)
    pts = clean
    if closed and len(pts) > 2 and math.dist(pts[0], pts[-1]) < 1e-12:
        pts.pop()
    h = width / 2
    verts: list = []
    faces: list = []
    if len(pts) == 1:
        seg = 8
        verts.extend(_disc(pts[0][0], pts[0][1], h, z, seg))
        faces.append(tuple(range(seg)))
        return verts, faces
    pairs = list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if closed and len(pts) > 2 else [])
    for (ax, ay), (bx, by) in pairs:
        dx, dy = bx - ax, by - ay
        ln = math.hypot(dx, dy)
        nx, ny = -dy / ln * h, dx / ln * h
        i = len(verts)
        verts.extend([(ax + nx, ay + ny, z), (bx + nx, by + ny, z), (bx - nx, by - ny, z), (ax - nx, ay - ny, z)])
        faces.append((i, i + 1, i + 2, i + 3))
    if round_joins and width > canvas_size * 0.0015:
        seg = max(6, min(24, int(width / canvas_size * 600)))
        for (x, y) in pts:                    # joins and round caps
            i = len(verts)
            verts.extend(_disc(x, y, h, z, seg))
            faces.append(tuple(range(i, i + seg)))
    return verts, faces


def _signed_area(poly) -> float:
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1])) / 2


def flat_polygon(poly, z: float):
    """One n-gon (counter-clockwise, so the normal points up)."""
    pts = [(float(p[0]), float(p[1])) for p in poly]
    if _signed_area(pts) < 0:
        pts.reverse()
    return [(x, y, z) for x, y in pts], [tuple(range(len(pts)))]


def extruded_polygon(poly, z0: float, z1: float):
    """Closed prism: bottom at z0, top at z1, side walls."""
    pts = [(float(p[0]), float(p[1])) for p in poly]
    if _signed_area(pts) < 0:
        pts.reverse()
    n = len(pts)
    verts = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return verts, faces


class MeshBuffer:
    """Collects many small meshes into one (with a material index per face)."""

    def __init__(self):
        self.verts: list = []
        self.faces: list = []
        self.mats: list = []

    def add(self, verts, faces, mat: int):
        off = len(self.verts)
        self.verts.extend(verts)
        for f in faces:
            self.faces.append(tuple(i + off for i in f))
            self.mats.append(mat)

    def __bool__(self):
        return bool(self.faces)
