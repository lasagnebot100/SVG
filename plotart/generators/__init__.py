"""Generator registry. Each generator module registers itself via @register."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from ..core import Drawing
from ..noise import Perlin
from ..params import Param


@dataclass
class Generator:
    name: str
    title: str
    description: str
    params: list[Param]
    func: Callable[[Drawing, random.Random, Perlin, dict], None]

    def to_json(self) -> dict:
        return {
            "name": self.name, "title": self.title, "description": self.description,
            "params": [p.to_json() for p in self.params],
        }


REGISTRY: dict[str, Generator] = {}


def register(name: str, title: str, description: str, params: list[Param]):
    def deco(func):
        REGISTRY[name] = Generator(name, title, description, params, func)
        return func
    return deco


# import order = order in the UI
from . import blocks, flowfield, waves, topo, circles, truchet, harmonograph  # noqa: E402,F401
