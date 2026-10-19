"""Stages 4–6: images & data, pixels & filters, curation & series."""
import base64
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from plotart import bridge
from plotart.sketch import data, execute, render_png, render_svg, run_sketch
from plotart.sketch.animation import Animation
from plotart.sketch.core import keyed_value
from plotart.sketchfiles import SketchFileError, SketchFolder

HAS_PIL = importlib.util.find_spec("PIL") is not None
HAS_NUMPY = importlib.util.find_spec("numpy") is not None


class DataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "daten").mkdir()
        data.ASSET_DIRS[:] = [str(self.tmp)]

    def tearDown(self):
        data.ASSET_DIRS[:] = []
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_csv_german_numbers_and_lookup(self):
        (self.tmp / "daten" / "w.csv").write_text("ort;wert;datum\nWien;12,5;2026-01-01\nGraz;1.234,5;x\n",
                                                  encoding="cp1252")
        rows = data.load_csv("w.csv")                      # found in daten/
        self.assertEqual(rows[0], {"ort": "Wien", "wert": 12.5, "datum": "2026-01-01"})
        self.assertEqual(rows[1]["wert"], 1234.5)
        self.assertEqual(data.load_csv("w.csv", numbers=False)[0]["wert"], "12,5")
        with self.assertRaises(data.DataError):
            data.load_csv("fehlt.csv")

    def test_samples(self):
        self.assertEqual(len(data.load_csv("beispiel:temperaturen.csv")), 12)
        self.assertEqual(data.load_csv("beispiel:temperaturen.csv")[0]["monat"], "Jänner")
        self.assertIn("punkte", data.load_json("beispiel:zufall.json"))

    def test_from_sketch(self):
        (self.tmp / "t.json").write_text('{"a": [1, 2, 3]}', encoding="utf-8")
        sk, log, err, _ = execute('print(sum(load_json("t.json")["a"]), len(load_lines("beispiel:gedicht.txt")))')
        self.assertIsNone(err, err)
        self.assertEqual(log.strip(), "6 3")


