"""Stages 7–8: sound & interaction, 3D in sketches, OSC, TouchDesigner, web viewer."""
import base64
import importlib.util
import json
import math
import unittest
from pathlib import Path

from plotart import bridge
from plotart.sketch import execute, run_sketch
from plotart.sketch.animation import Animation

HAS_PIL = importlib.util.find_spec("PIL") is not None
HAS_NUMPY = importlib.util.find_spec("numpy") is not None
EXAMPLES = Path(__file__).resolve().parent.parent / "plotart" / "sketch" / "examples"

CUBE = 'size(400, 400)\nlights()\ntranslate(200, 200)\nrotate_x(0.5)\nrotate_y(0.6)\nfill("#1f5fbf")\nbox(120)\n'


class ThreeDTests(unittest.TestCase):
    def test_cube_projects_three_shaded_faces(self):
        sk, log, err, _ = execute(CUBE)
        self.assertIsNone(err, err)
        faces = [it for it in sk.items if it.data.get("from3d")]
        self.assertEqual(len(faces), 3)                          # back faces culled
        shades = {it.style.fill.hex for it in faces}
        self.assertEqual(len(shades), 3)                         # lit differently
        self.assertEqual(len(sk.meshes3d), 1)
        self.assertEqual(len(sk.meshes3d[0]["faces"]), 6)

    def test_z0_plane_matches_2d_canvas(self):
        # without rotation a plane at z = 0 lands exactly where a 2D rect would be
        sk, _, err, _ = execute('size(300, 200)\nfill(0)\ntranslate(150, 100)\nplane(100, 50)')
        self.assertIsNone(err, err)
        segs = sk.items[0].data["subpaths"][0]
        xs = sorted({round(s[1], 6) for s in segs})
        ys = sorted({round(s[2], 6) for s in segs})
        self.assertEqual(xs, [100, 200])
        self.assertEqual(ys, [75, 125])

    def test_depth_order_and_2d_on_top(self):
        src = ('size(200, 200)\nno_stroke()\ntranslate(100, 100)\nfill(255, 0, 0)\ntranslate(0, 0, 50)\nplane(40)\n'
               'fill(0, 0, 255)\ntranslate(0, 0, -100)\nplane(80)\nreset_matrix()\nfill(0, 255, 0)\ncircle(10, 10, 5)')
        sk, _, err, _ = execute(src)
        self.assertIsNone(err, err)
        fills = [it.style.fill.hex for it in sk.items]
        self.assertEqual(fills, ["#0000ff", "#ff0000", "#00ff00"])   # far → near, then 2D

    def test_lights_reset_per_frame_and_meshes_per_frame(self):
        src = ('animation(frames=2)\ndef draw():\n    background(0)\n    if frame_count == 1:\n        lights()\n'
               '    translate(200, 200)\n    fill(200)\n    box(100)\n')
        a = Animation(src)
        f1, f2 = a.next_frame(), a.next_frame()
        self.assertEqual(len(f1.meshes), 1)
        self.assertEqual(len(f2.meshes), 1)
        lit = {it.style.fill.hex for it in f1.items if it.data.get("from3d")}
        unlit = {it.style.fill.hex for it in f2.items if it.data.get("from3d")}
        self.assertEqual(unlit, {"#c8c8c8"})
        self.assertNotEqual(lit, unlit)

    def test_run_sketch_flag(self):
        self.assertTrue(run_sketch(CUBE)["has3d"])
        self.assertFalse(run_sketch("circle(10, 10, 5)")["has3d"])

    def test_glb_and_obj(self):
        from plotart.sketch.export3d import read_glb
        out = bridge.dispatch("sketch_3d", {"source": CUBE + "stroke(0)\nline3d(0, 0, 0, 0, -100, 0)"})
        glb = base64.b64decode(out["glb_base64"])
        doc = read_glb(glb)
        self.assertEqual(doc["asset"]["version"], "2.0")
        self.assertEqual(len(doc["meshes"]), 2)
        self.assertEqual(doc["meshes"][1]["primitives"][0]["mode"], 1)     # line
        pos = doc["accessors"][doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"]]
        self.assertEqual(pos["count"], 36)                                 # 6 quads → 12 triangles
        self.assertLess(max(abs(v) for v in pos["max"] + pos["min"]), 1.2)  # 120 px ≈ 1.2 m, centred
        obj = base64.b64decode(bridge.dispatch("sketch_3d", {"source": CUBE, "format": "obj"})["obj_base64"]).decode()
        self.assertEqual(obj.count("\nv "), 8)
        self.assertEqual(obj.count("\nf "), 6)
        self.assertIn("error", bridge.dispatch("sketch_3d", {"source": "circle(1, 1, 1)"}))

    def test_hidden_lines(self):
        from plotart.sketch import to_plotter
        sk, _, err, _ = execute('size(400, 400)\nbackground(255)\nstroke(0)\nfill(255)\nrect(50, 50, 200, 200)\n'
                                'rect(150, 150, 200, 200)')
        full = to_plotter(sk, optimize=False).stats()["draw_mm"]
        hidden = to_plotter(sk, optimize=False, hidden_lines=True).stats()["draw_mm"]
        px = 25.4 / 96
        self.assertAlmostEqual(full - hidden, 200 * px, delta=0.1)             # the covered corner (2 × 100 px)

    def test_blender_scene_has_real_meshes(self):
        from plotart.blender.scene import build_scene
        sc = build_scene('size(400, 400)\nbackground(255)\n' + CUBE.split("\n", 1)[1] + 'fill(0)\ncircle(20, 20, 5)')
        shapes = sc["frames"][0]["shapes"]
        types = [s["type"] for s in shapes]
        self.assertEqual(types.count("mesh3d"), 1)
        self.assertEqual(types.count("fill"), 1)                         # projected faces are not duplicated
        bg = next(s for s in shapes if s["type"] == "background")
        dot = next(s for s in shapes if s["type"] == "fill")
        mesh = next(s for s in shapes if s["type"] == "mesh3d")
        zs = [v[2] for v in mesh["verts"]]
        self.assertLess(bg["z_base"], min(zs))                           # background behind the cube
        self.assertGreater(dot["z_base"], max(zs))                       # later 2D in front

    def test_examples_run(self):
        for path in sorted(EXAMPLES.glob("2[5-9]_*.py")):
            with self.subTest(path.name):
                r = run_sketch(path.read_text(encoding="utf-8"))
                self.assertIsNone(r["error"], r["error"])


if __name__ == "__main__":
    unittest.main()
