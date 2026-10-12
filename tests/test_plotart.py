import random
import unittest
import xml.etree.ElementTree as ET

from plotart import render, random_params, to_svg
from plotart.generators import REGISTRY
from plotart.geometry import clip_polyline
from plotart.optimize import merge_paths, sort_paths

SMALL = {"paper": "A5", "margin": 15}


class GeneratorTests(unittest.TestCase):
    def test_every_generator_renders_inside_margin(self):
        for name in REGISTRY:
            with self.subTest(generator=name):
                d = render(name, seed=3, settings=SMALL)
                self.assertTrue(d.layers, "no paths produced")
                x0, y0, x1, y1 = d.box
                for path in d.all_paths():
                    for x, y in path:
                        self.assertTrue(x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6)
                ET.fromstring(to_svg(d).split("\n", 1)[1])  # well-formed XML

    def test_same_seed_same_svg(self):
        for name in REGISTRY:
            with self.subTest(generator=name):
                a = to_svg(render(name, seed=11, settings=SMALL))
                b = to_svg(render(name, seed=11, settings=SMALL))
                self.assertEqual(a, b)

    def test_random_params_render(self):
        rng = random.Random(1)
        for name in REGISTRY:
            seed = rng.randrange(1000)
            render(name, random_params(name, seed), seed, SMALL)

    def test_params_are_clamped(self):
        d = render("blocks", {"cols": 99999, "fill": "nonsense"}, seed=1, settings=SMALL)
        self.assertEqual(d.meta["params"]["cols"], 140)
        self.assertEqual(d.meta["params"]["fill"], "hatch")

    def test_svg_has_mm_size_and_layers(self):
        d = render("topo", seed=2, settings={"paper": "A4", "orientation": "landscape"})
        svg = to_svg(d)
        self.assertIn('width="297mm" height="210mm"', svg)
        self.assertIn('inkscape:groupmode="layer"', svg)


class GeometryTests(unittest.TestCase):
    def test_clip(self):
        parts = clip_polyline([(-5, 5), (5, 5), (15, 5)], (0, 0, 10, 10))
        self.assertEqual(parts, [[(0.0, 5.0), (5.0, 5.0), (10.0, 5.0)]])

    def test_merge_and_sort(self):
        paths = [[(0, 0), (1, 0)], [(2, 0), (1, 0)], [(10, 10), (11, 10)]]
        merged = merge_paths(paths, 0.01)
        self.assertEqual(len(merged), 2)
        ordered = sort_paths(merged, (12, 10))
        self.assertEqual(ordered[0][0], (11, 10))


if __name__ == "__main__":
    unittest.main()
