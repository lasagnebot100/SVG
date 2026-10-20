"""Other languages in the Studio: Processing (.pde), p5.js (runs in the browser) and, later, R and Kotlin.

processing.py  run .pde sketches with an installed Processing
pde_convert.py convert simple Processing sketches to plotart Python
examples/      bundled examples: *.pde (Processing), *.js (p5.js)
"""
from __future__ import annotations

from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parent / "examples"


def list_examples(ext: str) -> list[dict]:
    """Bundled examples with this file extension: {"name", "title", "source"}; title = first // comment line."""
    out = []
    for path in sorted(EXAMPLES_DIR.glob(f"*{ext}")):
        src = path.read_text(encoding="utf-8")
        first = src.lstrip().splitlines()[0] if src.strip() else ""
        title = first[2:].strip() if first.startswith("//") else path.stem
        out.append({"name": path.stem, "title": title, "source": src})
    return out
