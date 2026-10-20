"""Other languages (I): Processing (.pde) – conversion to plotart Python and running with Processing."""
import ast
import io
import os
import struct
import sys
import tempfile
import unittest
import zlib
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from plotart import bridge
from plotart.languages import processing as P
from plotart.languages.pde_convert import convert_pde
from plotart.sketch import run_sketch
from plotart.sketch.animation import Animation

PDE_EXAMPLES = Path(P.__file__).resolve().parent / "examples"


def body(src):
    """Converted code without the header lines."""
    return "\n".join(l for l in convert_pde(src)["source"].splitlines()[2:] if not l.startswith("# Hinweis"))


def tiny_png(w, h):
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * w for _ in range(h))
    chunk = lambda tag, data: struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class ConvertTests(unittest.TestCase):
    def test_examples_convert_and_run(self):
        for path in sorted(PDE_EXAMPLES.glob("*.pde")):
            with self.subTest(path.name):
                r = convert_pde(path.read_text(encoding="utf-8"))
                self.assertEqual(r["warnings"], [])
                res = run_sketch(r["source"], seed=2)
                self.assertIsNone(res["error"], res["error"])
                self.assertGreater(res["items"], 0)
                if res["animated"]:
                    anim = Animation(r["source"], seed=2)
                    for _ in range(20):
                        self.assertIsNone(anim.next_frame().error)

    def test_statements(self):
        out = body("int n = 10;\nfloat step = width / n;\nint k = 7;\nfloat d = k / 2;\nfloat e = k / 2.0;\n"
                   "for (int i = 0; i <= n; i += 2) { }\nfor (int j = n; j > 0; j--) { }\n"
                   "int[] a = {1, 2, 3};\nfloat[][] g = new float[3][4];\nboolean b = !true && false || k != 3;\n"
                   "x++;\n--y;\nfloat c = (float) k + (int) 2.7;\nString s = \"n=\" + n + \"!\";\n"
                   "color col = #FF8800;\nint h = 0xFF102030;\nchar ch = 'a';\nint t = k > 3 ? 1 : 2;\n")
        for expected in ("step = width // n", "d = k // 2", "e = k / 2.0", "for i in range(0, n + 1, 2):",
                         "for j in range(n, 0, -1):", "a = [1, 2, 3]", "g = [[0.0] * (4) for _ in range(3)]",
                         "b = not True and False or k != 3", "x += 1", "y -= 1", "c = float(k) + int(2.7)",
                         's = "n=" + str(n) + "!"', 'col = "#FF8800"', 'h = "#102030"', 'ch = "a"',
                         "t = 1 if k > 3 else 2"):
            self.assertIn(expected, out)

    def test_control_flow(self):
        out = body("void draw() {\n  if (a) b(); else if (c) { d(); } else e();\n  while (x < 3) x++;\n"
                   "  do { x--; } while (x > 0);\n  switch (x) { case 1: break; }\n}\n")
        self.assertIn("if a:\n        b()\n    elif c:\n        d()\n    else:\n        e()", out)
        self.assertIn("while x < 3:\n        x += 1", out)
        self.assertIn("while True:\n        x -= 1\n        if not (x > 0):\n            break", out)
        self.assertIn("switch", convert_pde("void f() { switch (x) { case 1: break; } }")["warnings"][0])

    def test_functions_globals_events_and_names(self):
        out = body("int count = 0;\nfloat speed;\nvoid setup() { size(400, 300, P3D); smooth(); }\n"
                   "void draw() { count++; float local = 2; local += 1; pushMatrix(); popMatrix(); }\n"
                   "float twice(float v) { return v * 2; }\n"
                   "void mousePressed() { if (mousePressed) speed = map(mouseX, 0, width, 0, 1); println(speed); }\n"
                   "void mouseWheel(MouseEvent event) { speed += event.getCount(); }\n")
        self.assertIn("speed = 0.0", out)
        self.assertIn("createCanvas(400, 300, WEBGL)", out)
        self.assertIn("# smooth()  (in plotart nicht nötig)", out)
        self.assertIn("def draw():\n    global count\n    count += 1", out)
        self.assertNotIn("global local", out)
        self.assertIn("push()\n    pop()", out)
        self.assertIn("def twice(v):\n    return v * 2", out)
        self.assertIn("def mouse_pressed():\n    global speed\n    if mouse_is_pressed:", out)
        self.assertIn("speed = map_range(mouseX, 0, width, 0, 1)", out)
        self.assertIn("print(speed)", out)
        self.assertIn("def mouse_wheel(event):\n    global speed\n    speed += event", out)

    def test_classes_lists_and_vectors(self):
        src = ("ArrayList<Dot> dots = new ArrayList<Dot>();\nvoid setup() { dots.add(new Dot(1, 2)); }\n"
               "void draw() { for (int i = dots.size() - 1; i >= 0; i--) { Dot d = dots.get(i); d.move(); "
               "if (d.dead()) dots.remove(i); } }\n"
               "class Dot {\n  PVector p; PVector v = new PVector(1, 0); int age;\n"
               "  Dot(float x, float y) { p = new PVector(x, y); }\n"
               "  void move() { p.add(v); v.mult(0.9); v.normalize(); age++; this.age += 0; }\n"
               "  boolean dead() { return age > 3 || p.x > width; }\n}\n")
        out = body(src)
        for expected in ("dots = []", "dots.append(Dot(1, 2))", "for i in range(len(dots) - 1, 0 - 1, -1):",
                         "d = dots[i]", "dots.pop(i)", "class Dot:", "def __init__(self, x, y):",
                         "self.v = Vector(1, 0)", "self.age = 0", "self.p = Vector(x, y)",
                         "self.p = self.p + self.v", "self.v = self.v * 0.9", "self.v = self.v.normalize()",
                         "self.age += 1", "return self.age > 3 or self.p.x > width"):
            self.assertIn(expected, out)
        res = run_sketch(convert_pde(src)["source"])
        self.assertIsNone(res["error"], res["error"])

    def test_warnings_and_validity(self):
        r = convert_pde("void draw() { loadPixels(); a[i++] = 1; Foo.bar(); }")
        self.assertTrue(any("loadPixels" in w for w in r["warnings"]))
        self.assertTrue(any("++" in w for w in r["warnings"]))
        ast.parse(convert_pde("// Titel hier\nsize(10, 10);")["source"])
        self.assertTrue(convert_pde("// Titel hier\nsize(10, 10);")["source"].startswith('"""Titel hier"""'))
        broken = convert_pde("void f( { int = ; }")
        self.assertTrue(any("nicht lauffähig" in w for w in broken["warnings"]))

    def test_bridge_and_examples_list(self):
        r = bridge.dispatch("pde_convert", {"source": "size(10, 10);\nint a = 1;", "title": "T"})
        self.assertTrue(r["source"].startswith('"""T"""'))
        names = [e["name"] for e in bridge.dispatch("sketch_examples", {})["pde"]]
        self.assertIn("p01_baelle", names)

    def test_cli_convert(self):
        from plotart import cli
        with tempfile.TemporaryDirectory() as tmp:
            pde = Path(tmp, "kreis.pde")
            pde.write_text("size(50, 50);\nellipse(25, 25, 10, 10);\n", encoding="utf-8")

            def run(*argv):
                with self.assertRaises(SystemExit) as cm, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    cli.main(list(argv))
                return cm.exception.code
            self.assertEqual(run("pde", str(pde)), 0)
            self.assertIn("ellipse(25, 25, 10, 10)", Path(tmp, "kreis.py").read_text(encoding="utf-8"))
            self.assertEqual(run("pde", str(pde)), 1)                 # never overwrites


