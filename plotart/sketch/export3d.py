"""3D export of a sketch's meshes: glTF binary (.glb) and Wavefront OBJ (+ MTL).

Pure Python. Coordinates are converted from sketch space (x right, y down, z towards
the viewer, origin top left, pixels) to the usual 3D convention (y up, origin at the
canvas centre). `scale` turns sketch units into metres (default: 100 px = 1 m).
glb opens in Blender, TouchDesigner (File In SOP / Import), three.js, Windows 3D Viewer …
"""
from __future__ import annotations

import json
import math
import struct


def _to_world(meshes, width, height, scale):
    """Sketch → y-up coordinates. Mirroring y flips handedness, so faces are reversed."""
    cx, cy = width / 2, height / 2
    out = []
    for m in meshes:
        verts = [((x - cx) * scale, (cy - y) * scale, z * scale) for x, y, z in m["verts"]]
        faces = [list(reversed(f)) for f in m.get("faces", [])]
        out.append({**m, "verts": verts, "faces": faces})
    return out


def _srgb_to_linear(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _face_normal(pts):
    nx = ny = nz = 0.0
    for i in range(len(pts)):
        x0, y0, z0 = pts[i]
        x1, y1, z1 = pts[(i + 1) % len(pts)]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / ln, ny / ln, nz / ln


# ---------------------------------------------------------------------------- OBJ
def to_obj(meshes, width, height, scale=0.01, name="plotart") -> tuple[str, str]:
    """→ (obj text, mtl text). The OBJ references f"{name}.mtl"."""
    obj = [f"# plotart 3D-Export", f"mtllib {name}.mtl"]
    mtl = ["# plotart Materialien"]
    base = 1
    for i, m in enumerate(_to_world(meshes, width, height, scale)):
        r, g, b, a = m.get("color", (200, 200, 200, 255))
        mat = f"mat{i}"
        mtl += [f"newmtl {mat}", f"Kd {r / 255:.4f} {g / 255:.4f} {b / 255:.4f}", f"d {a / 255:.4f}", "illum 1", ""]
        obj.append(f"o {m['name']}_{i}")
        obj.append(f"usemtl {mat}")
        obj += [f"v {x:.5f} {y:.5f} {z:.5f}" for x, y, z in m["verts"]]
        if m.get("line"):
            obj.append("l " + " ".join(str(base + k) for k in range(len(m["verts"]))))
        for f in m["faces"]:
            obj.append("f " + " ".join(str(base + k) for k in f))
        base += len(m["verts"])
    return "\n".join(obj) + "\n", "\n".join(mtl)


# ---------------------------------------------------------------------------- glTF binary
def to_glb(meshes, width, height, scale=0.01) -> bytes:
    """Flat-shaded meshes (one glTF mesh + material per sketch shape) as .glb bytes."""
    buf = bytearray()
    views, accessors, gl_meshes, nodes, materials = [], [], [], [], []

    def add_floats(values, ncomp):
        while len(buf) % 4:
            buf.append(0)
        off = len(buf)
        buf.extend(struct.pack(f"<{len(values)}f", *values))
        views.append({"buffer": 0, "byteOffset": off, "byteLength": len(values) * 4, "target": 34962})
        n = len(values) // ncomp
        acc = {"bufferView": len(views) - 1, "componentType": 5126, "count": n,
               "type": {2: "VEC2", 3: "VEC3"}[ncomp]}
        if ncomp == 3:
            xs, ys, zs = values[0::3], values[1::3], values[2::3]
            acc["min"] = [min(xs), min(ys), min(zs)]
            acc["max"] = [max(xs), max(ys), max(zs)]
        accessors.append(acc)
        return len(accessors) - 1

    for i, m in enumerate(_to_world(meshes, width, height, scale)):
        verts = m["verts"]
        if not verts:
            continue
        r, g, b, a = m.get("color", (200, 200, 200, 255))
        mat = {"name": f"{m['name']}_{i}",
               "pbrMetallicRoughness": {"baseColorFactor": [_srgb_to_linear(r), _srgb_to_linear(g),
                                                            _srgb_to_linear(b), a / 255],
                                        "metallicFactor": 0.0, "roughnessFactor": 0.8}}
        if a < 255:
            mat["alphaMode"] = "BLEND"
        if m.get("line"):
            pos = [c for k in range(len(verts) - 1) for p in (verts[k], verts[k + 1]) for c in p]
            if not pos:
                continue
            prim = {"attributes": {"POSITION": add_floats(pos, 3)}, "mode": 1}
        else:
            pos, nrm = [], []
            for f in m["faces"]:
                pts = [verts[k] for k in f]
                if len(pts) < 3:
                    continue
                n = _face_normal(pts)
                for k in range(1, len(pts) - 1):          # triangle fan
                    for p in (pts[0], pts[k], pts[k + 1]):
                        pos.extend(p)
                        nrm.extend(n)
            if not pos:
                continue
            prim = {"attributes": {"POSITION": add_floats(pos, 3), "NORMAL": add_floats(nrm, 3)}, "mode": 4}
            if not m.get("closed", True):
                mat["doubleSided"] = True
        materials.append(mat)
        prim["material"] = len(materials) - 1
        gl_meshes.append({"name": f"{m['name']}_{i}", "primitives": [prim]})
        nodes.append({"name": f"{m['name']}_{i}", "mesh": len(gl_meshes) - 1})

    while len(buf) % 4:
        buf.append(0)
    gltf = {"asset": {"version": "2.0", "generator": "plotart"},
            "scene": 0, "scenes": [{"name": "plotart", "nodes": list(range(len(nodes)))}],
            "nodes": nodes, "meshes": gl_meshes, "materials": materials,
            "accessors": accessors, "bufferViews": views, "buffers": [{"byteLength": len(buf)}]}
    if not nodes:
        for k in ("nodes", "meshes", "materials", "accessors", "bufferViews", "buffers"):
            gltf.pop(k)
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    chunks = struct.pack("<II", len(js), 0x4E4F534A) + js
    if nodes:
        chunks += struct.pack("<II", len(buf), 0x004E4942) + bytes(buf)
    return struct.pack("<III", 0x46546C67, 2, 12 + len(chunks)) + chunks


def read_glb(data: bytes) -> dict:
    """Parse the JSON chunk of a .glb (for tests and quick inspection)."""
    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2 or length != len(data):
        raise ValueError("keine gültige GLB-Datei")
    jlen, _ = struct.unpack_from("<II", data, 12)
    return json.loads(data[20:20 + jlen])
