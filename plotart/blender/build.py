"""Scene description → Blender objects (needs bpy; works with Blender 4.2 – 5.x).

Usage inside Blender:
    from plotart.blender import scene, build
    desc = scene.build_scene(open("skizze.py").read(), seed=3)
    build.build(desc, build.Options(relief="order", relief_height=1.0))
"""
from __future__ import annotations

import base64
import os
import tempfile
from dataclasses import dataclass

import bpy

from .geometry import MeshBuffer, extruded_polygon, flat_polygon, ribbon
from .scene import visibility_ranges

TAG = "plotart"
COLLECTION = "plotart"


@dataclass
class Options:
    stroke_mode: str = "flat"         # flat | tube
    relief: str = "none"              # none | constant | order | brightness
    relief_height: float = 0.5        # Blender units
    material_mode: str = "flat"       # flat (emission, exact 2D colours) | physical (Principled BSDF)
    setup_scene: bool = True          # camera, resolution, fps, frame range, colour management
    camera: str = "top"               # top (orthographic, exactly the 2D image) | perspective (3D view)
    location: tuple = (0.0, 0.0, 0.0)


# ------------------------------------------------------------------------- helpers
def _lin(c: float) -> float:
    """sRGB → linear (Blender colour sockets are linear)."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _tag(idblock):
    idblock[TAG] = True
    return idblock


def clear_previous():
    """Remove everything an earlier build created (objects, meshes, curves, materials, images)."""
    for ob in [o for o in bpy.data.objects if o.get(TAG) and not o.get("plotart_keep")]:
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.images):
        for block in [b for b in coll if b.get(TAG) and b.users == 0]:
            coll.remove(block)


def _collection(scene) -> bpy.types.Collection:
    coll = bpy.data.collections.get(COLLECTION)
    if coll is None:
        coll = _tag(bpy.data.collections.new(COLLECTION))
    if coll.name not in scene.collection.children:
        scene.collection.children.link(coll)
    return coll


class _Materials:
    def __init__(self, mode: str):
        self.mode = mode
        self.cache: dict = {}

    def get(self, rgba) -> bpy.types.Material:
        key = tuple(round(v, 3) for v in rgba)
        mat = self.cache.get(key)
        if mat is not None:
            return mat
        r, g, b, a = key
        name = "plotart #{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))
        if a < 1:
            name += f" {int(a * 100)}%"
        mat = _tag(bpy.data.materials.new(name))
        try:
            mat.use_nodes = True                 # always on (and deprecated) in Blender 5
        except (AttributeError, TypeError):
            pass
        nt = mat.node_tree
        nodes, links = nt.nodes, nt.links
        nodes.clear()
        out = nodes.new("ShaderNodeOutputMaterial")
        color = (_lin(r), _lin(g), _lin(b), 1.0)
        if self.mode == "flat":
            shader = nodes.new("ShaderNodeEmission")
            shader.inputs["Color"].default_value = color
            shader.inputs["Strength"].default_value = 1.0
        else:
            shader = nodes.new("ShaderNodeBsdfPrincipled")
            shader.inputs["Base Color"].default_value = color
            shader.inputs["Roughness"].default_value = 0.55
        if a < 1:
            transp = nodes.new("ShaderNodeBsdfTransparent")
            mix = nodes.new("ShaderNodeMixShader")
            mix.inputs[0].default_value = a
            links.new(transp.outputs[0], mix.inputs[1])
            links.new(shader.outputs[0], mix.inputs[2])
            links.new(mix.outputs[0], out.inputs["Surface"])
            if hasattr(mat, "surface_render_method"):
                mat.surface_render_method = "BLENDED"
            elif hasattr(mat, "blend_method"):
                mat.blend_method = "BLEND"
        else:
            links.new(shader.outputs[0], out.inputs["Surface"])
        mat.diffuse_color = (r, g, b, a)        # viewport solid-mode colour
        self.cache[key] = mat
        return mat


def _new_object(name, data, coll, z_shift=0.0):
    ob = _tag(bpy.data.objects.new(name, data))
    coll.objects.link(ob)
    if z_shift:
        ob.location.z += z_shift
    return ob


def _mesh_object(name, buf: MeshBuffer, mats: list, coll):
    # put the origin at the content's mean height: Eevee sorts transparent objects by origin
    zc = sum(v[2] for v in buf.verts) / len(buf.verts)
    verts = [(x, y, z - zc) for x, y, z in buf.verts]
    me = _tag(bpy.data.meshes.new(name))
    me.from_pydata(verts, [], buf.faces)
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", buf.mats)
    me.update()
    ob = _new_object(name, me, coll)
    ob.location.z = zc
    return ob


def _mesh3d_object(name, shape, mat, coll):
    """A real 3D object from a sketch's box()/sphere()/mesh()/line3d() (origin at its centre)."""
    verts = shape["verts"]
    c = [sum(v[i] for v in verts) / len(verts) for i in range(3)]
    local = [(x - c[0], y - c[1], z - c[2]) for x, y, z in verts]
    if shape["line"]:
        cu = _tag(bpy.data.curves.new(name, "CURVE"))
        cu.dimensions = "3D"
        cu.bevel_depth = 0.01
        cu.bevel_resolution = 2
        sp = cu.splines.new("POLY")
        sp.points.add(len(local) - 1)
        sp.points.foreach_set("co", [v for p in local for v in (*p, 1.0)])
        data = cu
    else:
        data = _tag(bpy.data.meshes.new(name))
        data.from_pydata(local, [], shape["faces"])
        data.update()
    data.materials.append(mat)
    ob = _new_object(name, data, coll)
    ob.location = c
    return ob


