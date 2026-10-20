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
                   outline_fills=bool(req.get("outline_fills", True)),
                   hidden_lines=bool(req.get("hidden_lines")))
    return {"svg": to_svg(d), "stats": d.stats()}


def sketch_png(req: dict) -> dict:
    from .sketch import render_png
    sk, log, err, _ = _execute(req)
    if err:
        return {"sketch_error": err}
    png = render_png(sk, scale=req.get("scale"))
    return {"png_base64": base64.b64encode(png).decode()}


def sketch_3d(req: dict) -> dict:
    """3D shapes of the sketch as .glb (default) or .obj + .mtl (base64)."""
    from .sketch.export3d import to_glb, to_obj
    sk, log, err, _ = _execute(req)
    if err:
        return {"sketch_error": err}
    if not sk.meshes3d:
        return {"error": "Die Skizze enthält keine 3D-Formen (box, sphere, …)."}
    scale = float(req.get("scale") or 0.01)
    if req.get("format") == "obj":
        obj, mtl = to_obj(sk.meshes3d, sk.width, sk.height, scale, name=req.get("name") or "plotart")
        return {"obj_base64": base64.b64encode(obj.encode()).decode(),
                "mtl_base64": base64.b64encode(mtl.encode()).decode(), "meshes": len(sk.meshes3d)}
    return {"glb_base64": base64.b64encode(to_glb(sk.meshes3d, sk.width, sk.height, scale)).decode(),
            "meshes": len(sk.meshes3d)}


def sketch_thumb(req: dict) -> dict:
    """Small preview of one seed (for the variants grid): PNG if Pillow is there, else SVG."""
    from .sketch import render_svg
    sk, log, err, ms = _execute(req)
    if err:
        return {"seed": int(req.get("seed") or 1), "sketch_error": err}
    size = float(req.get("size") or 260)
    out = {"seed": sk.seed, "ms": round(ms, 1), "params": req.get("params") or {}}
    try:
        from .sketch import render_png
        out["png_base64"] = base64.b64encode(
            render_png(sk, scale=size / max(sk.width, sk.height), engine="pillow")).decode()
    except ImportError:
        out["svg"] = render_svg(sk)
    return out


def sketch_examples(req: dict) -> dict:
    from .languages import list_examples as language_examples
    from .sketch import list_examples
    return {"examples": list_examples(), "pde": language_examples(".pde"), "p5": language_examples(".js"),
            "r": language_examples(".R")}


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


_LIVE: dict = {"seed": None, "anim": None, "params": None, "failed": None, "failed_error": None}


