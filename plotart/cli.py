"""Command line interface.

    python -m plotart                         → Web-Oberfläche starten
    python -m plotart list                    → Generatoren und Parameter anzeigen
    python -m plotart render blocks -s 42     → SVG erzeugen
    python -m plotart random -n 10            → 10 zufällige Bilder
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


def main(argv=None):
    ap = argparse.ArgumentParser(prog="plotart", description="Generative SVG-Kunst für Stiftplotter")
    sub = ap.add_subparsers(dest="cmd")

    w = sub.add_parser("web", help="Web-Oberfläche starten (Standard)")
    w.add_argument("--port", type=int, default=8765)
    w.add_argument("--host", default="127.0.0.1")
    w.add_argument("--no-browser", action="store_true")

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

    if args.cmd in (None, "web"):
        from .web import serve
        serve(host=getattr(args, "host", "127.0.0.1"), port=getattr(args, "port", 8765),
              open_browser=not getattr(args, "no_browser", False))
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
