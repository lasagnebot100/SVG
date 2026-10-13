"""Sketch files on disk (desktop): list, load, save – confined to one folder."""
from __future__ import annotations

import re
from pathlib import Path

_NAME = re.compile(r"^[\w äöüÄÖÜß.\-]{1,80}\.py$")


class SketchFileError(Exception):
    pass


class SketchFolder:
    def __init__(self, folder: str | Path):
        self.dir = Path(folder).resolve()

    def _path(self, name: str) -> Path:
        name = (name or "").strip()
        if not name.endswith(".py"):
            name += ".py"
        if not _NAME.match(name) or name.startswith("."):
            raise SketchFileError("Ungültiger Dateiname – erlaubt sind Buchstaben, Ziffern, Leerzeichen, - _ .")
        path = (self.dir / name).resolve()
        if path.parent != self.dir:
            raise SketchFileError("Ungültiger Dateiname")
        return path

    def list(self) -> list[dict]:
        if not self.dir.exists():
            return []
        files = [p for p in self.dir.glob("*.py") if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return [{"name": p.name, "mtime": p.stat().st_mtime, "size": p.stat().st_size} for p in files]

    def load(self, name: str) -> dict:
        path = self._path(name)
        if not path.exists():
            raise SketchFileError(f"{path.name} gibt es nicht")
        return {"name": path.name, "source": path.read_text(encoding="utf-8"), "mtime": path.stat().st_mtime}

    def save(self, name: str, source: str, overwrite: bool = True) -> dict:
        path = self._path(name)
        if path.exists() and not overwrite:
            raise SketchFileError(f"{path.name} existiert bereits")
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".py.tmp")
        tmp.write_text(source, encoding="utf-8")
        tmp.replace(path)                       # atomic: editors never see half a file
        return {"name": path.name, "mtime": path.stat().st_mtime}

    def stat(self, name: str) -> dict:
        path = self._path(name)
        return {"name": path.name, "exists": path.exists(),
                "mtime": path.stat().st_mtime if path.exists() else None}
