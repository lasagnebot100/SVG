"""High-level API: render(generator, params, …) -> Drawing."""
from __future__ import annotations

import random

from .core import PAPER_SIZES, Drawing
from .generators import REGISTRY
from .noise import Perlin
from .params import Param, parse_values

# Settings shared by all generators (shown at the top of the UI)
GLOBAL_PARAMS: list[Param] = [
    Param("paper", "Papierformat", "A3", choices=[(k, k) for k in PAPER_SIZES], randomize=False),
    Param("orientation", "Ausrichtung", "portrait",
          choices=[("portrait", "Hochformat"), ("landscape", "Querformat")], randomize=False),
    Param("margin", "Rand (mm)", 25.0, 0, 100, 1, randomize=False),
    Param("pen_width", "Stiftbreite (mm)", 0.45, 0.1, 2.0, 0.05, randomize=False,
          help="z. B. Micron 05 ≈ 0,45 mm – bestimmt die Dichte der Füllschraffur"),
    Param("color1", "Farbe Stift 1", "#1f5fbf", randomize=False),
    Param("color2", "Farbe Stift 2", "#d2412f", randomize=False),
    Param("optimize", "Pfade optimieren", True, randomize=False,
          help="verbindet Linien und sortiert sie für möglichst wenig Leerfahrten"),
]


def new_seed() -> int:
    return random.randrange(1, 1_000_000)


def random_params(name: str, seed: int | None = None) -> dict:
    rng = random.Random(seed)
    return {p.name: p.random_value(rng) for p in REGISTRY[name].params}


def render(name: str, params: dict | None = None, seed: int | None = None,
           settings: dict | None = None) -> Drawing:
    if name not in REGISTRY:
        raise KeyError(f"Unbekannter Generator '{name}'. Verfügbar: {', '.join(REGISTRY)}")
    gen = REGISTRY[name]
    values = parse_values(gen.params, params)
    s = parse_values(GLOBAL_PARAMS, settings)
    seed = int(seed) if seed is not None else new_seed()

    w, h = PAPER_SIZES[s["paper"]]
    if s["orientation"] == "landscape":
        w, h = h, w
    margin = min(s["margin"], min(w, h) / 2 - 5)
    d = Drawing(w, h, margin, s["pen_width"])
    d.colors = {1: s["color1"], 2: s["color2"]}

    gen.func(d, random.Random(seed), Perlin(seed), values)
    d.clip_to_box()
    if s["optimize"]:
        d.optimize(merge_tol=max(0.02, s["pen_width"] * 0.1))
    d.meta = {"generator": name, "seed": seed, "params": values, "settings": s}
    return d
