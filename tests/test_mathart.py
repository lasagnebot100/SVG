"""Mathe-Kunst (II): curves, function plots & integration, ODEs & attractors, fractals, domain colouring."""
import importlib.util
import math
import random
import unittest
from pathlib import Path
from unittest import mock

from plotart.sketch import run_sketch
from plotart.sketch.algorithms import mathart
from plotart.sketch.algorithms.mathart import (ATTRACTORS, Epicycles, Graph, attractor, colorize, density,
                                               domain_coloring, fit_points, formula, fourier_approx, fractal_flame,
                                               harmonograph, ifs, integrate, julia, lissajous, mandelbrot,
                                               newton_fractal, phase_portrait, riemann, rk4, rose, spirograph,
                                               superformula)

HAS_NUMPY = importlib.util.find_spec("numpy") is not None
EXAMPLES = Path(__file__).resolve().parent.parent / "plotart" / "sketch" / "examples"


def pixel(field, x, y):
    v = field[y][x]
    return tuple(float(c) for c in v) if hasattr(v, "__len__") else float(v)


class CurveTests(unittest.TestCase):
    def test_closed_curves(self):
        for pts in (rose(5, 1), rose(7, 3), rose(2, 1), spirograph(96, 36, 50), spirograph(96, 40, 30, kind="epi"),
                    lissajous(3, 2)):
            self.assertLess(math.dist(pts[0], pts[-1]), 1e-6)
        with self.assertRaises(ValueError):
            spirograph(kind="seitlich")

    def test_superformula_circle_and_size(self):
        circle = superformula(0, 1, 1, 1, cx=10, cy=20, r=50)
        self.assertTrue(all(abs(math.dist(p, (10, 20)) - 50) < 1e-9 for p in circle))
        star = superformula(5, 0.3, 0.3, 0.3, r=80)
        self.assertAlmostEqual(max(math.hypot(x, y) for x, y in star), 80, 6)

    def test_harmonograph_is_seeded(self):
        a = harmonograph(steps=500, rng=random.Random(4))
        self.assertEqual(a, harmonograph(steps=500, rng=random.Random(4)))
        self.assertNotEqual(a, harmonograph(steps=500, rng=random.Random(5)))
        self.assertTrue(all(abs(x) <= 100 + 1e-9 and abs(y) <= 100 + 1e-9 for x, y in a))

    def test_epicycles(self):
        square = [(0, 0), (100, 0), (100, 100), (0, 100)]
        full = Epicycles(square)
        ring = mathart._resample_closed(square, 256)
        self.assertLess(max(math.dist(full.point(k / 256), p) for k, p in enumerate(ring)), 1e-9)
        few = Epicycles(square, terms=3)
        self.assertEqual(len(few), 3)
        self.assertEqual(len(few.circles(0.3)), 3)
        c = few.circles(0.25)
        self.assertGreaterEqual(c[0][2], c[1][2])                   # strongest circle first
        self.assertEqual(len(fourier_approx(square, 4, steps=100)), 101)
        self.assertEqual(len(full.path(0.5, steps=100)), 51)


class GraphFormulaTests(unittest.TestCase):
    def test_mapping_axes_labels(self):
        g = Graph(-1, 3, -2, 2, 10, 20, 400, 200)
        self.assertEqual(g.pt(-1, 2), (10, 20))
        self.assertEqual(g.pt(3, -2), (410, 220))
        self.assertEqual(len(g.curve(math.tan, 0, 3)), 2)           # broken at the pole π/2
        labels = {s for _, _, s in g.labels(1)}
        self.assertEqual(labels, {"-1", "1", "2", "3", "-2"})
        self.assertGreater(len(g.axes(1)), 2)
        self.assertEqual(g.area(lambda x: 1, 0, 1, steps=4)[0], g.pt(0, 0))

    def test_formula(self):
        f = formula("sin(x)^2 + ln(e)")
        self.assertAlmostEqual(f(math.pi / 2), 2.0)
        self.assertAlmostEqual(formula("z^2 + 1", "z")(1j), 0)
        self.assertAlmostEqual(formula("exp(i*pi)", "z")(0), -1)
        with self.assertRaises(ValueError):
            formula("open('x')")
        with self.assertRaises(ValueError):
            formula("sin(x")


