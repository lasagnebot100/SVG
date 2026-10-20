"""Series export: many seeds of one sketch at once, with a contact sheet (Kontaktbogen)."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Callable

from ..svg import to_svg
from ..viewer import sketch_doc
from .data import DataError
from .edition import write_edition
from .export import render_png, to_plotter
from .fonts import find_font
from .render_svg import render_svg
from .runner import execute

FORMATS = ("png", "svg", "plotter")


def contact_sheet(thumbs: list[tuple[str, object]], cols: int | None = None, cell: int = 260,
                  title: str = ""):
    """Grid of PIL thumbnails with labels → PIL image."""
    from PIL import Image, ImageDraw, ImageFont
    n = max(1, len(thumbs))
    cols = cols or min(6, max(1, round(n ** 0.5 + 0.49)))
    rows = (n + cols - 1) // cols
    pad, label, head = 14, 22, 40 if title else 0
    W = cols * (cell + pad) + pad
    H = head + rows * (cell + label + pad) + pad
    sheet = Image.new("RGB", (W, H), (236, 235, 231))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(find_font("sans"), 14)
        tfont = ImageFont.truetype(find_font("sans-bold"), 18)
    except (OSError, DataError):
        font = tfont = ImageFont.load_default()
    if title:
        d.text((pad, 12), title, fill=(29, 29, 31), font=tfont)
    for i, (text, im) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x0, y0 = pad + c * (cell + pad), head + pad + r * (cell + label + pad)
        if im is not None:
            t = im.copy()
            t.thumbnail((cell, cell))
            bg = Image.new("RGB", t.size, (251, 250, 247))
            bg.paste(t, mask=t.getchannel("A") if t.mode == "RGBA" else None)
            sheet.paste(bg, (x0 + (cell - t.width) // 2, y0 + (cell - t.height) // 2))
        d.text((x0, y0 + cell + 4), text, fill=(110, 110, 115), font=font)
    return sheet


def export_series(source: str, out_dir: str | Path, seeds: list[int], params: dict | None = None,
                  formats=("png",), scale: float | None = None, sheet: bool = True, pen_width: float = 0.45,
                  hidden_lines: bool = False,
                  stem: str = "skizze", progress: Callable[[int, int], None] | None = None,
                  should_stop: Callable[[], bool] | None = None, zip_path: str | Path | None = None,
                  title: str | None = None, description: str | None = None, artist: str = "") -> dict:
    """Render every seed into out_dir (PNG/SVG/plotter-SVG), plus kontaktbogen.png and serie.json.

    As an edition also metadata/<seed>.json, edition.json (traits and rarities from feature()) and
    galerie.html; title and description default to the sketch's concept (docstring).
    """
    from PIL import Image
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    entries, thumbs = [], []
    for i, seed in enumerate(seeds):
        if should_stop and should_stop():
            break
        sk, log, err, ms = execute(source, params, int(seed))
        entry = {"seed": int(seed), "files": []}
        if err:
            entry["error"] = err["message"]
            thumbs.append((f"Seed {seed} – Fehler", None))
        else:
            entry["params"] = {p.name: (params or {}).get(p.name, p.default) for p in sk.param_specs}
            entry["features"] = dict(sk.features)
            base = out / f"{stem}_{seed}"
            png = None
            if "png" in formats or sheet:
                png = render_png(sk, scale=scale)
            if "png" in formats:
                base.with_suffix(".png").write_bytes(png)
                entry["files"].append(base.with_suffix(".png").name)
            if "svg" in formats:
                base.with_suffix(".svg").write_text(render_svg(sk, {"seed": seed, "params": entry["params"]}),
                                                    encoding="utf-8")
                entry["files"].append(base.with_suffix(".svg").name)
            if "plotter" in formats:
                p = out / f"{stem}_{seed}_plotter.svg"
                p.write_text(to_svg(to_plotter(sk, pen_width=pen_width, hidden_lines=hidden_lines)), encoding="utf-8")
                entry["files"].append(p.name)
            thumbs.append((f"Seed {seed}", Image.open(io.BytesIO(png)).convert("RGBA") if png else None))
        entries.append(entry)
        if progress:
            progress(i + 1, len(seeds))
    result = {"dir": str(out), "count": len(entries), "errors": sum(1 for e in entries if "error" in e)}
    if sheet and thumbs:
        contact_sheet(thumbs, title=f"{stem} – {len(thumbs)} Varianten").save(out / "kontaktbogen.png")
        result["sheet"] = str(out / "kontaktbogen.png")
    (out / "serie.json").write_text(json.dumps({"skizze": stem, "varianten": entries}, ensure_ascii=False,
                                               indent=1), encoding="utf-8")
    if any("features" in e for e in entries):
        doc_title, doc_text = sketch_doc(source)
        images = {e["seed"]: next((f for f in e["files"] if f.endswith(".png")), e["files"][0] if e["files"] else None)
                  for e in entries if "features" in e}
        write_edition(out, entries, title or doc_title or stem, doc_text if description is None else description,
                      artist, images)
        result["gallery"] = str(out / "galerie.html")
    if zip_path:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(p for p in out.rglob("*") if p.is_file()):     # incl. metadata/
                z.write(f, f"{out.name}/{f.relative_to(out).as_posix()}")
        result["zip"] = str(zip_path)
    return result
