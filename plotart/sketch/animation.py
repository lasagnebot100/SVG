"""Frame-by-frame execution of animated sketches (p5.js semantics).

setup() runs once, draw() once per frame. Variables persist between frames, the
canvas is NOT cleared automatically – call background() in draw() for a fresh
frame, or a translucent background for trails. Transformations are reset before
every frame, styles persist (like p5).
"""
from __future__ import annotations

import io
import time
from contextlib import redirect_stderr, redirect_stdout

from .color import Color, Gradient
from .core import Item, Sketch
from .render_svg import render_svg
from .runner import MAX_LOG, SKETCH_FILE, _error_info, _seed_libraries, build_namespace


def _is_opaque_background(it: Item) -> bool:
    if it.kind != "background" or it.style.blend not in ("normal", "blend"):
        return False
    p = it.data["paint"]
    if isinstance(p, Color):
        return p.a >= 0.999
    if isinstance(p, Gradient):
        return all(c.a >= 0.999 for _, c in p.stops)
    return False


def trim_frame(items: list[Item]) -> tuple[list[Item], bool]:
    """Drop everything hidden by the last opaque background. Returns (items, clears_canvas)."""
    for k in range(len(items) - 1, -1, -1):
        if _is_opaque_background(items[k]):
            return items[k:], True
    return items, False


class Frame:
    __slots__ = ("index", "items", "clears", "log", "error", "ms", "meshes")

    def __init__(self, index, items, clears, log, error, ms, meshes=None):
        self.index = index
        self.meshes = meshes or []          # world-space 3D meshes of this frame (glTF/OBJ/Blender)
        self.items = items
        self.clears = clears
        self.log = log
        self.error = error
        self.ms = ms


class Animation:
    """Runs a sketch; call next_frame() repeatedly (frames are produced strictly in order)."""

    def __init__(self, source: str, params: dict | None = None, seed: int = 1,
                 frames: int | None = None, fps: float | None = None):
        self.source = source
        self.sk = sk = Sketch(seed, params)
        sk.apply_keys(1)
        self.ns = ns = build_namespace(sk)
        sk.ns = ns
        self.frame = 0                 # frames produced so far
        self.error = None
        self.log = ""
        _seed_libraries(sk.seed, source)
        ns.update(frame_count=1, t=0.0, time=0.0, frames=sk.anim_frames, fps=sk.anim_fps)
        buf = io.StringIO()
        try:
            code = compile(source, SKETCH_FILE, "exec")
            with redirect_stdout(buf), redirect_stderr(buf):
                exec(code, ns)
                setup = ns.get("setup")
                if callable(setup):
                    setup()
        except Exception as exc:
            self.error = _error_info(exc)
        self.log = buf.getvalue()[:MAX_LOG]
        self.draw = ns.get("draw") if callable(ns.get("draw")) else None
        if frames is not None:
            sk.anim_frames = max(1, int(frames))
        if fps is not None:
            sk.anim_fps = float(fps)
        self.animated = self.draw is not None and sk.looping
        self.total = sk.anim_frames if self.animated else 1
        self.fps = sk.anim_fps
        self._pending_setup_items = sk.items     # drawn before the first draw()
        sk.items = []
        sk._flush3d()
        self._pending_setup_items += sk.items
        sk.items = []
        self._pending_setup_meshes = sk.meshes3d

    # -------------------------------------------------------------- info
    @property
    def width(self):
        return self.sk.width

    @property
    def height(self):
        return self.sk.height

    @property
    def done(self) -> bool:
        return self.error is not None or self.frame >= self.total

    def info(self) -> dict:
        return {"animated": self.animated, "frames": self.total, "fps": self.fps,
                "width": self.sk.width, "height": self.sk.height, "unit": self.sk.unit,
                "params": [p.to_json() for p in self.sk.param_specs]}

    # -------------------------------------------------------------- stepping
    def next_frame(self) -> Frame | None:
        """Produce the next frame, or None when finished / after an error."""
        if self.done:
            return None
        sk, ns, i = self.sk, self.ns, self.frame
        sk.items = self._pending_setup_items
        self._pending_setup_items = []
        sk.reset_matrix()                     # p5 resets transformations (and lights) every frame
        sk._stack.clear()
        sk.meshes3d = self._pending_setup_meshes
        self._pending_setup_meshes = []
        sk.begin_frame3d()
        sk.apply_keys(i + 1)                  # animated sliders
        ns.update(frame_count=i + 1, t=i / self.total, time=i / self.fps,
                  frames=self.total, fps=self.fps)
        buf = io.StringIO()
        err = None
        t0 = time.perf_counter()
        if self.draw is not None:
            try:
                with redirect_stdout(buf), redirect_stderr(buf):
                    self.draw()
                    if sk._shape is not None:
                        sk.end_shape()
                    sk._flush3d()
            except Exception as exc:
                err = _error_info(exc)
                self.error = err
        items, clears = trim_frame(sk.items)
        if i == 0:
            clears = True                     # the first frame always starts on an empty canvas
        meshes, sk.items = sk.meshes3d, []
        self.frame += 1
        return Frame(i, items, clears, buf.getvalue()[:MAX_LOG], err, (time.perf_counter() - t0) * 1000, meshes)

    def skip_to(self, index: int):
        """Advance (without keeping items) until the next produced frame is `index`."""
        while self.frame < index and not self.done:
            self.next_frame()

    def frame_svg(self, frame: Frame) -> str:
        return render_svg(self.sk, items=frame.items)