def anim_live(req: dict) -> dict:
    """Live mode: one frame per call with the current mouse/keyboard/MIDI/tempo state.

    The animation keeps running (state persists) until the seed changes or {"restart": true} is
    sent. A changed source restarts it – unless {"hot": true}: then the new code is taken over
    while running (Animation.hot_swap); broken code is reported as "hot_error" and the old code
    keeps running. Sliders update without a restart – param() calls inside draw() see the new
    values immediately, with "hot" also top-level param() variables.
    """
    from .sketch.animation import Animation

    source, params, seed = req.get("source", ""), dict(req.get("params") or {}), int(req.get("seed") or 1)
    params.pop("__input__", None)                  # live input replaces a recording
    keys = params.pop("__keys__", None)
    hot = bool(req.get("hot"))
    anim = _LIVE["anim"]
    info, extra = None, {}
    restart = (anim is None or _LIVE["seed"] != seed or bool(req.get("restart"))
               or (source != anim.source and not hot))
    if not restart:
        anim.sk._param_values.update(params)
        params_changed = hot and params != _LIVE["params"]
        if source == _LIVE["failed"]:
            extra["hot_error"] = _LIVE["failed_error"]
        elif hot and (source != anim.source or params_changed):
            res = anim.hot_swap(source, refresh_params=params_changed)
            if res.get("restart"):
                restart = True
            elif res.get("error"):
                _LIVE.update(failed=source, failed_error=res["error"])
                extra["hot_error"] = res["error"]
            else:
                _LIVE.update(failed=None, failed_error=None)
                extra["swapped"] = True
                info = anim.info()
                info["log"] = anim.log
    if restart:
        anim = Animation(source, params, seed, endless=True)
        _LIVE.update(seed=seed, anim=anim, failed=None, failed_error=None)
        info = anim.info()
        info["log"] = anim.log
    _LIVE["params"] = params
    anim.sk._param_values.update(params)
    if keys is not None:
        anim.sk._param_keys = keys
    anim.set_input(req.get("input"), req.get("events"))
    out = {"info": info, "sketch_error": anim.error, **extra}
    if anim.error:
        return out
    fr = anim.next_frame()
    if fr is None:
        return {**out, "sketch_error": anim.error}
    osc_out, anim.sk._osc_out = anim.sk._osc_out, []
    sk = anim.sk
    beat_info = {"bpm": anim._tempo["bpm"] if anim._tempo else sk.bpm, "beat": sk.beat,
                 "bar": int(sk.beat // sk.beats_per_bar), "beats_per_bar": sk.beats_per_bar}
    if req.get("video") is not None:               # NDI / Spout ({"kind": None} switches it off)
        from .videoout import VideoOutError, video_for
        try:
            vo = video_for(req["video"])
            if vo is not None and fr.error is None:
                vo.send(sk, fr, anim.fps)
        except VideoOutError as exc:
            out["video_error"] = str(exc)
    return {**out, "frame": {"index": fr.index, "svg": anim.frame_svg(fr), "clears": fr.clears,
                             "ms": round(fr.ms, 1)},
            "log": fr.log, "sketch_error": fr.error, "osc_out": osc_out, "tempo": beat_info}


def pde_convert(req: dict) -> dict:
    """A Processing (.pde) sketch as plotart Python: {"source", "warnings"}."""
    from .languages.pde_convert import convert_pde
    return convert_pde(req.get("source", ""), req.get("title") or "")


def edition_features(req: dict) -> dict:
    """Traits (feature()) of many seeds for the rarity overview – in chunks: {"seeds": [...], "budget_ms"}."""
    from .sketch.edition import collect_features
    entries, done = collect_features(req.get("source", ""), req.get("seeds") or [], req.get("params"),
                                     float(req.get("budget_ms") or 1500) / 1000)
    return {"entries": entries, "done": done}


def audio_data(req: dict) -> dict:
    """An audio file of the sketch for playback in the browser (base64)."""
    from .sketch.audio import audio_file
    path = audio_file(str(req.get("name", "")))
    mime = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".flac": "audio/flac",
            ".m4a": "audio/mp4", ".aac": "audio/aac", ".opus": "audio/ogg"}.get(path.suffix.lower(),
                                                                                  "application/octet-stream")
    if path.stat().st_size > 60 * 1024 * 1024:
        return {"error": "Audiodatei zu groß für die Wiedergabe im Browser (max. 60 MB)"}
    return {"mime": mime, "base64": base64.b64encode(path.read_bytes()).decode()}


def viewer_html(req: dict) -> dict:
    """The sketch as a stand-alone web page (Pyodide, seed navigation, sliders, downloads)."""
    from .viewer import build_viewer
    return {"html": build_viewer(req.get("source", ""), int(req.get("seed") or 1), req.get("params") or {},
                                 title=req.get("title") or None)}


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
    "sketch_thumb": sketch_thumb,
    "sketch_3d": sketch_3d,
    "anim_live": anim_live,
    "edition_features": edition_features,
    "pde_convert": pde_convert,
    "audio_data": audio_data,
    "viewer_html": viewer_html,
    "export_capabilities": export_capabilities,
}
# commands that execute user code (the server runs them in a separate process)
USER_CODE_COMMANDS = {"sketch_run", "sketch_plotter", "sketch_png", "anim_frames", "sketch_thumb", "sketch_3d",
                      "anim_live", "audio_data", "edition_features"}


def dispatch(cmd: str, req: dict) -> dict:
    fn = COMMANDS.get(cmd)
    if fn is None:
        return {"error": f"unbekannter Befehl {cmd!r}"}
    if "asset_dirs" in req:            # where load_image("foto.jpg") & co. look for files
        from .sketch import data
        data.ASSET_DIRS[:] = [str(d) for d in req["asset_dirs"]]
    if "osc" in req:                   # latest OSC values from the server's receiver
        from .sketch.core import OSC_VALUES
        OSC_VALUES.clear()
        OSC_VALUES.update({str(k): list(v) for k, v in (req["osc"] or {}).items()})
    return fn(req)


def call_json(cmd: str, arg_json: str) -> str:
    """Entry point for the browser worker: JSON string in, JSON string out."""
    try:
        out = dispatch(cmd, json.loads(arg_json or "{}"))
    except Exception as exc:  # surface errors in the UI
        out = {"error": f"{type(exc).__name__}: {exc}"}
    return json.dumps(out, ensure_ascii=False)
