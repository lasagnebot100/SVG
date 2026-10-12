"""The Drawing container: paper, margins, pen, layers of polylines."""
from __future__ import annotations

import math

from . import geometry as geo
from .geometry import Path
from .optimize import merge_paths, simplify, sort_paths

# width x height in mm (portrait)
PAPER_SIZES: dict[str, tuple[float, float]] = {
    "A6": (105, 148),
    "A5": (148, 210),
    "A4": (210, 297),
    "A3": (297, 420),
    "A2": (420, 594),
    "A1": (594, 841),
    "Letter": (215.9, 279.4),
    "30x40": (300, 400),
    "50x70": (500, 700),
    "Quadrat 30": (300, 300),
}


class Drawing:
    def __init__(self, width: float, height: float, margin: float = 20.0,
                 pen_width: float = 0.45):
        self.width = float(width)
        self.height = float(height)
        self.margin = float(margin)
        self.pen_width = float(pen_width)
        self.layers: dict[int, list[Path]] = {}
        self.colors: dict[int, str] = {1: "#1f5fbf", 2: "#d2412f"}
        self.meta: dict = {}

    # --- geometry of the sheet -------------------------------------------------
    @property
    def box(self) -> tuple[float, float, float, float]:
        m = self.margin
        return (m, m, self.width - m, self.height - m)

    @property
    def inner_width(self) -> float:
        return self.width - 2 * self.margin

    @property
    def inner_height(self) -> float:
        return self.height - 2 * self.margin

    @property
    def center(self) -> tuple[float, float]:
        return (self.width / 2, self.height / 2)

    # --- adding geometry ----------------------------------------------------------
    def add(self, path: Path, layer: int = 1) -> None:
        if len(path) >= 2:
            self.layers.setdefault(layer, []).append(list(path))

    def line(self, x0: float, y0: float, x1: float, y1: float, layer: int = 1) -> None:
        self.add([(x0, y0), (x1, y1)], layer)

    def rect(self, x0: float, y0: float, x1: float, y1: float, layer: int = 1) -> None:
        self.add(geo.rect(x0, y0, x1, y1), layer)

    def circle(self, cx: float, cy: float, r: float, layer: int = 1) -> None:
        self.add(geo.circle(cx, cy, r), layer)

    def all_paths(self):
        for layer in sorted(self.layers):
            yield from self.layers[layer]

    # --- post processing -----------------------------------------------------------
    def clip_to_box(self) -> None:
        box = self.box
        eps = 1e-6
        for layer, paths in self.layers.items():
            out: list[Path] = []
            for p in paths:
                if all(box[0] - eps <= x <= box[2] + eps and box[1] - eps <= y <= box[3] + eps
                       for x, y in p):
                    out.append(p)
                else:
                    out.extend(geo.clip_polyline(p, box))
            self.layers[layer] = out

    def optimize(self, merge_tol: float = 0.05) -> None:
        for layer, paths in self.layers.items():
            paths = [simplify(p, 0.05) for p in paths]
            paths = merge_paths(paths, merge_tol)
            self.layers[layer] = sort_paths(paths)

    def stats(self, draw_speed: float = 30.0, travel_speed: float = 80.0,
              lift_time: float = 0.25) -> dict:
        """Path statistics and a rough plotting time estimate (speeds in mm/s)."""
        draw = travel = 0.0
        count = points = 0
        for layer in sorted(self.layers):
            pos = (0.0, 0.0)
            for p in self.layers[layer]:
                travel += math.dist(pos, p[0])
                draw += geo.path_length(p)
                pos = p[-1]
                count += 1
                points += len(p)
            travel += math.dist(pos, (0.0, 0.0))
        seconds = draw / draw_speed + travel / travel_speed + count * lift_time
        return {
            "paths": count,
            "points": points,
            "layers": len(self.layers),
            "draw_mm": round(draw, 1),
            "travel_mm": round(travel, 1),
            "minutes": round(seconds / 60, 1),
        }
