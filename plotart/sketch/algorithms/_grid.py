"""Uniform spatial hash for fast neighbour queries (pure Python)."""
from __future__ import annotations

import math


class SpatialGrid:
    def __init__(self, cell: float):
        self.cell = max(1e-9, float(cell))
        self.cells: dict = {}

    def key(self, x, y):
        c = self.cell
        return (int(math.floor(x / c)), int(math.floor(y / c)))

    def insert(self, x, y, item):
        self.cells.setdefault(self.key(x, y), []).append(item)

    def remove(self, x, y, item):
        lst = self.cells.get(self.key(x, y))
        if lst:
            try:
                lst.remove(item)
            except ValueError:
                pass

    def near(self, x, y, r=None):
        """Items in the cells overlapping the circle (x, y, r) – r defaults to one cell."""
        c = self.cell
        r = c if r is None else r
        x0, y0 = int(math.floor((x - r) / c)), int(math.floor((y - r) / c))
        x1, y1 = int(math.floor((x + r) / c)), int(math.floor((y + r) / c))
        cells = self.cells
        for gx in range(x0, x1 + 1):
            for gy in range(y0, y1 + 1):
                lst = cells.get((gx, gy))
                if lst:
                    yield from lst

    @classmethod
    def of_points(cls, points, cell):
        g = cls(cell)
        for i, p in enumerate(points):
            g.insert(p[0], p[1], i)
        return g