class SvgImportTests(unittest.TestCase):
    def test_roundtrip_and_shapes(self):
        from plotart.sketch.svgimport import parse_path, parse_svg
        svg = run_sketch('size(100, 50)\nfill("red")\nrect(10, 10, 20, 20)\nno_fill()\ncircle(70, 25, 30)')["svg"]
        d = parse_svg(svg)
        self.assertEqual((d.width, d.height), (100, 50))
        self.assertEqual(len(d.shapes), 2)
        self.assertEqual(d.shapes[0].fill.hex, "#ff0000")
        self.assertIsNone(d.shapes[1].fill)
        # relative commands, implicit lineto, close
        (pts, closed), = parse_path("m10 10 20 0 0 20 z")
        self.assertEqual(pts, [(10, 10), (30, 10), (30, 30)])
        self.assertTrue(closed)
        # semicircle arc ends where it should and passes the top
        (pts, _), = parse_path("M0 0 A10 10 0 0 1 20 0")
        self.assertAlmostEqual(pts[-1][0], 20, 6)
        self.assertLess(min(p[1] for p in pts), -9.9)

    def test_draw_svg_in_sketch(self):
        src = ('size(200, 200)\nsvg = load_svg("beispiel_unbekannt.svg")')
        self.assertIn("nicht gefunden", run_sketch(src)["error"]["message"])
        tmp = tempfile.mkdtemp()
        try:
            Path(tmp, "f.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                                          '<rect width="10" height="10" fill="#00f"/></svg>')
            data.ASSET_DIRS[:] = [tmp]
            r = run_sketch('size(200, 200)\ndraw_svg(load_svg("f.svg"), 0, 0, w=200)')
            self.assertIsNone(r["error"], r["error"])
            self.assertIn('fill="#0000ff"', r["svg"])
        finally:
            data.ASSET_DIRS[:] = []
            shutil.rmtree(tmp)


class FontTests(unittest.TestCase):
    def setUp(self):
        from plotart.sketch.fonts import _font_index
        if not _font_index():
            self.skipTest("keine TrueType-Schrift auf diesem System")

    def test_text_paths(self):
        from plotart.sketch.fonts import text_paths, text_width
        o = text_paths("o", 0, 0, 100)
        self.assertEqual(len(o), 2)                       # outer ring + hole
        xs = [p[0] for c in o for p in c]
        ys = [p[1] for c in o for p in c]
        self.assertTrue(max(ys) <= 2 and min(ys) < -40)   # above the baseline (y down)
        self.assertGreater(max(xs), 30)
        self.assertGreater(len(text_paths("Ä", 0, 0, 100)), 2)    # composite glyph: A + dots
        self.assertAlmostEqual(text_width("ab", 50), text_width("a", 50) + text_width("b", 50), 6)

    def test_text_shape_reaches_plotter(self):
        from plotart.sketch import to_plotter
        sk, _, err, _ = execute('size(300, 100)\nno_fill()\nstroke(0)\ntext_shape("Hi", 10, 80, 60)')
        self.assertIsNone(err, err)
        self.assertGreaterEqual(to_plotter(sk, optimize=False).stats()["paths"], 3)

    def test_portable_font_names(self):
        from plotart.sketch.fonts import find_font
        self.assertEqual(find_font("sans"), find_font(None))
        self.assertTrue(find_font("Sans-Bold").lower().endswith((".ttf", ".ttc")))  # falls back if no bold font


@unittest.skipUnless(HAS_PIL, "Pillow fehlt")
class RasterTests(unittest.TestCase):
    def test_image_access_and_filters(self):
        from plotart.sketch.raster import FILTERS, create_image, load_image
        img = load_image("beispiel:verlauf")
        self.assertLess(img.brightness(10, 2), 0.1)              # gradient: dark at the top …
        self.assertGreater(img.brightness(10, img.height - 2), 0.9)
        self.assertEqual(len(img.grid(4)), 4)
        for f in FILTERS:
            out = img.filter(f)
            self.assertEqual(out.size, img.size, f)
        c = create_image(4, 2, "red")
        c.set(1, 1, "blue")
        self.assertEqual(c.get(1, 1).hex, "#0000ff")
        self.assertEqual(c.get(0, 0).hex, "#ff0000")

    @unittest.skipUnless(HAS_NUMPY, "numpy fehlt")
    def test_pixels_roundtrip(self):
        from plotart.sketch.raster import create_image
        import numpy as np
        img = create_image(3, 2)
        px = img.pixels
        px[..., 0] = 1.0
        px[..., 3] = 1.0
        img.set_pixels(px)
        self.assertEqual(img.get(2, 1).hex, "#ff0000")
        self.assertTrue(np.allclose(img.pixels[..., 0], 1.0))

    def test_canvas_filter_snapshot_and_builtin_filter(self):
        r = run_sketch('size(50, 50)\nbackground(255)\nfill(0)\nrect(0, 0, 25, 50)\nfilter(INVERT)\n'
                       'print(list(filter(None, [0, 1, 2])))')
        self.assertIsNone(r["error"], r["error"])
        self.assertEqual(r["items"], 1)                          # canvas became one image
        self.assertIn("[1, 2]", r["log"])
        sk, _, err, _ = execute('size(50, 50)\nbackground(255)\nfill(0)\nrect(0, 0, 25, 50)\nfilter(INVERT)')
        from PIL import Image
        im = Image.open(io.BytesIO(render_png(sk, engine="pillow"))).convert("RGB")
        self.assertEqual(im.getpixel((5, 25)), (255, 255, 255))   # black became white
        self.assertEqual(im.getpixel((45, 25)), (0, 0, 0))

    def test_rotated_image_matches_geometry(self):
        from PIL import Image
        sk, _, err, _ = execute('size(100, 100)\nbackground(255)\nimg = create_image(40, 10, "black")\n'
                                'translate(50, 50)\nrotate(HALF_PI)\nimage(img, -20, -5)')
        self.assertIsNone(err, err)
        im = Image.open(io.BytesIO(render_png(sk, engine="pillow"))).convert("L")
        self.assertLess(im.getpixel((50, 30)), 40)      # rotated bar is vertical …
        self.assertGreater(im.getpixel((30, 50)), 220)  # … not horizontal


class KeyframeTests(unittest.TestCase):
    def test_interpolation(self):
        keys = [[1, 0], [11, 100]]
        self.assertEqual(keyed_value(keys, 1), 0)
        self.assertEqual(keyed_value(keys, 6), 50)              # eased midpoint
        self.assertLess(keyed_value(keys, 3), 20)               # slow start
        self.assertEqual(keyed_value(keys, 99), 100)
        self.assertEqual(keyed_value([[1, "a"], [5, "b"]], 4), "a")
        self.assertIsInstance(keyed_value([[1, 0], [3, 10]], 2), int)

    def test_animation_uses_keys(self):
        src = 'animation(frames=3)\ndef draw():\n    print(param("x", 1.0, 0, 10))\n'
        a = Animation(src, {"__keys__": {"x": [[1, 0.0], [3, 10.0]]}})
        logs = []
        while (f := a.next_frame()) is not None:
            logs.append(f.log.strip())
        self.assertEqual(logs, ["0.0", "5.0", "10.0"])


@unittest.skipUnless(HAS_PIL, "Pillow fehlt")
class SeriesTests(unittest.TestCase):
    def test_series_with_sheet(self):
        from plotart.sketch.series import export_series
        tmp = Path(tempfile.mkdtemp())
        try:
            src = 'size(60, 40)\nif seed == 3:\n    1 / 0\nbackground(random_int(255))'
            res = export_series(src, tmp / "s", [1, 2, 3], formats=("png", "svg", "plotter"),
                                zip_path=tmp / "s.zip", stem="t")
            self.assertEqual((res["count"], res["errors"]), (3, 1))
            names = sorted(p.name for p in (tmp / "s").iterdir())
            self.assertIn("kontaktbogen.png", names)
            self.assertIn("t_2_plotter.svg", names)
            meta = json.loads((tmp / "s" / "serie.json").read_text(encoding="utf-8"))
            self.assertIn("error", meta["varianten"][2])
            self.assertTrue((tmp / "s.zip").exists())
        finally:
            shutil.rmtree(tmp)

    def test_thumb_command(self):
        out = bridge.sketch_thumb({"source": "size(100, 50)\nbackground(0)", "seed": 4, "size": 40})
        self.assertEqual(out["seed"], 4)
        self.assertTrue(base64.b64decode(out["png_base64"]).startswith(b"\x89PNG"))


class SketchFolderHistoryTests(unittest.TestCase):
    def test_history_and_favorites(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = SketchFolder(tmp)
            f.save("a.py", "v1")
            f.save("a.py", "v1")                          # unchanged → no new version
            f.save("a.py", "v2")
            f.save("a.py", "v3")
            versions = f.history("a.py")
            self.assertEqual(len(versions), 2)
            self.assertEqual(f.history_load("a.py", versions[0]["version"])["source"], "v2")   # newest first
            with self.assertRaises(SketchFileError):
                f.history_load("a.py", "../../a.py")
            self.assertEqual(f.meta_load("a.py"), {"favorites": []})
            f.meta_save("a.py", {"favorites": [{"seed": 3}]})
            self.assertEqual(f.meta_load("a.py")["favorites"][0]["seed"], 3)
            self.assertEqual([x["name"] for x in f.list()], ["a.py"])          # hidden folder not listed

    def test_quick_saves_keep_every_version_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = SketchFolder(tmp)
            for i in range(11):                           # well within one second
                f.save("b.py", f"v{i}")
            versions = f.history("b.py")
            self.assertEqual([f.history_load("b.py", v["version"])["source"] for v in versions],
                             [f"v{i}" for i in range(9, -1, -1)])          # all 10 kept, newest first


if __name__ == "__main__":
    unittest.main()
