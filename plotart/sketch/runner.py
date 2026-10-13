"""Execute sketch source code and collect the result."""
from __future__ import annotations

import inspect
import io
import math
import random
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from functools import wraps
from pathlib import Path

from .color import Color, Gradient
from .core import CATEGORIES, Sketch
from .render_svg import render_svg
from .tools import TOOLS

SKETCH_FILE = "<skizze>"
EXAMPLES_DIR = Path(__file__).parent / "examples"
MAX_LOG = 20_000

BLEND_MODES = {
    "NORMAL": "normal", "BLEND": "normal", "MULTIPLY": "multiply", "SCREEN": "screen",
    "OVERLAY": "overlay", "DARKEN": "darken", "LIGHTEN": "lighten", "DIFFERENCE": "difference",
    "EXCLUSION": "exclusion", "ADD": "plus-lighter", "COLOR_DODGE": "color-dodge",
    "COLOR_BURN": "color-burn", "HARD_LIGHT": "hard-light", "SOFT_LIGHT": "soft-light",
    "HUE": "hue", "SATURATION": "saturation", "COLOR": "color", "LUMINOSITY": "luminosity",
}

CONSTANTS = {
    "PI": math.pi, "TAU": math.tau, "TWO_PI": math.tau, "HALF_PI": math.pi / 2,
    "QUARTER_PI": math.pi / 4, "CLOSE": True,
    "CENTER": "center", "CORNER": "corner", "CORNERS": "corners", "RADIUS": "radius",
    "LEFT": "left", "RIGHT": "right", "TOP": "top", "BOTTOM": "bottom", "BASELINE": "baseline",
    "ROUND": "round", "SQUARE": "square", "PROJECT": "project", "MITER": "miter", "BEVEL": "bevel",
    "OPEN": "open", "CHORD": "chord", "PIE": "pie", "POINTS": "points", "LINES": "lines",
    "RGB": "rgb", "HSB": "hsb", "BOLD": "bold", "ITALIC": "italic", "BOLDITALIC": "bold italic",
    "BLUR": "blur", "SHARPEN": "sharpen", "EDGES": "edges", "EMBOSS": "emboss", "GRAY": "gray",
    "INVERT": "invert", "POSTERIZE": "posterize", "THRESHOLD": "threshold", "CONTRAST": "contrast",
    "BRIGHTNESS": "brightness", "SATURATION": "saturation", "PIXELATE": "pixelate", "GRAIN": "grain",
    "DITHER": "dither", "SEPIA": "sepia", "LEVELS": "levels",
    **BLEND_MODES,
}
CONSTANTS["NORMAL"] = "normal"

MATH_NAMES = ["sin", "cos", "tan", "asin", "acos", "atan", "atan2", "sqrt", "floor", "ceil",
              "exp", "log", "hypot", "fmod", "copysign", "isclose"]


def _api_members(sk: Sketch):
    for name, fn in inspect.getmembers(type(sk), predicate=inspect.isfunction):
        cat = getattr(fn, "_api_category", None)
        if cat:
            yield name, getattr(sk, name), cat


def build_namespace(sk: Sketch) -> dict:
    ns: dict = {"__name__": "__skizze__", "__builtins__": __builtins__}
    for name, bound, _ in _api_members(sk):
        ns[name] = bound
    for name, (fn, _, needs_rng) in TOOLS.items():
        if needs_rng:
            ns[name] = _bind_rng(fn, sk)
        else:
            ns[name] = fn
    for name in MATH_NAMES:
        ns[name] = getattr(math, name)
    ns.update(CONSTANTS)
    ns.update({"math": math, "Color": Color, "Gradient": Gradient,
               "width": int(sk.width), "height": int(sk.height), "seed": sk.seed,
               "frame_count": 1, "t": 0.0, "time": 0.0, "frames": sk.anim_frames, "fps": sk.anim_fps})
    return ns


def _bind_rng(fn, sk):
    @wraps(fn)
    def bound(*args, **kw):
        kw.setdefault("rng", sk.rng)
        return fn(*args, **kw)
    return bound


def _seed_libraries(seed: int, source: str):
    random.seed(seed)
    if "numpy" not in sys.modules and "numpy" in source:
        try:
            import numpy  # noqa: F401
        except ImportError:
            pass
    np = sys.modules.get("numpy")
    if np is not None:
        np.random.seed(seed % (2 ** 32))


def _error_info(exc: BaseException) -> dict:
    if isinstance(exc, SyntaxError) and exc.filename == SKETCH_FILE:
        return {"message": f"Syntaxfehler: {exc.msg}", "line": exc.lineno,
                "trace": "".join(traceback.format_exception_only(type(exc), exc))}
    frames = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename == SKETCH_FILE]
    line = frames[-1].lineno if frames else None
    # trace limited to the sketch's own frames + the final error
    trace = "".join(traceback.format_list(frames)) + "".join(traceback.format_exception_only(type(exc), exc))
    return {"message": f"{type(exc).__name__}: {exc}", "line": line, "trace": trace}


