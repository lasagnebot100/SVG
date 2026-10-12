"""Parameter descriptions shared by the CLI and the web interface."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Param:
    name: str
    label: str
    default: Any
    min: float | None = None
    max: float | None = None
    step: float | None = None
    choices: list[tuple[str, str]] | None = None  # (value, label)
    help: str = ""
    kind: str = field(default="")
    randomize: bool = True  # include in "Parameter würfeln"
    rand: tuple[float, float] | None = None  # narrower range for randomising

    def __post_init__(self):
        if self.kind:
            return
        if self.choices:
            self.kind = "choice"
        elif isinstance(self.default, bool):
            self.kind = "bool"
        elif isinstance(self.default, int):
            self.kind = "int"
        elif isinstance(self.default, float):
            self.kind = "float"
        elif isinstance(self.default, str) and self.default.startswith("#"):
            self.kind = "color"
        else:
            self.kind = "str"

    def parse(self, raw: Any) -> Any:
        """Convert user input (string, number, bool) to a valid, clamped value."""
        if raw is None:
            return self.default
        if self.kind == "bool":
            if isinstance(raw, str):
                return raw.strip().lower() in ("1", "true", "yes", "ja", "on", "y")
            return bool(raw)
        if self.kind in ("int", "float"):
            try:
                val = float(raw)
            except (TypeError, ValueError):
                return self.default
            if self.min is not None:
                val = max(self.min, val)
            if self.max is not None:
                val = min(self.max, val)
            return int(round(val)) if self.kind == "int" else val
        if self.kind == "choice":
            raw = str(raw)
            values = [c[0] for c in self.choices]
            return raw if raw in values else self.default
        return str(raw)

    def random_value(self, rng: random.Random) -> Any:
        if not self.randomize:
            return self.default
        if self.kind == "bool":
            return rng.random() < 0.5
        if self.kind == "choice":
            return rng.choice(self.choices)[0]
        if self.kind in ("int", "float") and self.min is not None and self.max is not None:
            lo, hi = self.rand or (self.min, self.max)
            val = rng.uniform(lo, hi)
            if self.kind == "int":
                return int(round(val))
            step = self.step or 0.01
            return round(round(val / step) * step, 6)
        return self.default

    def to_json(self) -> dict:
        return {
            "name": self.name, "label": self.label, "default": self.default,
            "min": self.min, "max": self.max, "step": self.step, "kind": self.kind,
            "choices": self.choices, "help": self.help,
        }


def parse_values(params: list[Param], raw: dict | None) -> dict:
    raw = raw or {}
    return {p.name: p.parse(raw.get(p.name)) for p in params}
