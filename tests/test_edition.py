"""Editions & presentation (D): feature(), rarities, metadata, gallery, large-format tiles."""
import importlib.util
import io
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

from plotart import bridge
from plotart.sketch import execute, run_sketch
from plotart.sketch.edition import collect_features, feature_stats, gallery_html, write_edition
from plotart.sketch.tiles import TileError, crop_sketch, plan_tiles, print_size

HAS_PIL = importlib.util.find_spec("PIL") is not None
EXAMPLES = Path(__file__).resolve().parent.parent / "plotart" / "sketch" / "examples"
SRC = ('"""Testedition\nZum Prüfen."""\nsize(60, 40)\n'
       'f = feature("Form", random_choice(["Kreis", "Quadrat"], [3, 1]))\n'
       'g = feature("Gold", random_choice([True, False], [1, 3]))\n'
       'if g:\n    feature("Extra", 1.23456)\nbackground(250)\ncircle(30, 20, 10)\n')


class FeatureTests(unittest.TestCase):
    def test_feature_values(self):
        sk, _, err, _ = execute('a = feature("Gold", False)\nb = feature("Zahl", 0.123456)\n'
                                'c = feature("Liste", [1, 2])\nprint(a, b, c)')
        self.assertIsNone(err, err)
        self.assertEqual(sk.features, {"Gold": "nein", "Zahl": 0.1235, "Liste": "[1, 2]"})
        r = run_sketch('x = feature("Gold", False)\nprint(x is False)')
        self.assertEqual(r["log"].strip(), "True")                    # returned unchanged
        self.assertEqual(r["features"], {"Gold": "nein"})
        self.assertIn("&quot;features&quot;", r["svg"])
        self.assertIn("leer", run_sketch('feature(" ", 1)')["error"]["message"])

    def test_collect_and_stats(self):
        entries, done = collect_features(SRC, range(1, 41))
        self.assertTrue(done)
        self.assertEqual(len(entries), 40)
        part, done = collect_features(SRC, range(1, 41), budget_s=0)
        self.assertFalse(done)
        self.assertEqual(len(part), 1)
        st = feature_stats(entries + [{"seed": 99, "error": "kaputt"}])
        self.assertEqual(st["count"], 40)
        self.assertEqual(sum(v["count"] for v in st["traits"]["Form"]), 40)
        extra = {v["value"]: v["count"] for v in st["traits"]["Extra"]}
        gold = {v["value"]: v["count"] for v in st["traits"]["Gold"]}
        self.assertEqual(extra.get("–", 0), gold["nein"])               # missing trait counts as "–"
        self.assertEqual(st["traits"]["Form"][0]["count"], min(v["count"] for v in st["traits"]["Form"]))
        rarest = min(st["ranks"], key=st["ranks"].get)
        self.assertEqual(st["scores"][rarest], max(st["scores"].values()))

    def test_bridge_command(self):
        r = bridge.dispatch("edition_features", {"source": SRC, "seeds": [1, 2, 3]})
        self.assertTrue(r["done"])
        self.assertEqual([e["seed"] for e in r["entries"]], [1, 2, 3])
        self.assertIn("edition_features", bridge.USER_CODE_COMMANDS)

    def test_metadata_and_gallery(self):
        entries, _ = collect_features(SRC, range(1, 9))
        with tempfile.TemporaryDirectory() as tmp:
            write_edition(tmp, entries, "Titel </script>", "Text", "Künstlerin", {e["seed"]: f"b{e['seed']}.png" for e in entries})
            meta = json.loads((Path(tmp) / "metadata" / "3.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["name"], "Titel </script> #3")
            self.assertEqual(meta["image"], "b3.png")
            self.assertEqual(meta["artist"], "Künstlerin")
            self.assertEqual({a["trait_type"] for a in meta["attributes"]} >= {"Form", "Gold"}, True)
            ed = json.loads((Path(tmp) / "edition.json").read_text(encoding="utf-8"))
            self.assertEqual(ed["count"], 8)
            page = (Path(tmp) / "galerie.html").read_text(encoding="utf-8")
        self.assertEqual(page.count("</script>"), 2)                    # the title cannot close the data block
        self.assertIn("Titel &lt;/script&gt;", page)
        data = re.search(r'<script type="application/json" id="data">(.*?)</script>', gallery_html(ed), re.S).group(1)
        self.assertEqual(json.loads(data)["title"], "Titel </script>")

    @unittest.skipUnless(HAS_PIL, "Pillow fehlt")
    def test_series_writes_edition_and_zip(self):
        from plotart.sketch.series import export_series
        with tempfile.TemporaryDirectory() as tmp:
            res = export_series(SRC, Path(tmp, "s"), [1, 2, 3], zip_path=Path(tmp, "s.zip"), artist="A")
            names = zipfile.ZipFile(Path(tmp, "s.zip")).namelist()
            ed = json.loads(Path(tmp, "s", "edition.json").read_text(encoding="utf-8"))
        self.assertIn("gallery", res)
        self.assertIn("s/metadata/2.json", names)
        self.assertIn("s/galerie.html", names)
        self.assertEqual((ed["title"], ed["description"], ed["artist"]), ("Testedition", "Zum Prüfen.", "A"))
        self.assertEqual(ed["tokens"][0]["image"], "skizze_1.png")


class TileTests(unittest.TestCase):
    def test_plan(self):
        p = plan_tiles(600, 400, "A4")
        self.assertEqual((p["cols"], p["rows"], p["landscape"]), (4, 2, False))     # 8 sheets instead of 9
        t = p["tiles"]
        self.assertTrue(all(abs(x["w"] - t[0]["w"]) < 1e-9 and x["w"] <= p["printable"][0] for x in t))
        last = t[-1]
        self.assertAlmostEqual(last["x"] + last["w"], 600)
        self.assertAlmostEqual(last["y"] + last["h"], 400)
        self.assertAlmostEqual(t[1]["x"], t[0]["w"] - 10)                          # 10 mm overlap
        one = plan_tiles(100, 100, "A4")
        self.assertEqual((one["cols"], one["rows"]), (1, 1))
        with self.assertRaises(TileError):
            plan_tiles(100, 100, "A9")
        with self.assertRaises(TileError):
            plan_tiles(100, 100, "A4", margin=100)

    def test_crop_and_print_size(self):
        sk, _, _, _ = execute("size(200, 100)\nrect(150, 50, 10, 10)\ntranslate(10, 0)\ncircle(0, 0, 4)")
        tile = crop_sketch(sk, 100, 40, 100, 60)
        self.assertEqual((tile.width, tile.height), (100, 60))
        self.assertEqual(tile.items[0].matrix[4:], (-100, -40))
        self.assertEqual(tile.items[1].matrix[4:], (-90, -40))
        self.assertEqual(len(sk.items), 2)                              # the original is untouched
        self.assertEqual(sk.items[0].matrix, None)
        with self.assertRaises(TileError):
            print_size(sk)                                              # pixels need a print width
        self.assertEqual(print_size(sk, 1000), (1000.0, 500.0))
        mm, _, _, _ = execute('size("A3")')
        self.assertEqual(print_size(mm), (297, 420))

    @unittest.skipUnless(HAS_PIL, "Pillow fehlt")
    def test_export_reassembles(self):
        from PIL import Image, ImageChops
        from plotart.sketch.export import render_png
        from plotart.sketch.tiles import export_tiles
        sk, _, _, _ = execute("size(300, 200)\nbackground(240)\nno_stroke()\nfill(200, 40, 40)\n"
                              "rect(40, 30, 220, 140)\nfill(20, 60, 200)\ncircle(150, 100, 120)")
        dpi = 40
        with tempfile.TemporaryDirectory() as tmp:
            res = export_tiles(sk, tmp, "A5", print_width=400, overlap=10, dpi=dpi, title="Test")
            plan = plan_tiles(400, 400 * 200 / 300, "A5")
            self.assertEqual(res["sheets"], len(plan["tiles"]))
            self.assertIn("alle_blaetter.pdf", res["files"])
            svg = Path(tmp, "tafel_1-1.svg").read_text(encoding="utf-8")
            self.assertRegex(svg, r'width="[\d.]+mm" height="[\d.]+mm"')
            px = dpi / 25.4
            m = round(plan["margin"] * px)
            full = Image.open(io.BytesIO(render_png(sk, scale=400 * px / 300))).convert("RGB")
            canvas = Image.new("RGB", full.size)
            for t in plan["tiles"]:
                page = Image.open(Path(tmp, f"tafel_{t['row'] + 1}-{t['col'] + 1}.png")).convert("RGB")
                w, h = round(t["w"] * px), round(t["h"] * px)
                canvas.paste(page.crop((m, m, m + w, m + h)), (round(t["x"] * px), round(t["y"] * px)))
        hist = ImageChops.difference(canvas, full).convert("L").histogram()
        self.assertLess(sum(hist[60:]) / sum(hist), 0.03)              # only seams of half a pixel differ

    @unittest.skipUnless(HAS_PIL, "Pillow fehlt")
    def test_cli(self):
        from contextlib import redirect_stderr, redirect_stdout
        from plotart import cli

        def run(*argv):
            with self.assertRaises(SystemExit) as cm, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                cli.main(list(argv))
            return cm.exception.code
        with tempfile.TemporaryDirectory() as tmp:
            sketch = Path(tmp, "plakat.py")
            sketch.write_text('size("A4")\nbackground(200)\ncircle(105, 148, 100)\n', encoding="utf-8")
            self.assertEqual(run("sketch", str(sketch), "--tiles", "A5", "--dpi", "30", "--no-svg", "--out", tmp), 0)
            self.assertTrue(Path(tmp, "plakat_1_grossformat_A5", "uebersicht.png").exists())
            px_sketch = Path(tmp, "px.py")
            px_sketch.write_text("size(100, 100)\n", encoding="utf-8")
            self.assertEqual(run("sketch", str(px_sketch), "--tiles", "A4", "--out", tmp), 1)


class ExampleTests(unittest.TestCase):
    def test_examples_62_63(self):
        for name in ("62_edition_fenster.py", "63_grossformat_plakat.py"):
            with self.subTest(name):
                r = run_sketch((EXAMPLES / name).read_text(encoding="utf-8"), seed=4)
                self.assertIsNone(r["error"], r["error"])
                self.assertGreater(r["items"], 0)
        r = run_sketch((EXAMPLES / "62_edition_fenster.py").read_text(encoding="utf-8"), seed=4)
        self.assertEqual(set(r["features"]), {"Palette", "Raster", "Stil", "Goldrand"})

    def test_help(self):
        from plotart.sketch.runner import api_reference
        ref = {g["category"]: {e["name"] for e in g["entries"]} for g in api_reference()}
        self.assertIn("feature", ref["Edition"])


if __name__ == "__main__":
    unittest.main()