def _curve_object(name, paths, coll, *, fill=False, radius=None, mat=None, z=0.0):
    """POLY splines. fill=True → 2D filled curve (handles holes); radius → 3D tube."""
    cu = _tag(bpy.data.curves.new(name, "CURVE"))
    if fill:
        cu.dimensions = "2D"
        cu.fill_mode = "BOTH"
    else:
        cu.dimensions = "3D"
        cu.fill_mode = "FULL"
        cu.bevel_depth = 1.0
        cu.bevel_resolution = 3
        cu.use_fill_caps = True
    for pts, closed, w in paths:
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        flat = []
        for x, y in pts:
            flat.extend((x, y, 0.0, 1.0))
        sp.points.foreach_set("co", flat)
        if not fill:
            sp.points.foreach_set("radius", [w / 2] * len(pts))
        sp.use_cyclic_u = bool(closed or fill)
    if mat is not None:
        cu.materials.append(mat)
    ob = _new_object(name, cu, coll)
    ob.location.z = z
    return ob


def _text_object(name, shape, mat, coll, z):
    cu = _tag(bpy.data.curves.new(name, "FONT"))
    cu.body = shape["text"]
    cu.size = shape["size"]
    cu.align_x = {"left": "LEFT", "center": "CENTER", "right": "RIGHT"}.get(shape["align"], "LEFT")
    cu.align_y = {"top": "TOP", "center": "CENTER", "bottom": "BOTTOM"}.get(shape["valign"], "BOTTOM_BASELINE")
    cu.materials.append(mat)
    ob = _new_object(name, cu, coll)
    ob.location = (shape["pos"][0], shape["pos"][1], z)
    ob.rotation_euler.z = shape["rot"]
    return ob


