"""Ableton Link for the live Studio (desktop): one shared tempo and beat with Ableton Live, Bitwig,
Traktor, TouchDesigner, phones … on the same network.

Needs the optional package LinkPython-extern (pip install LinkPython-extern). The session is
joined on first use and kept for the lifetime of the server process.
"""
from __future__ import annotations

import threading


class LinkError(RuntimeError):
    pass


_lock = threading.Lock()
_link = None


def link_state(quantum: float = 4.0) -> dict:
    """{"bpm", "beat", "peers"} of the Ableton Link session right now."""
    global _link
    with _lock:
        if _link is None:
            try:
                import link
            except ImportError:
                raise LinkError("Ableton Link braucht das Paket LinkPython-extern: "
                                "pip install LinkPython-extern") from None
            _link = link.Link(120.0)
            _link.enabled = True
        state = _link.captureSessionState()
        now = _link.clock().micros()
        return {"bpm": float(state.tempo()), "beat": float(state.beatAtTime(now, quantum)),
                "peers": int(_link.numPeers())}


def resolve_tempo(req: dict) -> str | None:
    """Replace {"link": true} in a live request by the current Link tempo. → error message or None."""
    inp = req.get("input")
    tempo = inp.get("tempo") if isinstance(inp, dict) else None
    if not (isinstance(tempo, dict) and tempo.get("link")):
        return None
    try:
        inp["tempo"] = link_state()
    except LinkError as exc:
        inp["tempo"] = None                     # fall back to the sketch's own tempo()
        return str(exc)
    return None
