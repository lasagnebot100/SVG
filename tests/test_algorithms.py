"""Algorithm toolkit (B): growth, simulation, patterns."""
import importlib.util
import math
import random
import unittest
from pathlib import Path

from plotart.sketch import run_sketch
from plotart.sketch.algorithms.growth import DLA, DifferentialGrowth, SpaceColonization
from plotart.sketch.algorithms.patterns import (_expand_tiles, circle_packing, contour_lines, delaunay, join_paths,
                                                lsystem, streamlines, tile_paths, truchet, tsp_path, turtle,
                                                wave_function_collapse)
from plotart.sketch.algorithms.simulation import Flock, Life, Physics, elementary_ca, reaction_diffusion

HAS_NUMPY = importlib.util.find_spec("numpy") is not None
HAS_PIL = importlib.util.find_spec("PIL") is not None
EXAMPLES = Path(__file__).resolve().parent.parent / "plotart" / "sketch" / "examples"


def circle(n, r=50, cx=200, cy=200):
    return [(cx + r * math.cos(math.tau * i / n), cy + r * math.sin(math.tau * i / n)) for i in range(n)]


class GrowthTests(unittest.TestCase):
    def test_differential_growth(self):
        g = DifferentialGrowth(circle(20), max_edge=5, bounds=(0, 0, 400, 400), rng=random.Random(1))
        n0 = len(g)
        g.step(40)
        self.assertGreater(len(g), n0)
        pts = g.points
        self.assertTrue(all(0 <= x <= 400 and 0 <= y <= 400 for x, y in pts))
        edges = [math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
        self.assertLessEqual(max(edges), 5 * 1.6)                     # long edges keep getting split
        g2 = DifferentialGrowth(circle(20), max_edge=5, bounds=(0, 0, 400, 400), rng=random.Random(1)).step(40)
        self.assertEqual(g2.points, pts)                                # deterministic

    def test_differential_growth_open_line_keeps_ends(self):
        g = DifferentialGrowth([(0, 0), (100, 0)], closed=False, max_edge=4, rng=random.Random(2)).step(30)
        self.assertEqual(g.points[0], (0.0, 0.0))
        self.assertEqual(g.points[-1], (100.0, 0.0))

    def test_dla(self):
        d = DLA(seeds=[(0, 0)], step=2, rng=random.Random(3)).grow(300)
        self.assertEqual(len(d.particles), 301)
        for x, y, k in d.particles[1:]:
            px, py, _ = d.particles[k]
            self.assertAlmostEqual(math.hypot(x - px, y - py), 2.0, 6)   # glued exactly one step away
        self.assertEqual(len(d.segments), 300)
        self.assertEqual(max(d.depths()) > 5, True)

    def test_space_colonization_with_trunk(self):
        r = random.Random(4)
        lights = [(r.uniform(-100, 100), r.uniform(-300, -150)) for _ in range(200)]
        sc = SpaceColonization(lights, [(0, 0)], segment=5, influence=40, kill=8).grow(500)
        self.assertLess(len(sc.attractors), 20)                         # trunk grew up into the crown
        br = sc.branches
        self.assertGreater(len(br), 50)
        thick = max(b[4] for b in br)
        self.assertEqual(br[0][4], thick)                              # the first segment carries everything


class SimulationTests(unittest.TestCase):
    def test_physics_rope(self):
        w = Physics(gravity=(0, 0.5), iterations=20)
        ids = w.rope(0, 0, 100, 0, segments=10)
        w.step(300)
        first = w.particles[ids[0]]
        self.assertEqual(first.pos, (0.0, 0.0))                        # pinned
        last = w.particles[ids[-1]]
        self.assertGreater(last.y, 80)                                 # hangs down
        total = sum(math.dist(w.particles[a].pos, w.particles[b].pos) for a, b, *_ in w.springs)
        self.assertAlmostEqual(total, 100, delta=5)                    # springs keep their length

    def test_physics_tearing(self):
        w = Physics()
        a, b = w.add(0, 0, pinned=True), w.add(10, 0)
        w.spring(a, b, tear=2)
        w.particles[b].x = 50
        w.particles[b].px = 50
        w.step()
        self.assertEqual(w.springs, [])

    def test_flock(self):
        f = Flock(50, 200, 100, rng=random.Random(5))
        f.step(20)
        self.assertEqual(len(f.boids), 50)
        for b in f.boids:
            self.assertTrue(0 <= b.x < 200 and 0 <= b.y < 100)
            self.assertLessEqual(b.speed, f.max_speed + 1e-9)

    def test_elementary_ca(self):
        rows = elementary_ca(90, 9, 4)
        self.assertEqual(rows[1], [0, 0, 0, 1, 0, 1, 0, 0, 0])         # Sierpinski
        self.assertEqual(rows[2], [0, 0, 1, 0, 0, 0, 1, 0, 0])
        rows = elementary_ca(30, 7, 2)
        self.assertEqual(rows[1], [0, 0, 1, 1, 1, 0, 0])

    def test_life(self):
        blinker = [[0] * 5 for _ in range(5)]
        for x in (1, 2, 3):
            blinker[2][x] = 1
        lf = Life(5, 5, cells=blinker)
        lf.step()
        self.assertEqual([lf.cells[y][2] for y in (1, 2, 3)], [1, 1, 1])
        self.assertEqual(lf.population, 3)
        lf.step()
        self.assertEqual(lf.cells, blinker)
        self.assertEqual(lf.age[2][2], 3)                              # the centre lived all three generations
        hl = Life(5, 5, cells=blinker, rule="23/36")                   # S/B notation
        self.assertEqual((hl.born, hl.survive), ({3, 6}, {2, 3}))

    @unittest.skipUnless(HAS_NUMPY, "numpy fehlt")
    def test_reaction_diffusion(self):
        f = reaction_diffusion(40, 30, 200, rng=random.Random(1))
        self.assertEqual(f.shape, (30, 40))
        self.assertTrue(0 <= f.min() <= f.max() <= 1)


class PatternTests(unittest.TestCase):
    def test_wfc_edges_match(self):
        for tileset in ("rohre", "platine"):
            grid = wave_function_collapse(10, 8, tileset, rng=random.Random(2))
            tiles = _expand_tiles(tileset)
            for r in range(8):
                for c in range(10):
                    s = tiles[grid[r][c]][0]
                    if c < 9:
                        self.assertEqual(s[1], tiles[grid[r][c + 1]][0][3])
                    if r < 7:
                        self.assertEqual(s[2], tiles[grid[r + 1][c]][0][0])
                    if c == 0:
                        self.assertEqual(s[3], 0)                      # no open ends at the border
            self.assertTrue(tile_paths(grid, tileset, 10))

    def test_truchet_and_join(self):
        arcs = truchet(6, 6, 10, rng=random.Random(1))
        self.assertEqual(len(arcs), 72)
        joined = join_paths(arcs)
        self.assertLess(len(joined), len(arcs))
        self.assertEqual(sum(len(p) - 1 for p in joined), sum(len(p) - 1 for p in arcs))   # nothing lost

    def test_delaunay(self):
        pts = [(x * 10.0, y * 10.0 + (x % 2) * 3) for x in range(6) for y in range(5)]
        tris = delaunay(pts)

        def area(a, b, c):
            return abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2

        def hull(ps):                                                  # monotone chain
            ps = sorted(set(ps))
            def half(seq):
                h = []
                for q in seq:
                    while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (q[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (q[0] - h[-2][0]) <= 0:
                        h.pop()
                    h.append(q)
                return h
            return half(ps)[:-1] + half(ps[::-1])[:-1]
        H = hull(pts)
        hull_area = sum(area(H[0], H[i], H[i + 1]) for i in range(1, len(H) - 1))
        self.assertAlmostEqual(sum(area(pts[a], pts[b], pts[c]) for a, b, c in tris), hull_area, 6)  # no gaps/overlaps
        for a, b, c in tris:                                           # empty circumcircles
            (ax, ay), (bx, by), (cx, cy) = pts[a], pts[b], pts[c]
            D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
            ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / D
            uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / D
            r2 = (ax - ux) ** 2 + (ay - uy) ** 2
            for i, (x, y) in enumerate(pts):
                if i not in (a, b, c):
                    self.assertGreaterEqual((x - ux) ** 2 + (y - uy) ** 2, r2 - 1e-6)

    def test_tsp(self):
        r = random.Random(7)
        pts = [(r.random() * 100, r.random() * 100) for _ in range(300)]
        tour = tsp_path(pts, max_seconds=1)
        self.assertEqual(sorted(tour), sorted(pts))
        length = sum(math.dist(tour[i], tour[i + 1]) for i in range(len(tour) - 1))
        self.assertLess(length, 0.9 * math.sqrt(300 * 100 * 100))       # well below a random tour

    def test_contours(self):
        field = [[math.hypot(x - 20, y - 20) for x in range(41)] for y in range(41)]
        lines = contour_lines(field, 10)
        self.assertEqual(len(lines), 1)
        ring = lines[0]
        self.assertLess(math.dist(ring[0], ring[-1]), 1e-6)            # closed
        for x, y in ring:
            self.assertAlmostEqual(math.hypot(x - 20, y - 20), 10, delta=0.2)

    def test_streamlines_keep_distance(self):
        lines = streamlines(lambda x, y: 0.3, 200, 200, spacing=10, rng=random.Random(1))
        self.assertGreater(len(lines), 10)
        pts = [(i, p) for i, l in enumerate(lines) for p in l[::5]]
        close = min(math.dist(p, q) for i, p in pts for j, q in pts if i < j)
        self.assertGreater(close, 10 * 0.6 * 0.9)

    def test_lsystem_turtle(self):
        koch = lsystem("F", {"F": "F+F-F-F+F"}, 2, rng=random.Random(1))
        self.assertEqual(len(koch), 49)
        lines = turtle(koch, 0, 0, heading=0, step=1, angle=90)
        self.assertEqual(len(lines), 1)
        self.assertAlmostEqual(lines[0][-1][0], 9.0, 6)                # Koch curve level 2: 9 units wide
        tree = turtle("F[+F]F", 0, 0, step=10)
        self.assertEqual(len(tree), 2)                                 # trunk + one branch
        rnd = lsystem("X", {"X": [("A", 1), ("B", 1)]}, 1, rng=random.Random(1))
        self.assertIn(rnd, ("A", "B"))

    def test_circle_packing(self):
        cs = circle_packing(200, 200, 2, 30, 2000, padding=1, rng=random.Random(3))
        self.assertGreater(len(cs), 40)
        for i in range(len(cs)):
            x, y, r = cs[i]
            self.assertTrue(r <= x <= 200 - r and r <= y <= 200 - r)
            for j in range(i):
                X, Y, R = cs[j]
                self.assertGreaterEqual(math.hypot(x - X, y - Y), r + R + 1 - 1e-9)


class ExampleTests(unittest.TestCase):
    def test_examples_36_to_50(self):
        for path in sorted(EXAMPLES.glob("[345][0-9]_*.py")):
            if not 36 <= int(path.name[:2]) <= 50:
                continue
            src = path.read_text(encoding="utf-8")
            if ("load_image" in src and not HAS_PIL) or ("reaction_diffusion" in src and not HAS_NUMPY):
                continue
            with self.subTest(path.name):
                r = run_sketch(src, seed=3)
                self.assertIsNone(r["error"], r["error"])
                self.assertGreater(r["items"], 0)

    def test_tools_in_help(self):
        from plotart.sketch.runner import api_reference
        cats = {g["category"]: [e["name"] for e in g["entries"]] for g in api_reference()}
        self.assertIn("DifferentialGrowth", cats["Wachstum"])
        self.assertIn("Flock", cats["Simulation"])
        self.assertIn("wave_function_collapse", cats["Muster"])


if __name__ == "__main__":
    unittest.main()
