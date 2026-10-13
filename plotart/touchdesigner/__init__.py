"""plotart inside TouchDesigner: a sketch as a live texture in a Script TOP.

TouchDesigner (TD) ships its own Python 3.11 with numpy. plotart itself is pure
Python; for rasterising it needs Pillow, which you install once for Python 3.11
and add to TD's module path (see docs/touchdesigner.md).

    from plotart.touchdesigner import TDRenderer
    r = TDRenderer("C:/kunst/skizzen/wellen.py", seed=3, scale=1.0)
    arr = r.next_frame(osc={"/td/level": [0.4]}, mouse=(0.5, 0.5, False))
    scriptOp.copyNumpyArray(arr)          # in the Script TOP's onCook()

Works outside TD as well (tests, other hosts that want numpy frames).
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from ..sketch.animation import Animation
from ..sketch.core import OSC_VALUES
from ..sketch.export import make_canvas, px_per_unit


class TDRenderer:
    """Runs a sketch frame by frame and returns RGBA numpy arrays (h, w, 4, uint8)."""

    def __init__(self, source_or_path: str, seed: int = 1, params: dict | None = None,
                 scale: float | None = None, flip: bool = True, reload: bool = True):
        self.path = None
        p = Path(str(source_or_path))
        if "\n" not in str(source_or_path) and p.suffix == ".py" and p.exists():
            self.path = p
        self.source = None if self.path else str(source_or_path)
        self.seed, self.params, self.scale, self.flip, self.reload = seed, dict(params or {}), scale, flip, reload
        self.error: str | None = None
        self.log = ""
        self._mtime = None
        self._anim = None
        self._canvas = None
        self._last_check = 0.0
        self.restart()

    # ------------------------------------------------------------- lifecycle
    def _read(self) -> str:
        if self.path is None:
            return self.source
        self._mtime = os.path.getmtime(self.path)
        return self.path.read_text(encoding="utf-8")

    def restart(self, seed: int | None = None, params: dict | None = None):
        """(Re)start the sketch – e.g. after a new seed or when the file changed."""
        if seed is not None:
            self.seed = int(seed)
        if params is not None:
            self.params = dict(params)
        if self.path is not None:
            from ..sketch import data
            folder = str(self.path.parent)
            if folder not in data.ASSET_DIRS:
                data.ASSET_DIRS.insert(0, folder)              # load_image("…") next to the sketch
        self._anim = Animation(self._read(), self.params, self.seed, endless=True)
        self.error = _err(self._anim.error)
        self.log = self._anim.log
        sk = self._anim.sk
        scale = self.scale or px_per_unit(sk, dpi=96)
        self._canvas = make_canvas(sk, scale, "pillow")

    def _maybe_reload(self):
        if not (self.reload and self.path) or time.monotonic() - self._last_check < 0.5:
            return
        self._last_check = time.monotonic()
        try:
            if os.path.getmtime(self.path) != self._mtime:
                self.restart()
        except OSError:
            pass

    @property
    def width(self) -> int:
        return self._canvas.W

    @property
    def height(self) -> int:
        return self._canvas.H

    # ------------------------------------------------------------- frames
    def set_param(self, name: str, value):
        """Slider value (takes effect immediately when param() is called inside draw())."""
        self.params[name] = value
        if self._anim is not None:
            self._anim.sk._param_values[name] = value

    def next_frame(self, osc: dict | None = None, mouse: tuple | None = None, events: list | None = None):
        """Advance one frame → numpy array (height, width, 4) uint8, RGBA.

        osc:   {"/adresse": [werte]} – read by osc() in the sketch
        mouse: (u, v, pressed) with u, v in 0–1 (TD panel coordinates, v from the bottom)
        """
        import numpy as np
        self._maybe_reload()
        if osc:
            OSC_VALUES.update({k: list(v) if isinstance(v, (list, tuple)) else [v] for k, v in osc.items()})
        a = self._anim
        if mouse is not None:
            u, v, pressed = mouse
            a.set_input({"mouse_x": float(u) * a.sk.width, "mouse_y": (1 - float(v)) * a.sk.height,
                         "mouse_is_pressed": bool(pressed)}, events)
        elif events:
            a.set_input(None, events)
        if self.error is None:
            fr = a.next_frame()
            if fr is not None:
                self.log = fr.log
                if fr.error:
                    self.error = _err(fr.error)
                else:
                    if fr.clears:
                        self._canvas.clear()
                    self._canvas.draw(fr.items)
        img = np.asarray(self._canvas.image().convert("RGBA"), dtype=np.uint8)
        if self.flip:                       # TD textures start at the bottom row
            img = img[::-1]
        return np.ascontiguousarray(img)

    def osc_out(self) -> list:
        """Messages the sketch sent with osc_send() since the last call: [(address, [values])]."""
        sk = self._anim.sk
        out, sk._osc_out = sk._osc_out, []
        return out

    def meshes(self) -> list:
        """3D meshes of the current frame (world coordinates) – e.g. for a Script SOP."""
        return list(self._anim.sk.meshes3d)


def _err(err: dict | None) -> str | None:
    if not err:
        return None
    return (f"Zeile {err['line']}: " if err.get("line") else "") + err["message"]


def callbacks_template() -> str:
    """Text of the Script TOP callbacks DAT (see script_top_callbacks.py)."""
    return (Path(__file__).parent / "script_top_callbacks.py").read_text(encoding="utf-8")
