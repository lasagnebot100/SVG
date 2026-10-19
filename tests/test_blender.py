"""Blender integration. The pure-Python parts run everywhere; the bpy tests run when the
`bpy` module is installed (pip install bpy), e.g.:  python -m unittest tests.test_blender
"""
import importlib.util
import math
import os
import sys
import tempfile
import unittest
import zipfile

from plotart.blender.geometry import extruded_polygon, flat_polygon, ribbon
from plotart.blender.scene import SceneError, build_scene, visibility_ranges

HAS_BPY = importlib.util.find_spec("bpy") is not None

STILL = """
size(200, 100)
background("white")
fill("red"); stroke("blue"); stroke_weight(4)
rect(0, 0, 100, 50)
begin_shape(); vertex(120, 10); vertex(190, 10); vertex(190, 90); vertex(120, 90)
begin_contour(); vertex(140, 30); vertex(170, 30); vertex(170, 70); vertex(140, 70); end_contour()
end_shape(CLOSE)
text_size(20); fill(0); text("Hallo", 10, 90)
"""

TRAILS = """
size(100, 100)
animation(frames=6)
def setup():
    background(255)
def draw():
    background(255, 255, 255, 20)
    if frame_count == 4:
        background(0)
    circle(frame_count * 10, 50, 8)
"""


class GeometryTests(unittest.TestCase):
    def test_ribbon_width(self):
        verts, faces = ribbon([(0, 0), (10, 0)], False, 2.0, 0.5, round_joins=False)
        self.assertEqual(len(faces), 1)
        ys = sorted({round(v[1], 6) for v in verts})
        self.assertEqual(ys, [-1.0, 1.0])
        self.assertTrue(all(v[2] == 0.5 for v in verts))

    def test_polygons_face_up(self):
        verts, faces = flat_polygon([(0, 0), (0, 1), (1, 1), (1, 0)], 0)     # clockwise input
        (a, b, c) = (verts[i] for i in faces[0][:3])
        normal_z = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        self.assertGreater(normal_z, 0)
        verts, faces = extruded_polygon([(0, 0), (1, 0), (1, 1)], 0, 2)
        self.assertEqual((len(verts), len(faces)), (6, 5))


class SceneTests(unittest.TestCase):
    def test_still_scene(self):
        s = build_scene(STILL, width_bu=4)
        self.assertEqual((s["width"], s["height"], s["px_width"]), (4, 2, 200))
        shapes = s["frames"][0]["shapes"]
        types = [x["type"] for x in shapes]
        self.assertEqual(types, ["background", "fill", "stroke", "fill", "stroke", "text"])
        rect = shapes[1]["rings"][0]
        xs, ys = [p[0] for p in rect], [p[1] for p in rect]
        self.assertAlmostEqual(min(xs), -2) and self.assertAlmostEqual(max(ys), 1)   # top-left corner, y up
        self.assertEqual(len(shapes[3]["rings"]), 2)                                  # outer + hole
        self.assertAlmostEqual(shapes[2]["width"], 4 * 4 / 200)
        self.assertEqual([x["order"] for x in shapes], list(range(6)))
        self.assertEqual(shapes[5]["text"], "Hallo")

    def test_animation_visibility(self):
        s = build_scene(TRAILS)
        self.assertTrue(s["animated"])
        clears = [f["clears"] for f in s["frames"]]
        self.assertEqual(clears, [True, False, False, True, False, False])
        self.assertEqual(visibility_ranges(s["frames"]), [(0, 2), (1, 2), (2, 2), (3, 5), (4, 5), (5, 5)])

    def test_single_frame_collects_trails(self):
        s = build_scene(TRAILS, frame=3)
        self.assertFalse(s["animated"])
        circles = [x for x in s["frames"][0]["shapes"] if x["type"] == "fill" and x["color"][0] == 1.0
                   and len(x["rings"][0]) > 4]
        self.assertEqual(len(circles), 3)                       # frames 1–3 accumulate

    def test_errors(self):
        with self.assertRaises(SceneError):
            build_scene("circle(")
        with self.assertRaises(SceneError):
            build_scene("animation(frames=3)\ndef draw():\n    if frame_count == 2:\n        1 / 0\n")