class P5Tests(unittest.TestCase):
    def test_examples_and_library(self):
        from plotart import web
        ex = bridge.dispatch("sketch_examples", {})["p5"]
        self.assertEqual([e["name"] for e in ex], ["p5_01_stroemung", "p5_02_kacheln"])
        self.assertTrue(all(e["title"].startswith("p5.js:") and "plotart.param(" in e["source"] for e in ex))
        static = Path(web.__file__).resolve().parent / "static"
        self.assertEqual(web.FILES["/vendor/p5.min.js"][0], "vendor/p5.min.js")
        lib = (static / "vendor" / "p5.min.js").read_text(encoding="utf-8")
        self.assertTrue(lib.startswith("/*! p5.js v1.11"))
        self.assertNotIn("</script", lib)                              # it is inlined into the sandboxed iframe
        self.assertIn("Lesser General Public License", (static / "vendor" / "P5-LICENSE").read_text(encoding="utf-8"))
        studio = (static / "studio.html").read_text(encoding="utf-8")
        self.assertIn('sandbox="allow-scripts"', studio)
        self.assertNotIn("allow-same-origin", studio)

    def test_web_build_has_p5(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
        import build_web
        files = build_web.python_files()
        self.assertIn("plotart/languages/examples/p5_01_stroemung.js", files)
        self.assertIn("plotart/languages/examples/p01_baelle.pde", files)


class RTests(unittest.TestCase):
    def test_helpers(self):
        from plotart.languages import r as R
        self.assertEqual([R._r_value(v) for v in (True, 3, 2.5, 'a"b\\c')], ["TRUE", "3", "2.5", '"a\\"b\\\\c"'])
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp, "params.tsv")
            f.write_text("N\tint\t30\t3\t200\t\t\nFarbe\tcolor\t#1f5fbf\t\t\t\t\nP\tchoice\ta\t\t\t\ta\x1fb\n"
                         "Z\tfloat\t0.5\t\t\t\t\nAn\tbool\tTRUE\t\t\t\t\n", encoding="utf-8")
            specs = {s["name"]: s for s in R._parse_specs(f)}
        self.assertEqual((specs["N"]["min"], specs["N"]["max"], specs["N"]["step"], specs["N"]["default"]), (3, 200, 1, 30))
        self.assertEqual(specs["Farbe"]["kind"], "color")
        self.assertEqual(specs["P"]["choices"], [["a", "a"], ["b", "b"]])
        self.assertEqual((specs["Z"]["min"], specs["Z"]["max"]), (0, 1.5))
        self.assertIs(specs["An"]["default"], True)
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp, "Rscript.exe")
            fake.write_text("", encoding="utf-8")
            with mock.patch.dict(os.environ, {"PLOTART_RSCRIPT": str(fake)}):
                self.assertEqual(R.find_rscript(), str(fake))
        with mock.patch.object(R, "find_rscript", return_value=None):
            with self.assertRaises(R.RError) as cm:
                R.run_r("plot(1)")
        self.assertIn("cran.r-project.org", str(cm.exception))

    def test_examples_listed(self):
        ex = bridge.dispatch("sketch_examples", {})["r"]
        self.assertEqual([e["title"] for e in ex][0], "R: Kreise mit Basisgrafik")
        self.assertTrue(all("plotart_param(" in e["source"] for e in ex))

    @unittest.skipUnless(__import__("plotart.languages.r", fromlist=["find_rscript"]).find_rscript(), "R fehlt")
    def test_real_r(self):
        from plotart.languages.r import run_r
        src = ('n <- plotart_param("Anzahl", 10L, 1L, 50L)\nplotart_canvas(300, 200)\n'
               'par(mar = c(1, 1, 1, 1))\nplot(runif(n), runif(n))\ncat("n =", n, "\\n")\n')
        a = run_r(src, {"Anzahl": 7}, seed=3)
        self.assertIsNone(a["error"], a["error"])
        self.assertEqual((len(a["frames"]), a["width"], a["height"]), (1, 300, 200))
        self.assertIn("n = 7", a["log"])
        self.assertEqual(a["params"][0]["name"], "Anzahl")
        self.assertEqual(run_r(src, {"Anzahl": 7}, seed=3)["frames"], a["frames"])        # same seed, same image
        self.assertNotEqual(run_r(src, {"Anzahl": 7}, seed=4)["frames"], a["frames"])
        self.assertEqual(run_r("a <- 1\nb <- fehlt + 1\n")["error"]["line"], 2)
        self.assertEqual(run_r("x <- (1 +\n")["error"]["line"], 2)


