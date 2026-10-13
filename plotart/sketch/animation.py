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
from .runner import (INPUT_CALLBACKS, INPUT_DEFAULTS, MAX_LOG, SKETCH_FILE, _error_info, _seed_libraries,
                     _track_state, build_namespace, set_input_vars)


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


class _Event(dict):
    """Event passed to callbacks that take an argument: ev.x, ev.key, ev["button"] …"""
    __getattr__ = dict.get


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
                 frames: int | None = None, fps: float | None = None, endless: bool = False):
        self.source = source
        self.endless = endless         # live mode: never ends, t keeps looping
        self._input = dict(INPUT_DEFAULTS)
        self._events: list = []
        self._live_input = False
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
        sk.finalize_timing()
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
        if self.error is not None:
            return True
        return False if self.endless else self.frame >= self.total

    # -------------------------------------------------------------- input (live mode)
    def set_input(self, state: dict | None = None, events: list | None = None):
        """Mouse/keyboard state for the next frame (canvas units) plus events since the last frame.

        events: [{"type": "mouse_pressed", "x": …, "y": …, "button": "left"}, {"type": "key_pressed",
        "key": "a", "key_code": 65}, {"type": "mouse_wheel", "delta": 120}, …]
        """
        self._live_input = True
        if state:
            self._input.update({k: v for k, v in state.items() if k in INPUT_DEFAULTS or k == "midi"})
        if events:
            self._events.extend(events)

    def _apply_input(self, i: int):
        sk, ns = self.sk, self.ns
        if not self._live_input and i < len(sk.input_track):            # replay a recording
            entry = sk.input_track[i] or {}
            self._input.update(_track_state(entry))
            if entry.get("m"):
                self._input["midi"] = entry["m"]
            self._events.extend(entry.get("e") or [])
        prev = sk.input
        state = dict(self._input)
        state["pmouse_x"] = prev.get("mouse_x", state["mouse_x"])
        state["pmouse_y"] = prev.get("mouse_y", state["mouse_y"])
        events, self._events = self._events, []
        for ev in events:                        # p5 calls event handlers between frames
            typ = ev.get("type")
            if typ not in INPUT_CALLBACKS:
                continue
            if "x" in ev:
                ns.update(pmouse_x=ns.get("mouse_x", 0.0), pmouse_y=ns.get("mouse_y", 0.0),
                          mouse_x=ev["x"], mouse_y=ev["y"])
            if typ == "mouse_pressed":
                ns.update(mouse_is_pressed=True, mouse_button=ev.get("button", "left"))
            elif typ == "mouse_released":
                ns["mouse_is_pressed"] = False
            elif typ in ("key_pressed", "key_typed"):
                ns.update(key=ev.get("key", ""), key_code=ev.get("key_code", 0), key_is_pressed=True)
            elif typ == "key_released":
                ns.update(key=ev.get("key", ""), key_code=ev.get("key_code", 0), key_is_pressed=False)
            set_input_vars(ns, {})                # refresh camelCase aliases
            fn = ns.get(typ)
            if callable(fn):
                try:
                    takes_arg = fn.__code__.co_argcount > 0
                except AttributeError:
                    takes_arg = False
                if takes_arg:
                    fn(ev.get("delta", 0.0) if typ == "mouse_wheel" else _Event(ev))
                else:
                    fn()
        sk.input = state
        set_input_vars(ns, state)

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
        ns.update(frame_count=i + 1, frameCount=i + 1, t=(i % self.total) / self.total, time=i / self.fps,
                  frames=self.total, fps=self.fps)
        buf = io.StringIO()
        err = None
        t0 = time.perf_counter()
        if self.draw is not None:
            try:
                with redirect_stdout(buf), redirect_stderr(buf):
                    self._apply_input(i)
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
