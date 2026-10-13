"""Command line interface.

    python -m plotart                         → Studio (Web-Oberfläche) starten
    python -m plotart sketch meine.py --png   → Skizze ausführen und exportieren
    python -m plotart list                    → Generatoren und Parameter anzeigen
    python -m plotart render blocks -s 42     → Generator-SVG erzeugen
    python -m plotart random -n 10            → 10 zufällige Generator-Bilder
"""
from __future__ import annotations

import argparse
import os
import random
import sys

from .api import GLOBAL_PARAMS, new_seed, random_params, render
from .generators import REGISTRY
from .svg import to_png, to_svg


def _settings(args) -> dict:
    return {
        "paper": args.paper,
        "orientation": "landscape" if args.landscape else "portrait",
        "margin": args.margin,
        "pen_width": args.pen,
        "color1": args.color1,
        "color2": args.color2,
        "optimize": not args.no_optimize,
    }


def _add_common(sp):
    g = {p.name: p for p in GLOBAL_PARAMS}
    sp.add_argument("--paper", default=g["paper"].default, help="A6 … A1, Letter, 30x40, 50x70")
    sp.add_argument("--landscape", action="store_true", help="Querformat")
    sp.add_argument("--margin", type=float, default=g["margin"].default, help="Rand in mm")
    sp.add_argument("--pen", type=float, default=g["pen_width"].default, help="Stiftbreite in mm")
    sp.add_argument("--color1", default=g["color1"].default)
    sp.add_argument("--color2", default=g["color2"].default)
    sp.add_argument("--no-optimize", action="store_true", help="Pfade nicht optimieren")
    sp.add_argument("--png", action="store_true", help="zusätzlich PNG-Vorschau (braucht Pillow)")
    sp.add_argument("-o", "--out", default="output", help="Ausgabeordner oder Dateiname .svg")


def _write(d, out: str, png: bool, quiet=False) -> str:
    meta = d.meta
    if out.lower().endswith(".svg"):
        path = out
    else:
        os.makedirs(out, exist_ok=True)
        path = os.path.join(out, f"{meta['generator']}_{meta['seed']}.svg")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(to_svg(d))
    if png:
        to_png(d, path[:-4] + ".png")
    if not quiet:
        st = d.stats()
        print(f"✓ {path}  –  {st['paths']} Pfade, {st['draw_mm'] / 1000:.1f} m Linie, "
              f"ca. {st['minutes']} min Plotzeit")
    return path


def _parse_sets(items: list[str]) -> dict:
    out = {}
    for item in items or []:
        if "=" not in item:
            sys.exit(f"Parameter '{item}' bitte als name=wert angeben")
        k, v = item.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _load_sketch_source(name: str) -> tuple[str, str]:
    """Returns (source, stem) for a file path or an example name/prefix."""
    from .sketch import list_examples
    if os.path.isfile(name):
        with open(name, encoding="utf-8") as f:
            return f.read(), os.path.splitext(os.path.basename(name))[0]
    matches = [e for e in list_examples() if e["name"] == name or e["name"].startswith(name)]
    if len(matches) == 1:
        return matches[0]["source"], matches[0]["name"]
    names = ", ".join(e["name"] for e in list_examples())
    sys.exit(f"'{name}' ist weder eine Datei noch ein eindeutiges Beispiel.\nBeispiele: {names}")


