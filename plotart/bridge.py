"""JSON-level interface shared by the local web server and the in-browser (Pyodide) app."""
from __future__ import annotations

import base64
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


# ---------------------------------------------------------------------------- sketches
# Errors inside the user's sketch are returned as data ("sketch_error"), so the
# editor can mark the line; "error" is reserved for failures of the tool itself.

def _execute(req: dict):
    from .sketch import execute
    return execute(req.get("source", ""), req.get("params"), int(req.get("seed") or 1))


def sketch_run(req: dict) -> dict:
    from .sketch import run_sketch
    out = run_sketch(req.get("source", ""), req.get("params"), int(req.get("seed") or 1))
    out["sketch_error"] = out.pop("error")
    return out


def sketch_plotter(req: dict) -> dict:
    from .sketch import to_plotter
    sk, log, err, _ = _execute(req)
    if err:
        return {"sketch_error": err}
    d = to_plotter(sk, pen_width=float(req.get("pen_width") or 0.45),
                   outline_fills=bool(req.get("outline_fills", True)))
    return {"svg": to_svg(d), "stats": d.stats()}


def sketch_png(req: dict) -> dict:
    from .sketch import render_png
    sk, log, err, _ = _execute(req)
    if err:
        return {"sketch_error": err}
    png = render_png(sk, scale=req.get("scale"))
    return {"png_base64": base64.b64encode(png).decode()}


def sketch_examples(req: dict) -> dict:
    from .sketch import list_examples
    return {"examples": list_examples()}


def sketch_reference(req: dict) -> dict:
    from .sketch import api_reference
    return {"reference": api_reference()}


COMMANDS = {
    "schema": lambda req: schema(),
    "render": render_response,
    "random": random_response,
    "sketch_run": sketch_run,
    "sketch_plotter": sketch_plotter,
    "sketch_png": sketch_png,
    "sketch_examples": sketch_examples,
    "sketch_reference": sketch_reference,
}
# commands that execute user code (the server runs them in a separate process)
USER_CODE_COMMANDS = {"sketch_run", "sketch_plotter", "sketch_png"}


def dispatch(cmd: str, req: dict) -> dict:
    fn = COMMANDS.get(cmd)
    if fn is None:
        return {"error": f"unbekannter Befehl {cmd!r}"}
    return fn(req)


def call_json(cmd: str, arg_json: str) -> str:
    """Entry point for the browser worker: JSON string in, JSON string out."""
    try:
        out = dispatch(cmd, json.loads(arg_json or "{}"))
    except Exception as exc:  # surface errors in the UI
        out = {"error": f"{type(exc).__name__}: {exc}"}
    return json.dumps(out, ensure_ascii=False)
