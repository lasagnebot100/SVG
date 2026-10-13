"""Sketch → neutral scene description for Blender (pure Python, no bpy needed).

Coordinates are Blender units: canvas centred on the origin, y pointing up, the
canvas `width_bu` wide. Every shape gets an increasing `order` (painter's order)
that the builder turns into a tiny z offset.
"""
from __future__ import annotations

import math

from ..sketch.animation import Animation
from ..sketch.color import Color, Gradient
from ..sketch.core import IDENTITY, mat_apply
from ..sketch.flatten import _scale_of, flatten

MM_TO_PX = 96 / 25.4


def _rgba(paint) -> tuple | None:
    if paint is None:
        return None
    if isinstance(paint, Gradient):
        paint = paint.average()
    if isinstance(paint, Color):
        return (round(paint.r / 255, 4), round(paint.g / 255, 4), round(paint.b / 255, 4), round(paint.a, 4))
    return None


class SceneError(Exception):
    pass


def _convert_meshes(meshes, sk, k):
    """World-space 3D meshes → real Blender meshes (y up; mirroring y reverses the winding)."""
    w, h = sk.width, sk.height
    out = []
    for m in meshes:
        verts = [((x - w / 2) * k, (h / 2 - y) * k, z * k) for x, y, z in m["verts"]]
        r, g, b, a = m["color"]
        shape = {"type": "mesh3d", "name": m["name"], "verts": verts,
                 "faces": [list(reversed(f)) for f in m["faces"]], "line": bool(m.get("line")),
                 "color": (round(r / 255, 4), round(g / 255, 4), round(b / 255, 4), round(a / 255, 4))}
        out.append(shape)
    return out


def _convert_items(items, sk, k, order_start, meshes=()):
    """Sketch items → shapes. Returns (shapes, next_order).

    3D shapes come as real meshes (`meshes`) instead of their projected 2D outlines;
    2D shapes drawn before them are moved behind the 3D objects.
    """
    w, h = sk.width, sk.height

    def bu(x, y):
        return ((x - w / 2) * k, (h / 2 - y) * k)

    shapes = _convert_meshes(meshes, sk, k)
    n3d = len(shapes)
    zmin = min((v[2] for s in shapes for v in s["verts"]), default=0.0)
    before3d = None                             # number of shapes that were drawn before the 3D ones
    order = order_start
    for s in shapes:
        s["order"] = order
    tol = max(w, h) / 2000                      # chord error in sketch units
    for it in items:
        if isinstance(it.data, dict) and it.data.get("from3d"):
            if before3d is None:
                before3d = len(shapes)
            continue
        st = it.style
        m = it.matrix or IDENTITY
        if it.kind == "background":
            col = _rgba(st.fill)
            if col and col[3] > 0:
                shapes.append({"type": "background", "color": col, "order": order})
                order += 1
            continue
        if it.kind == "text":
            d = it.data
            col = _rgba(st.fill)
            if col is None:
                continue
            x, y = mat_apply(m, d["x"], d["y"])
            shapes.append({"type": "text", "text": d["s"], "pos": bu(x, y),
                           "size": st.text_size * _scale_of(m) * k,
                           "rot": -math.atan2(m[1], m[0]), "align": st.text_align, "valign": st.text_valign,
                           "bold": "bold" in st.text_style, "italic": "italic" in st.text_style,
                           "color": col, "order": order})
            order += 1
            continue
        if it.kind == "image":
            d = it.data
            corners = [bu(*mat_apply(m, x, y)) for x, y in
                       ((d["x"], d["y"] + d["h"]), (d["x"] + d["w"], d["y"] + d["h"]),
                        (d["x"] + d["w"], d["y"]), (d["x"], d["y"]))]     # bottom-left first (UV order)
            shapes.append({"type": "image", "png": d["png"], "corners": corners,
                           "smooth": d["smooth"], "order": order})
            order += 1
            continue
        subs = flatten(it, w, h, tol=tol)
        if not subs:
            continue
        fill, stroke = _rgba(st.fill), _rgba(st.stroke) if st.weight > 0 else None
        if fill and fill[3] > 0:
            rings = [[bu(x, y) for x, y in pts] for pts, _ in subs if len(pts) >= 3]
            if rings:
                shapes.append({"type": "fill", "rings": rings, "color": fill, "order": order})
                order += 1
        if stroke and stroke[3] > 0:
            paths = [{"pts": [bu(x, y) for x, y in pts], "closed": closed} for pts, closed in subs]
            shapes.append({"type": "stroke", "paths": paths, "width": st.weight * _scale_of(m) * k,
                           "cap": st.cap, "color": stroke, "order": order})
            order += 1
    if n3d and before3d is not None:
        gap = max(w, h) * k * 0.01
        zmax = max(v[2] for s in shapes[:n3d] for v in s["verts"])
        for i, s in enumerate(shapes[n3d:], n3d):
            s["z_base"] = min(0.0, zmin) - gap if i < before3d else max(0.0, zmax) + gap
    return shapes, order