def _export_animation_cli(source, stem, params, seed, args) -> int:
    from .sketch.video import ExportError, export_animation
    formats = [f for f, on in (("mp4", args.mp4), ("webm", args.webm), ("gif", args.gif),
                               ("png", args.png_seq)) if on]
    out_dir = args.out if not args.out.lower().endswith((".svg", ".png", ".mp4", ".gif", ".webm", ".zip")) \
        else os.path.dirname(args.out) or "."
    status = 0
    for fmt in formats:
        ext = "zip" if fmt == "png" else fmt
        path = os.path.join(out_dir, f"{stem}_{seed}.{ext}")

        def progress(i, n):
            if sys.stdout.isatty():
                bar = "█" * int(30 * i / n) + "░" * (30 - int(30 * i / n))
                print(f"\r  {fmt.upper():4} {bar} {i}/{n}", end="", flush=True)

        try:
            res = export_animation(source, path, fmt, params, seed, args.scale, args.frames, args.fps,
                                   progress=progress)
        except ExportError as exc:
            print(("\n" if sys.stdout.isatty() else "") + f"✗ {exc}", file=sys.stderr)
            status = 1
            continue
        if sys.stdout.isatty():
            print()
        mb = res["bytes"] / 1048576
        print(f"✓ {path}  –  {res['frames']} Bilder, {res['fps']:g} fps, {res['width']}×{res['height']} px, {mb:.1f} MB")
    return status


