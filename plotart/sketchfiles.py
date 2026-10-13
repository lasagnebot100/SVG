"""Sketch files on disk (desktop): list, load, save – confined to one folder."""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path

_NAME = re.compile(r"^[\w äöüÄÖÜß.\-]{1,80}\.py$")
_VERSION = re.compile(r"^\d{8}-\d{6}-\d{6}\.py$")
MAX_VERSIONS = 50


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
        if path.exists():
            old = path.read_text(encoding="utf-8")
            if old != source:
                self._archive(path, old)
        tmp = path.with_suffix(".py.tmp")
        tmp.write_text(source, encoding="utf-8")
        tmp.replace(path)                       # atomic: editors never see half a file
        return {"name": path.name, "mtime": path.stat().st_mtime}

    # ------------------------------------------------------------- history
    def _history_dir(self, path: Path) -> Path:
        return self.dir / ".plotart" / "verlauf" / path.stem

    def _archive(self, path: Path, source: str):
        hdir = self._history_dir(path)
        hdir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y%m%d-%H%M%S")
        (hdir / f"{stamp}-{int(time.time() * 1e6) % 1_000_000:06d}.py").write_text(source, encoding="utf-8")
        versions = sorted(hdir.glob("*.py"))
        for old in versions[:-MAX_VERSIONS]:
            old.unlink()

    def history(self, name: str) -> list[dict]:
        """Earlier versions (newest first)."""
        path = self._path(name)
        hdir = self._history_dir(path)
        if not hdir.exists():
            return []
        out = []
        for p in sorted(hdir.glob("*.py"), reverse=True):
            if _VERSION.match(p.name):
                t = datetime.strptime(p.name[:15], "%Y%m%d-%H%M%S")
                out.append({"version": p.name, "time": t.strftime("%d.%m.%Y %H:%M:%S"), "size": p.stat().st_size})
        return out

    def history_load(self, name: str, version: str) -> dict:
        path = self._path(name)
        if not _VERSION.match(version or ""):
            raise SketchFileError("Ungültige Version")
        vpath = self._history_dir(path) / version
        if not vpath.exists():
            raise SketchFileError("Version nicht gefunden")
        return {"name": path.name, "version": version, "source": vpath.read_text(encoding="utf-8")}

    # ------------------------------------------------------------- favourites (per sketch)
    def _meta_path(self, path: Path) -> Path:
        return self.dir / ".plotart" / f"{path.stem}.json"

    def meta_load(self, name: str) -> dict:
        mp = self._meta_path(self._path(name))
        if not mp.exists():
            return {"favorites": []}
        try:
            return json.loads(mp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"favorites": []}

    def meta_save(self, name: str, meta: dict) -> dict:
        mp = self._meta_path(self._path(name))
        mp.parent.mkdir(parents=True, exist_ok=True)
        tmp = mp.with_suffix(".tmp")
        tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(mp)
        return {"ok": True}

    def stat(self, name: str) -> dict:
        path = self._path(name)
        return {"name": path.name, "exists": path.exists(),
                "mtime": path.stat().st_mtime if path.exists() else None}
