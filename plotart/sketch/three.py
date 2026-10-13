"""3D in sketches (p5.js-WEBGL-like): primitives, camera, lights, flat shading.

3D shapes are projected onto the 2D canvas (painter's algorithm, depth-sorted) and
emitted as ordinary 2D items – so SVG, PNG, video, plotter and series export work
unchanged. The world-space meshes are kept as well (sk.meshes3d) for glTF/OBJ export
and real 3D objects in Blender.

World coordinates: x right, y down (like the 2D canvas), z towards the viewer.
The default camera looks at the canvas centre so that the plane z = 0 maps 1:1
onto the 2D canvas.
"""
from __future__ import annotations

import math

from .color import Color

# ------------------------------------------------------------------------ 4×4 matrices (row-major)
I4 = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)


def m4_mul(a, b):
    return tuple(sum(a[r * 4 + k] * b[k * 4 + c] for k in range(4)) for r in range(4) for c in range(4))


def m4_apply(m, p):
    x, y, z = p
    return (m[0] * x + m[1] * y + m[2] * z + m[3],
            m[4] * x + m[5] * y + m[6] * z + m[7],
            m[8] * x + m[9] * y + m[10] * z + m[11])


def m4_translate(x, y, z):
    return (1, 0, 0, x, 0, 1, 0, y, 0, 0, 1, z, 0, 0, 0, 1)


def m4_scale(x, y, z):
    return (x, 0, 0, 0, 0, y, 0, 0, 0, 0, z, 0, 0, 0, 0, 1)


def m4_rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return (1, 0, 0, 0, 0, c, -s, 0, 0, s, c, 0, 0, 0, 0, 1)


def m4_rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return (c, 0, s, 0, 0, 1, 0, 0, -s, 0, c, 0, 0, 0, 0, 1)


def m4_rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return (c, -s, 0, 0, s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)


def from_2d(m):
    """2D affine (a, b, c, d, e, f) → 4×4."""
    a, b, c, d, e, f = m
    return (a, c, 0, e, b, d, 0, f, 0, 0, 1, 0, 0, 0, 0, 1)


# ------------------------------------------------------------------------ vectors
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    ln = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / ln, a[1] / ln, a[2] / ln)


def newell_normal(pts):
    nx = ny = nz = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0, z0 = pts[i]
        x1, y1, z1 = pts[(i + 1) % n]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    return _norm((nx, ny, nz))


def _centroid(pts):
    n = len(pts)
    return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n, sum(p[2] for p in pts) / n)


# ------------------------------------------------------------------------ primitive geometry (local)
def orient_outward(verts, faces, centre_of):
    """Flip faces whose normal points towards the inside (centre_of(face_centroid) → inner point)."""
    out = []
    for f in faces:
        pts = [verts[i] for i in f]
        n = newell_normal(pts)
        c = _centroid(pts)
        if _dot(n, _sub(c, centre_of(c))) < 0:
            f = list(reversed(f))
        out.append(list(f))
    return out


def geo_box(w, h, d):
    x, y, z = w / 2, h / 2, d / 2
    v = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z), (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    f = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [3, 2, 6, 7], [0, 3, 7, 4], [1, 2, 6, 5]]
    return v, orient_outward(v, f, lambda c: (0, 0, 0)), True


def geo_ellipsoid(rx, ry, rz, dx=24, dy=16):
    v = []
    for j in range(dy + 1):
        phi = math.pi * j / dy
        for i in range(dx):
            th = math.tau * i / dx
            v.append((rx * math.sin(phi) * math.cos(th), -ry * math.cos(phi), rz * math.sin(phi) * math.sin(th)))
    f = []
    for j in range(dy):
        for i in range(dx):
            a, b = j * dx + i, j * dx + (i + 1) % dx
            c, d = (j + 1) * dx + (i + 1) % dx, (j + 1) * dx + i
            if j == 0:
                f.append([a, c, d])
            elif j == dy - 1:
                f.append([a, b, d])
            else:
                f.append([a, b, c, d])
    return v, orient_outward(v, f, lambda c: (0, 0, 0)), True


def geo_cylinder(r, h, detail=24, top_r=None, caps=True):
    top_r = r if top_r is None else top_r
    v = []
    for i in range(detail):
        a = math.tau * i / detail
        v.append((r * math.cos(a), h / 2, r * math.sin(a)))          # bottom ring (y down = +h/2)
    for i in range(detail):
        a = math.tau * i / detail
        v.append((top_r * math.cos(a), -h / 2, top_r * math.sin(a)))  # top ring
    f = []
    for i in range(detail):
        j = (i + 1) % detail
        if top_r > 0:
            f.append([i, j, detail + j, detail + i])
        else:
            f.append([i, j, detail + i])
    if caps:
        f.append(list(range(detail)))
        if top_r > 0:
            f.append(list(range(detail, 2 * detail)))
    if top_r == 0:
        # cone: collapse the top ring to its first vertex
        apex = len(v)
        v.append((0, -h / 2, 0))
        f = [[i, (i + 1) % detail, apex] for i in range(detail)] + ([list(range(detail))] if caps else [])
    return v, orient_outward(v, f, lambda c: (0, c[1] if abs(c[1]) < h / 2 - 1e-9 else 0, 0)), caps


