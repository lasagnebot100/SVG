"""Run sketches in a separate, restartable process (used by the local web server).

User code can loop forever or crash; the worker is killed and respawned after a
timeout so the server stays responsive. The process is kept alive between runs,
so imports like numpy are only paid once.
"""
from __future__ import annotations

import multiprocessing as mp
import threading


def _loop(conn):
    from .. import bridge
    while True:
        try:
            cmd, payload = conn.recv()
        except (EOFError, KeyboardInterrupt):
            return
        try:
            out = bridge.dispatch(cmd, payload)
        except Exception as exc:   # never let the worker die on user errors
            out = {"error": f"{type(exc).__name__}: {exc}"}
        conn.send(out)


class SketchWorker:
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.lock = threading.Lock()
        self.ctx = mp.get_context("spawn")
        self.proc = None
        self.conn = None

    def _start(self):
        parent, child = self.ctx.Pipe()
        self.proc = self.ctx.Process(target=_loop, args=(child,), daemon=True)
        self.proc.start()
        child.close()
        self.conn = parent

    def _restart(self):
        if self.proc is not None and self.proc.is_alive():
            self.proc.kill()
            self.proc.join(2)
        self._start()

    def call(self, cmd: str, payload: dict, timeout: float | None = None) -> dict:
        with self.lock:
            if self.proc is None or not self.proc.is_alive():
                self._start()
            limit = timeout or self.timeout
            try:
                self.conn.send((cmd, payload))
                if not self.conn.poll(limit):
                    self._restart()
                    return {"error": f"Abgebrochen: Die Skizze lief länger als {limit:g} s (Endlosschleife?)."}
                return self.conn.recv()
            except (EOFError, BrokenPipeError, OSError):
                self._restart()
                return {"error": "Der Skizzen-Prozess ist abgestürzt (zu viel Speicher?) und wurde neu gestartet."}

    def close(self):
        if self.proc is not None and self.proc.is_alive():
            self.proc.kill()