def execute(source: str, params: dict | None = None, seed: int = 1) -> tuple[Sketch, str, dict | None, float]:
    """Run a sketch once (setup + first draw). Returns (sketch, output, error or None, ms).

    For animated sketches this is the first frame; see animation.Animation for all frames.
    """
    sk = Sketch(seed, params)
    sk.apply_keys(1)
    ns = build_namespace(sk)
    sk.ns = ns
    _seed_libraries(sk.seed, source)
    buf = io.StringIO()
    err = None
    t0 = time.perf_counter()
    try:
        code = compile(source, SKETCH_FILE, "exec")
        with redirect_stdout(buf), redirect_stderr(buf):
            exec(code, ns)
            for hook in ("setup", "draw"):
                fn = ns.get(hook)
                if callable(fn):
                    if hook == "draw":                 # like p5: fresh transform per frame
                        sk.reset_matrix()
                        sk._stack.clear()
                    fn()
            if sk._shape is not None:
                sk.end_shape()
                print("Hinweis: end_shape() fehlte und wurde ergänzt.")
    except Exception as exc:   # report everything to the editor
        err = _error_info(exc)
    log = buf.getvalue()
    if len(log) > MAX_LOG:
        log = log[:MAX_LOG] + f"\n… ({len(log) - MAX_LOG} Zeichen gekürzt)"
    return sk, log, err, (time.perf_counter() - t0) * 1000


def run_sketch(source: str, params: dict | None = None, seed: int = 1) -> dict:
    """Run a sketch and return everything the editor needs (JSON-serialisable)."""
    sk, log, err, ms = execute(source, params, seed)
    meta = {"seed": sk.seed, "params": {p.name: (params or {}).get(p.name, p.default) for p in sk.param_specs}}
    if sk._param_keys:
        meta["keyframes"] = sk._param_keys
    return {
        "svg": render_svg(sk, meta) if not err else None,
        "params": [p.to_json() for p in sk.param_specs],
        "log": log,
        "error": err,
        "seed": sk.seed,
        "width": sk.width,
        "height": sk.height,
        "unit": sk.unit,
        "items": len(sk.items),
        "ms": round(ms, 1),
        "animated": callable((sk.ns or {}).get("draw")) and sk.looping,
        "frames": sk.anim_frames,
        "fps": sk.anim_fps,
    }


def api_reference() -> list[dict]:
    """Functions available in sketches, grouped by category (for the editor's help panel)."""
    sk = Sketch()
    groups: dict[str, list] = {c: [] for c in CATEGORIES}

    def sig(fn, drop=()):
        try:
            s = inspect.signature(fn)
            ps = [p for n, p in s.parameters.items() if n not in drop]
            return "(" + ", ".join(str(p) for p in ps) + ")"
        except (TypeError, ValueError):
            return "(…)"

    for name, bound, cat in _api_members(sk):
        doc = (inspect.getdoc(bound) or "").split("\n")[0]
        groups.setdefault(cat, []).append({"name": name, "sig": sig(bound), "doc": doc})
    for name, (fn, cat, needs_rng) in TOOLS.items():
        doc = (inspect.getdoc(fn) or "").split("\n")[0]
        groups.setdefault(cat, []).append({"name": name, "sig": sig(fn, ("rng",)), "doc": doc})
    groups["Konstanten"] = [{"name": n, "sig": "", "doc": repr(v)} for n, v in CONSTANTS.items()]
    groups["Variablen"] = [
        {"name": "width", "sig": "", "doc": "Breite der Leinwand"},
        {"name": "height", "sig": "", "doc": "Höhe der Leinwand"},
        {"name": "seed", "sig": "", "doc": "aktueller Zufalls-Seed"},
        {"name": "frame_count", "sig": "", "doc": "Nummer des aktuellen Bildes (1, 2, 3 …)"},
        {"name": "t", "sig": "", "doc": "Fortschritt der Animation 0 … 1 (perfekt für Loops)"},
        {"name": "time", "sig": "", "doc": "Zeit in Sekunden seit Beginn"},
        {"name": "frames", "sig": "", "doc": "Anzahl Bilder der Animation"},
        {"name": "fps", "sig": "", "doc": "Bilder pro Sekunde"},
    ]
    return [{"category": c, "entries": sorted(e, key=lambda x: x["name"])} for c, e in groups.items() if e]


def list_examples() -> list[dict]:
    out = []
    for path in sorted(EXAMPLES_DIR.glob("*.py")):
        src = path.read_text(encoding="utf-8")
        title = path.stem
        if src.startswith('"""'):
            title = src[3:].split("\n")[0].strip().rstrip('"').strip() or title
        out.append({"name": path.stem, "title": title, "source": src})
    return out
