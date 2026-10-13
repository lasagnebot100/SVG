"""Build the installable Blender extension (zip) – no Blender needed for this step.

    python3 -m plotart blender-addon            → output/plotart_blender.zip
Blender: Bearbeiten › Einstellungen › Erweiterungen › ▾ › Von Datenträger installieren …
"""
from __future__ import annotations

import zipfile
from pathlib import Path

from .. import __version__

PKG = Path(__file__).resolve().parent.parent          # …/plotart

MANIFEST = f'''schema_version = "1.0.0"

id = "plotart"
version = "{__version__}"
name = "plotart"
tagline = "Generative Kunst-Skizzen in Python als Blender-Objekte"
maintainer = "plotart"
type = "add-on"
tags = ["Import-Export", "Object", "Animation"]

blender_version_min = "4.2.0"

license = ["SPDX:MIT"]

[permissions]
files = "Skizzen-Dateien (.py) lesen und auf Änderungen prüfen"
'''

# not needed inside Blender: web server, generators UI, CLI
SKIP_DIRS = {"__pycache__", "static"}
SKIP_FILES = {"web.py", "cli.py", "__main__.py", "worker.py"}


def build_addon(out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("blender_manifest.toml", MANIFEST)
        z.write(PKG / "blender" / "addon.py", "__init__.py")
        for path in sorted(PKG.rglob("*.py")):
            rel = path.relative_to(PKG)
            if SKIP_DIRS & set(rel.parts) or rel.name in SKIP_FILES:
                continue
            z.write(path, (Path("plotart") / rel).as_posix())
    return out