class RunTests(unittest.TestCase):
    def test_prepare_and_has_draw(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(P.prepare_sketch("size(10, 10);", tmp), 1)
            code = Path(tmp, f"{P.SKETCH_NAME}.pde").read_text(encoding="utf-8")
            self.assertTrue(code.startswith("void setup() {\nsize(10, 10);\n}"))
            self.assertIn("public class PlotartCapture", code)
            self.assertEqual(P.prepare_sketch("void setup() { }", tmp), 0)
        self.assertTrue(P.has_draw("void draw() {}"))
        self.assertFalse(P.has_draw("void setup() {}"))

    def _fake(self, script):
        """Pretend to be Processing: a Python script gets the same environment."""
        tmp = tempfile.mkdtemp()
        fake = Path(tmp, "fake.py")
        fake.write_text(script, encoding="utf-8")
        return (mock.patch.object(P, "find_processing", return_value=(sys.executable, "cli")),
                mock.patch.object(P, "_command", lambda exe, kind, sketch, build: [sys.executable, str(fake)]))

    def test_frames_and_log(self):
        png = tiny_png(7, 5)
        script = ("import os\nout = os.environ['PLOTART_OUT']\nprint('hallo', os.environ['PLOTART_SEED'], "
                  "os.environ['PLOTART_FRAMES'])\n"
                  f"for i in (1, 2):\n    open(os.path.join(out, f'frame-{{i:05d}}.png'), 'wb').write({png!r})\n")
        a, b = self._fake(script)
        with a, b:
            r = P.run_pde("void draw() {}", frames=2, seed=9)
        self.assertIsNone(r["error"])
        self.assertEqual((len(r["frames"]), r["width"], r["height"]), (2, 7, 5))
        self.assertIn("hallo 9 2", r["log"])
        self.assertIn('width="7"', P.frames_as_svg(r["frames"])[0])

    def test_errors_stop_the_sketch(self):
        script = ("import time\nprint('plotart_skizze.pde:4:0:4:0: ArrayIndexOutOfBoundsException: Index 5', "
                  "flush=True)\ntime.sleep(60)\n")
        a, b = self._fake(script)
        with a, b:
            r = P.run_pde("size(10, 10);\nint[] q = new int[2];\nq[5] = 1;", timeout=30)
        self.assertEqual(r["error"], {"message": "ArrayIndexOutOfBoundsException: Index 5", "line": 3})
        self.assertLess(r["ms"], 15000)                                # stopped long before the timeout
        a, b = self._fake("import time\ntime.sleep(60)\n")
        with a, b:
            r = P.run_pde("void draw() {}", timeout=1)
        self.assertIn("Abgebrochen", r["error"]["message"])

    def test_not_installed(self):
        with mock.patch.object(P, "find_processing", return_value=None):
            with self.assertRaises(P.ProcessingError) as cm:
                P.run_pde("size(10, 10);")
        self.assertIn("processing.org", str(cm.exception))

    @unittest.skipUnless(P.find_processing() and os.environ.get("PLOTART_TEST_PROCESSING"),
                         "echtes Processing nur mit PLOTART_TEST_PROCESSING=1")
    def test_real_processing(self):
        src = (PDE_EXAMPLES / "p02_raster.pde").read_text(encoding="utf-8")
        r = P.run_pde(src)
        self.assertIsNone(r["error"], r["error"])
        self.assertEqual((r["width"], r["height"]), (400, 400))


if __name__ == "__main__":
    unittest.main()