def build_scene(source: str, params: dict | None = None, seed: int = 1, *, width_bu: float = 10.0,
                frame: int | None = None, max_frames: int | None = None) -> dict:
    """Run the sketch and describe it for Blender.

    frame=None → all frames of an animation (or the single image of a still sketch);
    frame=n    → only image n (1-based), including trails accumulated before it.
    """
    anim = Animation(source, params, seed)
    if anim.error:
        raise SceneError(_err(anim.error))
    sk = anim.sk
    k = width_bu / sk.width
    total = anim.total
    if max_frames:
        total = min(total, int(max_frames))
    px_scale = MM_TO_PX if sk.unit == "mm" else 1.0
    scene = {
        "width": width_bu, "height": sk.height * k,
        "px_width": max(1, round(sk.width * px_scale)), "px_height": max(1, round(sk.height * px_scale)),
        "fps": anim.fps, "animated": anim.animated and frame is None and total > 1,
        "params": [p.to_json() for p in sk.param_specs], "seed": seed, "frames": [],
    }
    order = 0
    if frame is not None:                         # one still image, trails included
        target = max(1, min(int(frame), anim.total)) - 1
        acc, meshes = [], []
        while anim.frame <= target:
            fr = anim.next_frame()
            if fr is None:
                break
            if fr.error:
                raise SceneError(f"Bild {fr.index + 1}: {_err(fr.error)}")
            acc = list(fr.items) if fr.clears else acc + list(fr.items)
            meshes = fr.meshes
        shapes, order = _convert_items(acc, sk, k, 0, meshes)
        scene["frames"].append({"index": target, "clears": True, "shapes": shapes})
        scene["params"] = [p.to_json() for p in sk.param_specs]
        return scene
    for _ in range(total):
        fr = anim.next_frame()
        if fr is None:
            break
        if fr.error:
            raise SceneError(f"Bild {fr.index + 1}: {_err(fr.error)}")
        if fr.clears:
            order = 0
        shapes, order = _convert_items(fr.items, sk, k, order, fr.meshes)
        scene["frames"].append({"index": fr.index, "clears": fr.clears, "shapes": shapes})
    scene["params"] = [p.to_json() for p in sk.param_specs]
    return scene


def visibility_ranges(frames: list[dict]) -> list[tuple[int, int]]:
    """For each frame: (first, last) image index during which its shapes are visible.

    Shapes stay visible until the next frame that clears the canvas (trails!).
    """
    clears = [i for i, f in enumerate(frames) if f["clears"]] + [len(frames)]
    out = []
    for i in range(len(frames)):
        nxt = next(c for c in clears if c > i)
        out.append((i, nxt - 1))
    return out


def _err(err: dict) -> str:
    return (f"Zeile {err['line']}: " if err.get("line") else "") + err["message"]
