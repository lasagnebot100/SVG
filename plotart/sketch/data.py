"""Loading data files in sketches: paths, CSV, JSON, text, built-in sample data."""
from __future__ import annotations

import csv
import io
import json
import math
import os
import random
from pathlib import Path

SAMPLE_PREFIX = "beispiel:"

# Folders searched for relative paths (set by the runner: sketch folder, its daten/ folder …)
ASSET_DIRS: list[str] = []


class DataError(Exception):
    pass


def resolve(path: str) -> Path:
    """Find a file: absolute path, or relative to the sketch folders / their daten/ subfolder."""
    p = Path(os.path.expanduser(str(path)))
    if p.is_absolute():
        if p.exists():
            return p
        raise DataError(f"Datei nicht gefunden: {p}")
    tried = []
    for base in [*ASSET_DIRS, os.getcwd()]:
        for cand in (Path(base) / p, Path(base) / "daten" / p):
            if cand.exists():
                return cand
            tried.append(str(cand.parent))
    hint = " · ".join(dict.fromkeys(tried))
    raise DataError(f"Datei '{path}' nicht gefunden. Gesucht in: {hint}. "
                    f"Tipp: Datei in den Ordner daten/ legen (im Studio: Bereich „Daten“).")


def _number(v: str):
    s = v.strip()
    if not s:
        return s
    for cand in (s, s.replace(".", "").replace(",", ".") if "," in s else None):
        if cand is None:
            continue
        try:
            f = float(cand)
        except ValueError:
            continue
        return int(f) if f.is_integer() and "." not in cand and "e" not in cand.lower() else f
    return s


def parse_csv(text: str, delimiter: str | None = None, numbers: bool = True) -> list[dict]:
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ";" if text.count(";") > text.count(",") else ","
    rows = list(csv.DictReader(io.StringIO(text), delimiter=delimiter))
    if numbers:
        rows = [{k: _number(v) if isinstance(v, str) else v for k, v in r.items()} for r in rows]
    return rows


def read_text(path: str) -> str:
    if str(path).startswith(SAMPLE_PREFIX):
        return sample_text(str(path)[len(SAMPLE_PREFIX):])
    data = resolve(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def load_csv(path: str, delimiter: str | None = None, numbers: bool = True) -> list[dict]:
    """CSV als Liste von Dicts (Zahlen werden umgewandelt, auch mit Dezimalkomma)."""
    return parse_csv(read_text(path), delimiter, numbers)


def load_json(path: str):
    """JSON-Datei laden."""
    return json.loads(read_text(path))


def load_text(path: str) -> str:
    """Textdatei als String."""
    return read_text(path)


def load_lines(path: str) -> list[str]:
    """Textdatei als Liste von Zeilen."""
    return read_text(path).splitlines()


# ------------------------------------------------------------------------ samples
def sample_names() -> list[str]:
    return [SAMPLE_PREFIX + n for n in ("temperaturen.csv", "zufall.json", "gedicht.txt")]


def sample_text(name: str) -> str:
    """Built-in, clearly synthetic sample data (works offline, without files)."""
    if name == "temperaturen.csv":
        rng = random.Random(4)
        monate = ["Jänner", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
                  "September", "Oktober", "November", "Dezember"]
        lines = ["monat;stadt_a;stadt_b;stadt_c"]
        for i, m in enumerate(monate):
            base = 10 - 11 * math.cos(math.tau * (i + 0.5) / 12)
            vals = [base + rng.uniform(-1.5, 1.5) + off for off in (0.0, 2.5, -3.0)]
            lines.append(m + ";" + ";".join(f"{v:.1f}".replace(".", ",") for v in vals))
        return "\n".join(lines) + "\n"
    if name == "zufall.json":
        rng = random.Random(9)
        pts = [{"x": round(rng.random(), 3), "y": round(rng.random(), 3), "wert": round(rng.gauss(50, 15), 1)}
               for _ in range(60)]
        return json.dumps({"beschreibung": "synthetische Beispieldaten", "punkte": pts}, ensure_ascii=False)
    if name == "gedicht.txt":
        return ("Linie folgt Linie,\nPunkt um Punkt wächst ein Bild –\n"
                "der Zufall hat Form.\n")
    raise DataError(f"Unbekannte Beispieldaten '{SAMPLE_PREFIX}{name}'. Möglich: "
                    + ", ".join(sample_names()))
