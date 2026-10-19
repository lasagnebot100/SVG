"""Live video output to other programs (desktop): NDI and Spout.

NDI   – OBS, Resolume, TouchDesigner (NDI In TOP), vMix, also over the network.
        pip install ndi-python numpy Pillow
Spout – Windows only, GPU texture sharing with Resolume, TouchDesigner (Syphon Spout In TOP), OBS (plugin).
        pip install SpoutGL moderngl numpy Pillow  (SpoutGL has wheels for Python 3.11–3.13)

The live frames are rasterised with Pillow (frames without background() accumulate as in the Studio)
and sent as RGBA images.
"""
from __future__ import annotations

import importlib.util
import sys

KINDS = ("ndi", "spout")
# kind → (label, [(module, pip package), …])
REQUIRES = {"ndi": ("NDI", [("NDIlib", "ndi-python"), ("numpy", "numpy"), ("PIL", "Pillow")]),
            "spout": ("Spout", [("SpoutGL", "SpoutGL"), ("moderngl", "moderngl"), ("numpy", "numpy"),
                                ("PIL", "Pillow")])}


class VideoOutError(RuntimeError):
    pass


def check_packages(kind: str):
    """Friendly error naming every missing package at once."""
    label, needs = REQUIRES[kind]
    missing = [pip for module, pip in needs if importlib.util.find_spec(module) is None]
    if not missing:
        return
    msg = f"Videoausgang {label} braucht: pip install {' '.join(missing)}"
    if "SpoutGL" in missing and sys.version_info >= (3, 14):
        msg += " (SpoutGL gibt es bisher nur für Python 3.11 bis 3.13 – sonst NDI verwenden)"
    raise VideoOutError(msg)


def _need(module: str, pip: str):
    try:
        return __import__(module)
    except ImportError:
        raise VideoOutError(f"Videoausgang braucht {pip}: pip install {pip}") from None


class _NDISender:
    def __init__(self, name: str):
        ndi = self.ndi = _need("NDIlib", "ndi-python")
        if not ndi.initialize():
            raise VideoOutError("NDI konnte nicht gestartet werden (CPU ohne SSE4.2?)")
        settings = ndi.SendCreate()
        settings.ndi_name = name
        self.handle = ndi.send_create(settings)
        if self.handle is None:
            raise VideoOutError("NDI-Sender konnte nicht angelegt werden")
        self.frame = ndi.VideoFrameV2()
        self.frame.FourCC = ndi.FOURCC_VIDEO_TYPE_RGBA

    def send(self, rgba, fps: float):
        self.frame.data = rgba
        self.frame.frame_rate_N, self.frame.frame_rate_D = int(round(fps * 1000)), 1000
        self.ndi.send_send_video_v2(self.handle, self.frame)

    def close(self):
        self.ndi.send_destroy(self.handle)


class _SpoutSender:
    GL_RGBA = 0x1908

    def __init__(self, name: str):
        spout = _need("SpoutGL", "SpoutGL")
        moderngl = _need("moderngl", "moderngl")
        self.ctx = moderngl.create_standalone_context()     # Spout needs a current OpenGL context
        self.sender = spout.SpoutSender()
        self.sender.setSenderName(name)

    def send(self, rgba, fps: float):
        h, w = rgba.shape[:2]
        if not self.sender.sendImage(rgba.tobytes(), w, h, self.GL_RGBA, False, 0):
            raise VideoOutError("Spout: Bild konnte nicht gesendet werden")

    def close(self):
        self.sender.releaseSender()
        self.ctx.release()


class VideoOut:
    """Sender for one kind/name; feed it the live frames of a sketch with send(sk, frame, fps)."""

    def __init__(self, kind: str, name: str = "plotart", width: int = 1280):
        if kind not in KINDS:
            raise VideoOutError(f"Unbekannter Videoausgang {kind!r} – möglich: ndi, spout")
        check_packages(kind)
        self.np = _need("numpy", "numpy")
        self.kind, self.name, self.width = kind, name, int(width)
        self.sender = _NDISender(name) if kind == "ndi" else _SpoutSender(name)
        self.canvas = None
        self._sketch = None

    def send(self, sk, frame, fps: float):
        from .sketch.export import PillowCanvas
        if self.canvas is None or self._sketch is not sk:          # new sketch run or first frame
            self.canvas = PillowCanvas(sk.width, sk.height, self.width / sk.width)
            self._sketch = sk
        if frame.clears or frame.index == 0:
            self.canvas.clear()
        self.canvas.draw(frame.items)
        rgba = self.np.ascontiguousarray(self.np.asarray(self.canvas.image(), dtype=self.np.uint8))
        self.sender.send(rgba, fps)
        return rgba.shape[1], rgba.shape[0]

    def close(self):
        self.sender.close()


_CURRENT: dict = {"key": None, "out": None}


def video_for(spec: dict | None) -> VideoOut | None:
    """The sender for {"kind", "name", "width"} – reused while unchanged, closed when switched off."""
    key = (spec.get("kind"), spec.get("name") or "plotart", int(spec.get("width") or 1280)) if spec else None
    if key is None or not key[0]:
        key = None
    if key != _CURRENT["key"]:
        if _CURRENT["out"] is not None:
            _CURRENT["out"].close()
        _CURRENT.update(key=None, out=None)
        if key is not None:
            _CURRENT.update(key=key, out=VideoOut(*key))
    return _CURRENT["out"]
