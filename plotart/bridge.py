"""JSON-level interface shared by the local web server and the in-browser (Pyodide) app."""
from __future__ import annotations

import json

from .api import GLOBAL_PARAMS, new_seed, random_params, render
from .generators import REGISTRY
from .svg import to_svg


def schema() -> dict:
    return {
        "generators": [g.to_json() for g in REGISTRY.values()],
        "settings": [p.to_json() for p in GLOBAL_PARAMS],
    }


def render_request(req: dict):
    """Returns (drawing, svg) for a request {generator, params, seed, settings}."""
    d = render(req["generator"], req.get("params"), req.get("seed"), req.get("settings"))
    return d, to_svg(d)


def render_response(req: dict) -> dict:
    d, svg = render_request(req)
    return {"svg": svg, "stats": d.stats(), "seed": d.meta["seed"]}


def random_response(req: dict) -> dict:
    return {"params": random_params(req["generator"], new_seed()), "seed": new_seed()}


def call_json(cmd: str, arg_json: str) -> str:
    """Entry point for the browser worker: JSON string in, JSON string out."""
    arg = json.loads(arg_json or "{}")
    try:
        if cmd == "schema":
            out = schema()
        elif cmd == "render":
            out = render_response(arg)
        elif cmd == "random":
            out = random_response(arg)
        else:
            out = {"error": f"unbekannter Befehl {cmd!r}"}
    except Exception as exc:  # surface errors in the UI
        out = {"error": f"{type(exc).__name__}: {exc}"}
    return json.dumps(out, ensure_ascii=False)
