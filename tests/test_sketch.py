import importlib.util
import json
import math
import unittest
import xml.etree.ElementTree as ET

from plotart import bridge
from plotart.sketch import execute, list_examples, render_png, render_svg, run_sketch, to_plotter
from plotart.sketch.color import to_color
from plotart.sketch.tools import poisson_disc, polygon_area, voronoi_cells

HAS_NUMPY = importlib.util.find_spec("numpy") is not None
HAS_PIL = importlib.util.find_spec("PIL") is not None


def xml(svg: str):
    return ET.fromstring(svg.split("\n", 1)[1])


class ExampleTests(unittest.TestCase):
    def test_examples_run(self):
        for ex in list_examples():
            if "numpy" in ex["source"] and not HAS_NUMPY:
                continue
            uses_images = any(f in ex["source"] for f in ("load_image", "create_image", "snapshot(", "filter("))
            if uses_images and not HAS_PIL:
                continue
            with self.subTest(example=ex["name"]):
                r = run_sketch(ex["source"], seed=5)
                self.assertIsNone(r["error"], r["error"])
                self.assertGreater(r["items"], 0)
                xml(r["svg"])

    def test_examples_are_deterministic(self):
        src = list_examples()[0]["source"]
        self.assertEqual(run_sketch(src, seed=9)["svg"], run_sketch(src, seed=9)["svg"])
        self.assertNotEqual(run_sketch(src, seed=9)["svg"], run_sketch(src, seed=10)["svg"])


class ApiTests(unittest.TestCase):
    def test_shapes_styles_and_svg(self):
        src = """
size(200, 100)
background("#fff")
fill(255, 0, 0, 128); stroke("navy"); stroke_weight(2)
rect(10, 10, 50, 30, 5)
with push():
    translate(100, 50); rotate(PI / 4)
    fill(linear_gradient(0, 0, 10, 0, ["red", "blue"]))
    ellipse(0, 0, 40, 20)
blend_mode(MULTIPLY)
begin_shape(); vertex(0, 0); bezier_vertex(10, 0, 20, 10, 20, 20); curve_vertex(30, 30); curve_vertex(40, 20)
begin_contour(); vertex(5, 5); vertex(6, 5); vertex(6, 6); end_contour()
end_shape(CLOSE)
text("Hallo", 10, 90)
"""
        sk, log, err, _ = execute(src)
        self.assertIsNone(err, err)
        svg = render_svg(sk)
        root = xml(svg)
        self.assertEqual(root.get("width"), "200")
        self.assertIn("linearGradient", svg)
        self.assertIn('fill-opacity="0.5"', svg)
        self.assertIn("matrix(", svg)
        self.assertIn("mix-blend-mode:multiply", svg)
        self.assertIn('fill-rule="evenodd"', svg)
        self.assertIn(">Hallo</text>", svg)

    def test_mm_paper_and_int_width(self):
        sk, log, err, _ = execute('size("A4")\nprint(type(width).__name__, width, height)')
        self.assertIsNone(err)
        self.assertEqual(log.strip(), "int 210 297")
        self.assertIn('width="210mm"', render_svg(sk))

    def test_params(self):
        src = 'n = param("Anzahl", 10, 1, 50)\nk = param("Art", "a", options=["a", "b"])\nprint(n, k)'
        r = run_sketch(src, {"Anzahl": 999, "Art": "b"})
        self.assertEqual(r["log"].strip(), "50 b")           # clamped to max
        self.assertEqual([p["name"] for p in r["params"]], ["Anzahl", "Art"])
        self.assertEqual(r["params"][1]["kind"], "choice")

    def test_error_reports_line(self):
        r = run_sketch("x = 1\n\nprint(1 / 0)\n")
        self.assertIsNone(r["svg"])
        self.assertEqual(r["error"]["line"], 3)
        self.assertIn("ZeroDivisionError", r["error"]["message"])
        r = run_sketch("circle(1, 2\n")
        self.assertIn("Syntaxfehler", r["error"]["message"])

    def test_colors(self):
        self.assertEqual(to_color(("#1f5fbf",)).hex, "#1f5fbf")
        self.assertEqual(to_color((255, 0, 0, 51)).a, 0.2)
        self.assertEqual(to_color(("tomato",)).hex, "#ff6347")
        self.assertEqual(to_color((0, 100, 100), "hsb").hex, "#ff0000")

    def test_noise_range_and_random(self):
        sk, log, err, _ = execute(
            "v = [noise(i * 0.1, i * 0.07) for i in range(500)]\n"
            "print(min(v) >= 0, max(v) <= 1, random_int(3, 3), random(['x']))")
        self.assertEqual(log.strip(), "True True 3 x")