def _make_blend_cli(source, params, seed, args) -> int:
    from .blender.make import BlenderError, make_blend
    from .blender.scene import SceneError
    out = args.blend if args.count == 1 else args.blend.replace(".blend", f"_{seed}.blend")
    options = {"relief": args.relief, "relief_height": args.relief_height, "stroke_mode": args.lines,
               "material_mode": args.material, "camera": args.camera}
    try:
        res = make_blend(source, out, params=params, seed=seed, width=args.width, frame=args.image,
                         max_frames=args.frames, options=options, render=args.render, engine=args.engine)
    except (BlenderError, SceneError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    print(f"✓ {res['out']}  –  {res['objects']} Objekte, {res['frames']} Bild(er)"
          + (f", gerendert nach {args.render}" if args.render else ""))
    return 0


def _run_sketch_cmd(args) -> int:
    from .sketch import execute, render_png, render_svg, to_plotter
    from .svg import to_svg

    source, stem = _load_sketch_source(args.file)
    params = _parse_sets(args.param)
    status = 0
    animated_out = args.mp4 or args.webm or args.gif or args.png_seq
    for i in range(args.count):
        seed = args.seed + i
        if args.blend:
            status |= _make_blend_cli(source, params, seed, args)
            if not animated_out:
                continue
        if animated_out:
            status |= _export_animation_cli(source, stem, params, seed, args)
            continue
        sk, log, err, ms = execute(source, params, seed)
        if log:
            print(log, end="" if log.endswith("\n") else "\n")
        if err:
            where = f"Zeile {err['line']}: " if err.get("line") else ""
            print(f"✗ {where}{err['message']}", file=sys.stderr)
            status = 1
            continue
        unknown = set(params) - {p.name for p in sk.param_specs}
        if unknown:
            print(f"Hinweis: unbekannte Parameter {', '.join(sorted(unknown))}", file=sys.stderr)
        out = args.out
        if out.lower().endswith((".svg", ".png")):
            base = out[:-4] + (f"_{seed}" if args.count > 1 else "")
            want_png = args.png or out.lower().endswith(".png")
            want_svg = not args.no_svg and out.lower().endswith(".svg")
        else:
            os.makedirs(out, exist_ok=True)
            base = os.path.join(out, f"{stem}_{seed}")
            want_png, want_svg = args.png, not args.no_svg
        os.makedirs(os.path.dirname(os.path.abspath(base)) or ".", exist_ok=True)
        written = []
        meta = {"seed": seed, "params": {p.name: params.get(p.name, p.default) for p in sk.param_specs}}
        if want_svg:
            with open(base + ".svg", "w", encoding="utf-8") as f:
                f.write(render_svg(sk, meta))
            written.append(base + ".svg")
        if want_png:
            with open(base + ".png", "wb") as f:
                f.write(render_png(sk, scale=args.scale))
            written.append(base + ".png")
        if args.plotter:
            d = to_plotter(sk, pen_width=args.pen)
            with open(base + "_plotter.svg", "w", encoding="utf-8") as f:
                f.write(to_svg(d))
            st = d.stats()
            written.append(f"{base}_plotter.svg ({st['paths']} Pfade, ca. {st['minutes']} min)")
        print(f"✓ Seed {seed} in {ms:.0f} ms → " + ", ".join(written))
    return status


def main(argv=None):
    ap = argparse.ArgumentParser(prog="plotart", description="Generative SVG-Kunst für Stiftplotter")
    sub = ap.add_subparsers(dest="cmd")

    w = sub.add_parser("web", aliases=["studio"], help="Studio / Web-Oberfläche starten (Standard)")
    w.add_argument("--port", type=int, default=8765)
    w.add_argument("--host", default="127.0.0.1",
                   help="0.0.0.0 = im Netzwerk erreichbar (z. B. fürs iPad, mit Zugangs-Token)")
    w.add_argument("--no-browser", action="store_true")
    w.add_argument("--timeout", type=float, default=30.0, help="Zeitlimit pro Skizze in Sekunden")
    w.add_argument("--ordner", default="skizzen", help="Ordner für deine Skizzen (Standard: ./skizzen)")

    sk = sub.add_parser("sketch", help="Skizze (.py) ausführen und exportieren")
    sk.add_argument("file", help="Skizzen-Datei oder Name eines Beispiels (z. B. 03)")
    sk.add_argument("-s", "--seed", type=int, default=1)
    sk.add_argument("-p", "--param", action="append", metavar="NAME=WERT", help="Regler-Wert setzen")
    sk.add_argument("-n", "--count", type=int, default=1, help="mehrere Seeds (seed, seed+1, …)")
    sk.add_argument("-o", "--out", default="output", help="Ausgabeordner oder Datei (.svg / .png)")
    sk.add_argument("--png", action="store_true", help="zusätzlich PNG")
    sk.add_argument("--scale", type=float, help="PNG-Pixel pro Einheit (Standard: 1 bei px, 300 dpi bei mm)")
    sk.add_argument("--plotter", action="store_true", help="zusätzlich Plotter-SVG (nur Linien, optimiert)")
    sk.add_argument("--pen", type=float, default=0.45, help="Stiftbreite für --plotter (mm)")
    sk.add_argument("--no-svg", action="store_true", help="kein Farb-SVG schreiben")
    anim = sk.add_argument_group("Animation (Skizzen mit draw())")
    anim.add_argument("--mp4", action="store_true", help="als MP4-Video exportieren (braucht ffmpeg)")
    anim.add_argument("--webm", action="store_true", help="als WebM-Video exportieren (braucht ffmpeg)")
    anim.add_argument("--gif", action="store_true", help="als GIF-Animation exportieren")
    anim.add_argument("--png-seq", action="store_true", help="alle Bilder als PNG-Sequenz (ZIP)")
    anim.add_argument("--frames", type=int, help="Anzahl Bilder (überschreibt animation())")
    anim.add_argument("--fps", type=float, help="Bilder pro Sekunde (überschreibt animation())")
    bl = sk.add_argument_group("Blender (braucht Blender oder `pip install bpy`)")
    bl.add_argument("--blend", metavar="DATEI.blend", help="Blender-Datei erzeugen")
    bl.add_argument("--render", metavar="BILD", help="zusätzlich rendern (bei Animationen z. B. frames/bild_####.png)")
    bl.add_argument("--relief", choices=["none", "constant", "order", "brightness"], default="none",
                    help="Flächen hochziehen: gleich hoch, nach Reihenfolge oder nach Helligkeit")
    bl.add_argument("--relief-height", type=float, default=0.5, help="Relief-Höhe in Blender-Einheiten")
    bl.add_argument("--lines", choices=["flat", "tube"], default="flat", help="Linien flach oder als 3D-Röhren")
    bl.add_argument("--material", choices=["flat", "physical"], default="flat",
                    help="flat = exakte 2D-Farben, physical = reagiert auf Licht")
    bl.add_argument("--camera", choices=["top", "perspective"], default="top")
    bl.add_argument("--width", type=float, default=10.0, help="Breite in Blender-Einheiten")
    bl.add_argument("--image", type=int, metavar="N", help="nur Bild N der Animation (inkl. Spuren)")
    bl.add_argument("--engine", choices=["CYCLES", "BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"],
                    help="Render-Engine")

    ba = sub.add_parser("blender-addon", help="Blender-Erweiterung (ZIP) bauen")
    ba.add_argument("-o", "--out", default=os.path.join("output", "plotart_blender.zip"))

    sub.add_parser("list", help="Generatoren und Parameter auflisten")

    r = sub.add_parser("render", help="ein Bild erzeugen")
    r.add_argument("generator", choices=list(REGISTRY))
    r.add_argument("-s", "--seed", type=int, help="Zufalls-Seed (gleicher Seed = gleiches Bild)")
    r.add_argument("-p", "--param", action="append", metavar="NAME=WERT",
                   help="Parameter setzen, mehrfach möglich (siehe 'list')")
    r.add_argument("-n", "--count", type=int, default=1, help="mehrere Varianten (Seeds) erzeugen")
    _add_common(r)

    rnd = sub.add_parser("random", help="Zufallsbilder mit zufälligen Parametern")
    rnd.add_argument("-g", "--generator", choices=list(REGISTRY), help="nur dieser Generator")
    rnd.add_argument("-n", "--count", type=int, default=6)
    _add_common(rnd)

    args = ap.parse_args(argv)

    if args.cmd in (None, "web", "studio"):
        from .web import serve
        serve(host=getattr(args, "host", "127.0.0.1"), port=getattr(args, "port", 8765),
              open_browser=not getattr(args, "no_browser", False),
              timeout=getattr(args, "timeout", 30.0), sketch_dir=getattr(args, "ordner", "skizzen"))
        return

    if args.cmd == "sketch":
        sys.exit(_run_sketch_cmd(args))

    if args.cmd == "blender-addon":
        from .blender.package import build_addon
        path = build_addon(args.out)
        print(f"✓ {path}\n  In Blender: Bearbeiten › Einstellungen › Erweiterungen › ▾ (oben rechts) › "
              "„Von Datenträger installieren …“ → diese ZIP wählen.\n"
              "  Danach im 3D-Viewport die Seitenleiste (Taste N) öffnen › Reiter „plotart“.")
        return

    if args.cmd == "list":
        for g in REGISTRY.values():
            print(f"\n{g.name:13} {g.title} – {g.description}")
            for p in g.params:
                extra = ""
                if p.kind == "choice":
                    extra = " [" + "|".join(c[0] for c in p.choices) + "]"
                elif p.min is not None:
                    extra = f" [{p.min} … {p.max}]"
                print(f"    {p.name:15} = {str(p.default):10} {p.label}{extra}")
        return

    settings = _settings(args)
    if args.cmd == "render":
        params = _parse_sets(args.param)
        unknown = set(params) - {p.name for p in REGISTRY[args.generator].params}
        if unknown:
            sys.exit(f"Unbekannte Parameter: {', '.join(sorted(unknown))} (siehe 'plotart list')")
        for i in range(args.count):
            seed = args.seed + i if args.seed is not None else new_seed()
            out = args.out
            if args.count > 1 and out.lower().endswith(".svg"):
                out = out[:-4] + f"_{seed}.svg"
            _write(render(args.generator, params, seed, settings), out, args.png)
        return

    if args.cmd == "random":
        rng = random.Random()
        for _ in range(args.count):
            name = args.generator or rng.choice(list(REGISTRY))
            seed = new_seed()
            d = render(name, random_params(name, seed), seed, settings)
            _write(d, args.out, args.png)