class IntegrationTests(unittest.TestCase):
    def test_rules_on_sine(self):
        expected = {"links": 1.974232, "rechts": 1.974232, "mitte": 2.012909, "trapez": 1.974232,
                    "simpson": 2.000269}
        for rule, value in expected.items():
            r = riemann(math.sin, 0, math.pi, 8, rule)
            self.assertAlmostEqual(r.value, value, 6)
            self.assertAlmostEqual(r.exact, 2.0, 9)
            self.assertEqual(len(r.shapes), 4 if rule == "simpson" else 8)
            self.assertEqual(len(r.error_shapes), len(r.shapes))

    def test_simpson_exact_for_cubics_and_odd_n(self):
        r = riemann(lambda x: x ** 3 - x, 0, 2, 3, "simpson")
        self.assertEqual(r.n, 4)
        self.assertAlmostEqual(r.value, 2.0, 12)
        self.assertAlmostEqual(integrate(lambda x: x * x, 0, 3), 9.0, 9)
        with self.assertRaises(ValueError):
            riemann(math.sin, 0, 1, 4, "zufall")


class OdeTests(unittest.TestCase):
    def test_rk4(self):
        self.assertAlmostEqual(rk4(lambda t, y: y, 1.0, 0, 1, 0.01)[-1][1], math.e, 8)
        end = rk4(lambda t, v: (v[1], -v[0]), (1.0, 0.0), 0, math.tau, 0.01)[-1]
        self.assertAlmostEqual(end[1][0], 1.0, 6)                      # one full oscillation
        self.assertAlmostEqual(end[0], math.tau, 9)

    def test_phase_portrait_stays_in_range(self):
        paths = phase_portrait(lambda x, y: (y, -x), -2, 2, -2, 2, n=4, steps=100)
        self.assertEqual(len(paths), 16)
        for p in paths:
            self.assertTrue(all(-2.2 <= x <= 2.2 and -2.2 <= y <= 2.2 for x, y in p))

    def test_attractors(self):
        for name, (kind, *_rest) in ATTRACTORS.items():
            with self.subTest(name):
                pts = attractor(name, 2000)
                self.assertEqual(len(pts), 2000)
                self.assertEqual(len(pts[0]), 3 if kind == "ode" else 2)
                self.assertTrue(all(math.isfinite(c) and abs(c) < 100 for p in pts for c in p))
        self.assertNotEqual(attractor("clifford", 50), attractor("clifford", 50, a=-1.7))
        with self.assertRaises(ValueError):
            attractor("unbekannt")
        with self.assertRaises(ValueError):
            attractor("lorenz", 10, zeta=1)

    def test_fit_points_and_density(self):
        pts = fit_points([(0, 0, "a"), (2, 1, "b")], 10, 10, 100, 100)
        self.assertEqual(pts, [(10.0, 35.0, "a"), (110.0, 85.0, "b")])
        self.assertEqual(fit_points([(0, 0), (1, 1)], 0, 0, 10, 10, flip_y=True)[0], (0.0, 10.0))
        d = density([(1.5, 1.5)] * 4 + [(3, 0), (99, 99)], 5, 4)
        self.assertEqual((len(d), len(d[0])), (4, 5))
        self.assertAlmostEqual(pixel(d, 1, 1), 1.0)
        self.assertEqual(pixel(d, 0, 0), 0.0)