@unittest.skipUnless(HAS_PIL, "Pillow fehlt")
class ExportTests(unittest.TestCase):
    def test_png_and_plotter(self):
        sk, _, err, _ = execute('size(120, 80)\nbackground(255)\nfill("red")\nstroke("blue")\n'
                                'circle(60, 40, 50)\nno_stroke()\nfill("green")\nrect(0, 0, 20, 20)')
        self.assertIsNone(err)
        png = render_png(sk, scale=2, engine="pillow")
        self.assertTrue(png.startswith(b"\x89PNG"))
        from PIL import Image
        import io
        im = Image.open(io.BytesIO(png)).convert("RGB")
        self.assertEqual(im.size, (240, 160))
        self.assertEqual(im.getpixel((120, 80)), (255, 0, 0))      # circle centre
        self.assertEqual(im.getpixel((10, 10)), (0, 128, 0))       # green square
        d = to_plotter(sk)
        self.assertEqual(sorted(d.colors.values()), ["#0000ff", "#008000"])   # stroke + outlined fill
        self.assertAlmostEqual(d.width, 120 * 25.4 / 96, places=3)

    @unittest.skipUnless(HAS_NUMPY, "numpy fehlt")
    def test_image_from_numpy(self):
        sk, _, err, _ = execute("import numpy as np\nsize(10, 10)\n"
                                "image(np.linspace(0, 1, 100).reshape(10, 10), 0, 0)")
        self.assertIsNone(err, err)
        self.assertIn("data:image/png;base64,", render_svg(sk))


class ToolTests(unittest.TestCase):
    def test_voronoi_covers_area(self):
        import random
        rng = random.Random(1)
        pts = [(rng.uniform(0, 100), rng.uniform(0, 50)) for _ in range(60)]
        cells = voronoi_cells(pts, 0, 0, 100, 50)
        self.assertAlmostEqual(sum(polygon_area(c) for c in cells), 5000, delta=1e-6)

    def test_poisson_min_distance(self):
        import random
        pts = poisson_disc(100, 100, 8, rng=random.Random(2))
        self.assertGreater(len(pts), 60)
        dmin = min(math.dist(a, b) for i, a in enumerate(pts) for b in pts[i + 1:])
        self.assertGreaterEqual(dmin, 8 - 1e-9)


class BridgeTests(unittest.TestCase):
    def test_sketch_commands(self):
        out = json.loads(bridge.call_json("sketch_run", json.dumps({"source": "circle(10, 10, 5)", "seed": 3})))
        self.assertIsNone(out["sketch_error"])
        self.assertTrue(out["svg"].startswith("<?xml"))
        out = json.loads(bridge.call_json("sketch_run", json.dumps({"source": "foo("})))
        self.assertIn("Syntaxfehler", out["sketch_error"]["message"])
        out = json.loads(bridge.call_json("sketch_plotter", json.dumps({"source": "line(0, 0, 50, 50)"})))
        self.assertEqual(out["stats"]["paths"], 1)
        ref = json.loads(bridge.call_json("sketch_reference", "{}"))["reference"]
        names = {e["name"] for g in ref for e in g["entries"]}
        self.assertTrue({"circle", "noise", "param", "voronoi_cells", "PI"} <= names)

    def test_worker_timeout_and_recovery(self):
        from plotart.sketch.worker import SketchWorker
        w = SketchWorker(timeout=2)
        try:
            out = w.call("sketch_run", {"source": "while True:\n    pass"})
            self.assertIn("Abgebrochen", out["error"])
            out = w.call("sketch_run", {"source": "circle(1, 1, 1)"})
            self.assertIsNone(out["sketch_error"])
        finally:
            w.close()


if __name__ == "__main__":
    unittest.main()
