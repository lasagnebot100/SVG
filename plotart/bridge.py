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


# The running animation is kept between calls, so the editor can stream frames chunk by
# chunk. Asking for an earlier frame (or other code/params/seed) restarts it.
_ANIM: dict = {"key": None, "anim": None}


def anim_frames(req: dict) -> dict:
    import time
    from .sketch.animation import Animation

    source, params, seed = req.get("source", ""), req.get("params") or {}, int(req.get("seed") or 1)
    start = int(req.get("start") or 0)
    count = max(1, int(req.get("count") or 10))
    budget = float(req.get("budget_ms") or 400) / 1000
    key = (source, json.dumps(params, sort_keys=True), seed)
    anim = _ANIM["anim"]
    if anim is None or _ANIM["key"] != key or anim.frame > start:
        anim = Animation(source, params, seed)
        _ANIM.update(key=key, anim=anim)
    anim.skip_to(start)
    out, logs, err = [], [], anim.error
    t0 = time.perf_counter()
    while len(out) < count and not anim.done:
        fr = anim.next_frame()
        if fr is None:
            break
        if fr.log:
            logs.append(fr.log)
        if fr.error:
            err = fr.error
            break
        out.append({"svg": anim.frame_svg(fr), "clears": fr.clears, "ms": round(fr.ms, 1)})
        if time.perf_counter() - t0 > budget:
            break
    return {"start": start, "frames": out, "next": anim.frame, "total": anim.total, "fps": anim.fps,
            "animated": anim.animated, "done": anim.done, "log": "".join(logs)[-20000:],
            "sketch_error": err}


def sketch_export(req: dict) -> dict:
    """Render a whole animation to a file (used by the CLI-less desktop export jobs)."""
    from .sketch.video import export_animation
    return export_animation(req["source"], req["out_path"], req.get("format", "mp4"),
                            req.get("params"), int(req.get("seed") or 1), req.get("scale"),
                            req.get("frames"), req.get("fps"))


def export_capabilities(req: dict) -> dict:
    from .sketch.video import FORMATS, capabilities
    return {"formats": FORMATS, "available": capabilities()}


COMMANDS = {
    "schema": lambda req: schema(),
    "render": render_response,
    "random": random_response,
    "sketch_run": sketch_run,
    "sketch_plotter": sketch_plotter,
    "sketch_png": sketch_png,
    "sketch_examples": sketch_examples,
    "sketch_reference": sketch_reference,
    "anim_frames": anim_frames,
    "export_capabilities": export_capabilities,
}
# commands that execute user code (the server runs them in a separate process)
USER_CODE_COMMANDS = {"sketch_run", "sketch_plotter", "sketch_png", "anim_frames"}


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