class FractalTests(unittest.TestCase):
    def test_mandelbrot_and_julia(self):
        m = mandelbrot(40, 30, (-0.6, 0), 1, 100)
        self.assertEqual((len(m), len(m[0])), (30, 40))
        self.assertEqual(pixel(m, 20, 15), 1.0)                      # inside the main cardioid
        self.assertLess(pixel(m, 0, 0), 0.2)                          # far outside, escapes quickly
        j = julia(30, 30, (-0.8, 0.156), max_iter=80)
        self.assertEqual((len(j), len(j[0])), (30, 30))
        self.assertLess(pixel(j, 0, 0), 0.2)

    @unittest.skipUnless(HAS_NUMPY, "numpy fehlt")
    def test_numpy_and_pure_python_agree(self):
        fast = mandelbrot(30, 20, (-0.6, 0.1), 2, 60)
        fast_dc = domain_coloring(lambda z: z * z - 1, 12, 12)
        with mock.patch.object(mathart, "_np", lambda: None):
            slow = mandelbrot(30, 20, (-0.6, 0.1), 2, 60)
            slow_dc = domain_coloring(lambda z: z * z - 1, 12, 12)
        self.assertLess(max(abs(fast[y][x] - slow[y][x]) for y in range(20) for x in range(30)), 1e-6)
        self.assertLess(max(abs(a - b) for y in range(12) for x in range(12)
                            for a, b in zip(fast_dc[y][x], slow_dc[y][x])), 1e-6)

    def test_newton_colours_follow_roots(self):
        img = newton_fractal(41, 41, 3, ["#ff0000", "#00ff00", "#0000ff"], zoom=1)
        r, g, b = pixel(img, 34, 20)                                  # near z = 1 (root 0, red)
        self.assertGreater(r, max(g, b))

    def test_colorize(self):
        out = colorize([[0.0, 0.5, 1.0]], ["#000000", "#ffffff"], inside="#ff0000")
        self.assertEqual(pixel(out, 0, 0), (0.0, 0.0, 0.0))
        self.assertEqual(pixel(out, 2, 0), (1.0, 0.0, 0.0))
        self.assertAlmostEqual(pixel(out, 1, 0)[0], 0.5, 1)
        banded = colorize([[0.5]], ["#000000", "#ffffff"], cycles=2)          # 0.5·2 → white end
        self.assertAlmostEqual(pixel(banded, 0, 0)[0], 1.0, 2)

    def test_ifs_and_flame(self):
        fern = ifs("farn", 3000, rng=random.Random(1))
        self.assertEqual(len(fern), 3000)
        self.assertEqual(fern, ifs("farn", 3000, rng=random.Random(1)))
        self.assertTrue(all(-3 < x < 3 and -0.1 < y < 10.1 for x, y, _ in fern))
        self.assertEqual({k for *_, k in ifs("sierpinski", 500, rng=random.Random(2))}, {0, 1, 2})
        with self.assertRaises(ValueError):
            ifs("unbekannt", 10, rng=random.Random(1))
        flame = fractal_flame(30, 20, 5000, rng=random.Random(3))
        self.assertEqual((len(flame), len(flame[0]), len(flame[0][0])), (20, 30, 4))
        alphas = [float(flame[y][x][3]) for y in range(20) for x in range(30)]
        self.assertTrue(all(0 <= a <= 1 for a in alphas) and max(alphas) > 0.99)
        with self.assertRaises(ValueError):
            fractal_flame(10, 10, 100, variations=["gibtsnicht"], rng=random.Random(1))

    def test_domain_coloring(self):
        img = domain_coloring(lambda z: z, 21, 21, style="klassisch")
        self.assertLess(sum(pixel(img, 10, 10)), 0.3)                 # zero of f(z) = z is dark
        self.assertEqual(pixel(domain_coloring(lambda z: 1 / z, 3, 3, -1, 1, -1, 1), 1, 1), (1.0, 1.0, 1.0))
        for style in ("phase", "raster"):
            self.assertEqual(len(domain_coloring(formula("sin(z)", "z"), 8, 6, style=style)), 6)
        with self.assertRaises(ValueError):
            domain_coloring(lambda z: z, 4, 4, style="bunt")


class ExampleTests(unittest.TestCase):
    def test_examples_51_to_58(self):
        for path in sorted(EXAMPLES.glob("5[1-8]_*.py")):
            with self.subTest(path.name):
                r = run_sketch(path.read_text(encoding="utf-8"), seed=3)
                self.assertIsNone(r["error"], r["error"])
                self.assertGreater(r["items"], 0)

    def test_tools_in_help(self):
        from plotart.sketch.runner import api_reference
        ref = {g["category"]: {e["name"] for e in g["entries"]} for g in api_reference()}
        self.assertTrue({"mandelbrot", "riemann", "Epicycles", "Graph", "attractor"} <= ref["Mathe-Kunst"])


if __name__ == "__main__":
    unittest.main()