def geo_torus(r, tube, dx=32, dy=16):
    v = []
    for i in range(dx):
        a = math.tau * i / dx
        for j in range(dy):
            b = math.tau * j / dy
            v.append(((r + tube * math.cos(b)) * math.cos(a), tube * math.sin(b), (r + tube * math.cos(b)) * math.sin(a)))
    f = []
    for i in range(dx):
        for j in range(dy):
            i2, j2 = (i + 1) % dx, (j + 1) % dy
            f.append([i * dy + j, i2 * dy + j, i2 * dy + j2, i * dy + j2])

    def ring_centre(c):
        ln = math.hypot(c[0], c[2]) or 1.0
        return (c[0] / ln * r, 0, c[2] / ln * r)
    return v, orient_outward(v, f, ring_centre), True


def geo_plane(w, h, dx=1, dy=1):
    v = [(-w / 2 + w * i / dx, -h / 2 + h * j / dy, 0.0) for j in range(dy + 1) for i in range(dx + 1)]
    f = [[j * (dx + 1) + i, j * (dx + 1) + i + 1, (j + 1) * (dx + 1) + i + 1, (j + 1) * (dx + 1) + i]
         for j in range(dy) for i in range(dx)]
    return v, f, False


# ------------------------------------------------------------------------ scene
class Scene3D:
    """Collects 3D primitives until they are flushed into 2D items."""

    def __init__(self, width, height):
        self.width, self.height = width, height
        self.fov = math.pi / 3
        self.ortho = None                    # None = perspective, else zoom factor
        self.near = 1.0
        self.reset_camera()
        self.lights: list = []
        self.faces: list = []                # (world_pts, fill, stroke, weight, cull, mesh_id)
        self.lines: list = []                # (world_pts, stroke, weight)

    def reset_camera(self):
        focal = (self.height / 2) / math.tan(self.fov / 2)
        self.eye = (self.width / 2, self.height / 2, focal)
        self.target = (self.width / 2, self.height / 2, 0.0)
        self.down = (0.0, 1.0, 0.0)

    @property
    def empty(self):
        return not self.faces and not self.lines

    # ------------------------------------------------------------- projection
    def _basis(self):
        f = _norm(_sub(self.target, self.eye))
        r = _norm(_cross(f, self.down))
        if r == (0.0, 0.0, 0.0) or math.isnan(r[0]):
            r = (1.0, 0.0, 0.0)
        d = _cross(r, f)
        return f, r, d

    def project(self, pts, basis):
        f, r, d = basis
        focal = (self.height / 2) / math.tan(self.fov / 2)
        cx, cy = self.width / 2, self.height / 2
        out, depths = [], []
        for p in pts:
            q = _sub(p, self.eye)
            vz = _dot(q, f)
            vx, vy = _dot(q, r), _dot(q, d)
            if self.ortho is not None:
                out.append((cx + vx * self.ortho, cy + vy * self.ortho))
            else:
                if vz < self.near:
                    return None, None
                out.append((cx + vx * focal / vz, cy + vy * focal / vz))
            depths.append(vz)
        return out, sum(depths) / len(depths)

    # ------------------------------------------------------------- shading
    def shade(self, base: Color, normal, centroid) -> Color:
        if not self.lights:
            return base
        r = g = b = 0.0
        for kind, col, vec in self.lights:
            if kind == "ambient":
                k = (1.0, 1.0, 1.0)
                inten = 1.0
            elif kind == "directional":
                inten = max(0.0, -_dot(normal, vec))
            else:                                    # point light
                inten = max(0.0, _dot(normal, _norm(_sub(vec, centroid))))
            r += col.r / 255 * inten
            g += col.g / 255 * inten
            b += col.b / 255 * inten
        return Color(min(255, base.r * r), min(255, base.g * g), min(255, base.b * b), base.a)

    def render(self):
        """→ list of (pts2d, fill, stroke, weight, closed) back to front."""
        basis = self._basis()
        f_dir = basis[0]
        prims = []
        for pts, fill, stroke, weight, cull, _ in self.faces:
            n = newell_normal(pts)
            c = _centroid(pts)
            to_eye = _sub(self.eye, c) if self.ortho is None else (-f_dir[0], -f_dir[1], -f_dir[2])
            facing = _dot(n, to_eye)
            if cull and facing <= 0:
                continue
            if facing < 0:
                n = (-n[0], -n[1], -n[2])             # double-sided surfaces: light the visible side
            p2, depth = self.project(pts, basis)
            if p2 is None:
                continue
            shaded = self.shade(fill, n, c) if isinstance(fill, Color) else fill
            prims.append((depth, p2, shaded, stroke, weight, True))
        for pts, stroke, weight in self.lines:
            p2, depth = self.project(pts, basis)
            if p2 is not None:
                prims.append((depth - 1e-6, p2, None, stroke, weight, False))
        prims.sort(key=lambda p: -p[0])               # far → near
        return [p[1:] for p in prims]