def _image_object(name, shape, coll, z, mode):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(shape["png"] if isinstance(shape["png"], bytes) else base64.b64decode(shape["png"]))
        path = f.name
    try:
        img = _tag(bpy.data.images.load(path))
        img.pack()
    finally:
        os.unlink(path)
    mat = _tag(bpy.data.materials.new(name))
    try:
        mat.use_nodes = True
    except (AttributeError, TypeError):
        pass
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Linear" if shape["smooth"] else "Closest"
    shader = nodes.new("ShaderNodeEmission" if mode == "flat" else "ShaderNodeBsdfPrincipled")
    links.new(tex.outputs["Color"], shader.inputs["Color" if mode == "flat" else "Base Color"])
    links.new(shader.outputs[0], out.inputs["Surface"])
    me = _tag(bpy.data.meshes.new(name))
    me.from_pydata([(x, y, 0.0) for x, y in shape["corners"]], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for loop, co in zip(uv.data, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        loop.uv = co
    me.materials.append(mat)
    ob = _new_object(name, me, coll)
    ob.location.z = z
    return ob


def _key_visibility(obj, first: int, last: int, frame_end: int):
    """Visible from image `first` to `last` (0-based) → Blender frames first+1 … last+1."""
    for prop in ("hide_render", "hide_viewport"):
        if first > 0:
            setattr(obj, prop, True)
            obj.keyframe_insert(prop, frame=1)
        setattr(obj, prop, False)
        obj.keyframe_insert(prop, frame=first + 1)
        if last + 1 < frame_end:
            setattr(obj, prop, True)
            obj.keyframe_insert(prop, frame=last + 2)


def _luminance(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


# ------------------------------------------------------------------------- main
def build(desc: dict, opts: Options | None = None, scene=None) -> dict:
    """Create Blender objects for a scene description. Returns some statistics."""
    opts = opts or Options()
    scene = scene or bpy.context.scene
    clear_previous()
    coll = _collection(scene)
    mats = _Materials(opts.material_mode)
    W, H = desc["width"], desc["height"]
    frames = desc["frames"]
    max_order = max((s["order"] for f in frames for s in f["shapes"]), default=0) + 1
    dz = min(W * 2e-4, W * 0.02 / max_order)
    relief = opts.relief if opts.relief in ("constant", "order", "brightness") else None
    animated = desc["animated"] and len(frames) > 1
    ranges = visibility_ranges(frames) if animated else [(0, 0)]
    frame_end = len(frames)
    stats = {"objects": 0, "faces": 0, "frames": len(frames)}

    def height_of(shape):
        if not relief:
            return 0.0
        if relief == "constant":
            return opts.relief_height
        if relief == "order":
            return opts.relief_height * (shape["order"] + 1) / max_order
        return opts.relief_height * max(0.03, _luminance(shape["color"]))

    for fi, frame in enumerate(frames):
        tag = f"{fi + 1:04d}" if animated else ""
        created = []
        buf, buf_mats = MeshBuffer(), []
        mat_index: dict = {}

        def mi(color):
            m = mats.get(color)
            if m.name not in mat_index:
                mat_index[m.name] = len(buf_mats)
                buf_mats.append(m)
            return mat_index[m.name]

        tubes: dict = {}
        for s in frame["shapes"]:
            z = s.get("z_base", 0.0) + s["order"] * dz
            t = s["type"]
            if t == "mesh3d":
                created.append(_mesh3d_object(f"plotart {s['name']} {tag}".strip(), s, mats.get(s["color"]), coll))
                stats["faces"] += len(s["faces"])
            elif t == "background":
                bg = MeshBuffer()
                v, f = flat_polygon([(-W / 2, -H / 2), (W / 2, -H / 2), (W / 2, H / 2), (-W / 2, H / 2)], z)
                bg.add(v, f, 0)
                created.append(_mesh_object(f"plotart Hintergrund {tag}".strip(), bg, [mats.get(s["color"])], coll))
            elif t == "fill":
                hgt = height_of(s)
                if len(s["rings"]) > 1 and not relief:
                    # holes: Blender's 2D curve fill does even-odd for us
                    created.append(_curve_object(f"plotart Form {tag}".strip(), [(r, True, 0) for r in s["rings"]],
                                                 coll, fill=True, mat=mats.get(s["color"]), z=z))
                    continue
                for ring in s["rings"]:
                    v, f = extruded_polygon(ring, z, z + hgt) if hgt > 0 else flat_polygon(ring, z)
                    buf.add(v, f, mi(s["color"]))
            elif t == "stroke":
                if opts.stroke_mode == "tube":
                    tubes.setdefault(tuple(s["color"]), []).extend(
                        (p["pts"], p["closed"], s["width"]) for p in s["paths"] if len(p["pts"]) >= 2)
                    continue
                hgt = height_of(s)
                for p in s["paths"]:
                    v, f = ribbon(p["pts"], p["closed"], s["width"], z, canvas_size=W)
                    if hgt > 0:
                        for face in f:
                            vv, ff = extruded_polygon([v[i][:2] for i in face], z, z + hgt)
                            buf.add(vv, ff, mi(s["color"]))
                    else:
                        buf.add(v, f, mi(s["color"]))
            elif t == "text":
                created.append(_text_object(f"plotart Text {tag}".strip(), s, mats.get(s["color"]), coll, z))
            elif t == "image":
                created.append(_image_object(f"plotart Bild {tag}".strip(), s, coll, z, opts.material_mode))
        if buf:
            created.append(_mesh_object(f"plotart Formen {tag}".strip(), buf, buf_mats, coll))
            stats["faces"] += len(buf.faces)
        for color, paths in tubes.items():
            created.append(_curve_object(f"plotart Linien {tag}".strip(), paths, coll, mat=mats.get(color),
                                         z=max(s["order"] for s in frame["shapes"]) * dz))
        if animated:
            first, last = ranges[fi]
            for ob in created:
                _key_visibility(ob, first, last, frame_end)
        for ob in created:
            ob.location.x += opts.location[0]
            ob.location.y += opts.location[1]
            ob.location.z += opts.location[2]
        stats["objects"] += len(created)

    if opts.setup_scene:
        top3d = max((v[2] for f in frames for s in f["shapes"] if s["type"] == "mesh3d" for v in s["verts"]),
                    default=0.0)
        _setup_scene(scene, desc, frames, animated, opts,
                     top=max(top3d, max_order * dz + (opts.relief_height if relief else 0)))
    return stats


def _setup_scene(scene, desc, frames, animated, opts, top):
    W, H = desc["width"], desc["height"]
    r = scene.render
    r.resolution_x, r.resolution_y = desc["px_width"], desc["px_height"]
    r.resolution_percentage = 100
    fps = desc["fps"]
    r.fps = max(1, round(fps))
    r.fps_base = r.fps / fps
    scene.frame_start = 1
    scene.frame_end = len(frames) if animated else max(scene.frame_end, 1)
    if opts.material_mode == "flat":
        try:
            scene.view_settings.view_transform = "Standard"     # exact 2D colours instead of AgX/Filmic
        except TypeError:
            pass
    # trails stack many translucent layers – Cycles stops after 8 by default
    cycles = getattr(scene, "cycles", None)
    if cycles is not None and hasattr(cycles, "transparent_max_bounces"):
        cycles.transparent_max_bounces = max(cycles.transparent_max_bounces, 1024)
    if scene.world is None:
        scene.world = _tag(bpy.data.worlds.new("plotart Welt"))
    if opts.material_mode == "physical":
        try:
            scene.world.use_nodes = True
        except (AttributeError, TypeError):
            pass
        bg = scene.world.node_tree.nodes.get("Background") if scene.world.node_tree else None
        if bg is not None:
            bg.inputs["Color"].default_value = (0.8, 0.8, 0.8, 1.0)
            bg.inputs["Strength"].default_value = 0.6
    cam = bpy.data.objects.get("plotart Kamera")
    if cam is None:
        cam = _tag(bpy.data.objects.new("plotart Kamera", _tag(bpy.data.cameras.new("plotart Kamera"))))
        cam["plotart_keep"] = True
        scene.collection.objects.link(cam)
    ox, oy, oz = opts.location
    if opts.camera == "perspective":
        # look at the piece from the front, ~35° above – shows reliefs and tubes in 3D
        import math
        cam.data.type = "PERSP"
        cam.data.lens = 50
        dist = max(W, H) * 1.9
        tilt = math.radians(35)
        cam.location = (ox, oy - dist * math.cos(tilt), oz + top / 2 + dist * math.sin(tilt))
        cam.rotation_euler = (math.radians(90) - tilt, 0, 0)
        cam.data.clip_start = 0.05
        cam.data.clip_end = dist * 4
    else:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = max(W, H)
        cam.location = (ox, oy, oz + top + 5)
        cam.rotation_euler = (0, 0, 0)
        cam.data.clip_start = 0.01
        cam.data.clip_end = top + 20 + max(W, H) * 2
    scene.camera = cam
    if opts.material_mode == "physical" and not any(o.type == "LIGHT" for o in scene.objects):
        sun = _tag(bpy.data.objects.new("plotart Licht", _tag(bpy.data.lights.new("plotart Licht", "SUN"))))
        sun["plotart_keep"] = True
        sun.rotation_euler = (0.6, 0.2, 0.8)
        sun.data.energy = 3.0
        scene.collection.objects.link(sun)