class PackageTests(unittest.TestCase):
    def test_addon_zip(self):
        import tomllib
        from plotart.blender.package import build_addon
        with tempfile.TemporaryDirectory() as tmp:
            path = build_addon(os.path.join(tmp, "a.zip"))
            with zipfile.ZipFile(path) as z:
                names = set(z.namelist())
                manifest = tomllib.loads(z.read("blender_manifest.toml").decode())
                init = z.read("__init__.py").decode()
        self.assertEqual(manifest["id"], "plotart")
        self.assertEqual(manifest["type"], "add-on")
        self.assertIn("plotart/blender/build.py", names)
        self.assertIn("plotart/sketch/examples/13_loop_kreise.py", names)
        self.assertFalse(any("static/" in n or n.endswith("web.py") for n in names))
        self.assertIn("def register()", init)
        compile(init, "__init__.py", "exec")


@unittest.skipUnless(HAS_BPY, "bpy nicht installiert (pip install bpy)")
class BlenderTests(unittest.TestCase):
    def setUp(self):
        import bpy
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_build_options(self):
        import bpy
        from plotart.blender import build
        s = build_scene(STILL)
        for opts in (build.Options(), build.Options(stroke_mode="tube", relief="order", camera="perspective",
                                                    material_mode="physical")):
            stats = build.build(s, opts)
            self.assertGreater(stats["objects"], 2)
        types = sorted({o.type for o in bpy.data.objects})
        self.assertEqual(types, ["CAMERA", "CURVE", "FONT", "LIGHT", "MESH"])
        # rebuilding replaced the first build instead of piling up objects
        self.assertEqual(sum(1 for o in bpy.data.objects if o.type == "FONT"), 1)

    def test_animation_keyframes(self):
        import bpy
        from plotart.blender import build
        build.build(build_scene(TRAILS))
        sc = bpy.context.scene
        self.assertEqual((sc.frame_start, sc.frame_end), (1, 6))

        def visible_frames():
            # object names end in the image number (Blender may append .001 for duplicates)
            return {o.name.split()[-1][:4] for o in bpy.data.objects
                    if o.get("plotart") and o.type == "MESH" and not o.hide_render}
        sc.frame_set(3)
        self.assertEqual(visible_frames(), {"0001", "0002", "0003"})      # trails accumulate
        sc.frame_set(5)
        self.assertEqual(visible_frames(), {"0004", "0005"})              # image 4 cleared the canvas

    def test_extension_install_and_panel(self):
        import bpy
        from plotart.blender.package import build_addon
        with tempfile.TemporaryDirectory() as tmp:
            sketch = os.path.join(tmp, "s.py")
            with open(sketch, "w", encoding="utf-8") as f:
                f.write('n = param("Anzahl", 5, 1, 20)\nno_stroke()\nfor i in range(n):\n    circle(i * 30, 50, 20)\n')
            zp = build_addon(os.path.join(tmp, "a.zip"))
            bpy.ops.extensions.package_install_files(filepath=str(zp), repo="user_default", enable_on_install=True)
            try:
                st = bpy.context.scene.plotart
                st.source, st.filepath = "FILE", sketch
                self.assertEqual(bpy.ops.plotart.build(), {"FINISHED"})
                sc = bpy.context.scene
                self.assertEqual(sc["plotart: Anzahl"], 5)
                sc["plotart: Anzahl"] = 9
                bpy.ops.plotart.build()
                meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.get("plotart")]
                self.assertEqual(sum(len(o.data.polygons) for o in meshes), 9)
                # draw the panel with a stand-in layout to catch UI errors
                mod = sys.modules[next(m for m in sys.modules if m.endswith(".plotart") and
                                       hasattr(sys.modules[m], "VIEW3D_PT_plotart"))]

                class Layout:
                    def __getattr__(self, name):
                        return lambda *a, **k: self
                mod.VIEW3D_PT_plotart.draw(type("P", (), {"layout": Layout()})(), bpy.context)
            finally:
                bpy.ops.extensions.package_uninstall(repo_index=next(
                    i for i, r in enumerate(bpy.context.preferences.extensions.repos)
                    if r.module == "user_default"), pkg_id="plotart")


if __name__ == "__main__":
    unittest.main()
