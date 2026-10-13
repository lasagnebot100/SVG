"""Local web UI: the Studio (live-coding sketches) and the generator page (standard library only)."""
from __future__ import annotations

import hmac
import json
import multiprocessing as mp
import os
import queue
import re
import secrets
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

from . import bridge
from .sketch.worker import SketchWorker
from .sketchfiles import SketchFileError, SketchFolder

STATIC = Path(__file__).parent / "static"
OUTPUT_DIR = Path(os.environ.get("PLOTART_OUTPUT", "output"))

PAGES = {"/": "studio.html", "/index.html": "studio.html", "/studio": "studio.html",
         "/generatoren": "generators.html", "/generatoren.html": "generators.html"}
FILES = {"/vendor/codemirror.js": ("vendor/codemirror.js", "text/javascript; charset=utf-8"),
         "/vendor/codemirror.css": ("vendor/codemirror.css", "text/css; charset=utf-8")}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
EXTENSIONS = {"mp4": "mp4", "webm": "webm", "gif": "gif", "png": "zip"}
MIME = {".mp4": "video/mp4", ".webm": "video/webm", ".gif": "image/gif", ".zip": "application/zip",
        ".svg": "image/svg+xml", ".png": "image/png"}


# ------------------------------------------------------------------------- export jobs
def _export_entry(q, req):
    """Runs in a separate process: render the animation, report progress via the queue."""
    from .sketch.video import ExportError, export_animation
    last = [0.0]

    def progress(i, n):
        now = time.monotonic()
        if now - last[0] > 0.2 or i == n:
            last[0] = now
            q.put(("progress", i, n))
    try:
        res = export_animation(req["source"], req["out_path"], req["format"], req.get("params"),
                               int(req.get("seed") or 1), req.get("scale"), req.get("frames"),
                               req.get("fps"), progress=progress)
        q.put(("done", res))
    except ExportError as exc:
        q.put(("error", str(exc)))
    except Exception as exc:   # noqa: BLE001 – report anything to the UI
        q.put(("error", f"{type(exc).__name__}: {exc}"))


class ExportJob:
    def __init__(self, req: dict):
        self.id = secrets.token_hex(6)
        self.state = "running"
        self.progress, self.total = 0, int(req.get("frames") or 0)
        self.result, self.error = None, None
        self.started = time.time()
        self.file = Path(req["out_path"]).name
        ctx = mp.get_context("spawn")
        self.q = ctx.Queue()
        self.proc = ctx.Process(target=_export_entry, args=(self.q, req), daemon=True)
        self.proc.start()
        threading.Thread(target=self._watch, daemon=True).start()

    def _watch(self):
        while self.state == "running":
            try:
                msg = self.q.get(timeout=0.5)
            except queue.Empty:
                if not self.proc.is_alive() and self.q.empty():
                    if self.state == "running":
                        self.state, self.error = "error", "Der Export-Prozess wurde unerwartet beendet."
                continue
            if msg[0] == "progress":
                self.progress, self.total = msg[1], msg[2]
            elif msg[0] == "done":
                self.state, self.result = "done", msg[1]
            elif msg[0] == "error":
                self.state, self.error = "error", msg[1]

    def cancel(self):
        if self.state == "running":
            self.state = "cancelled"
            self.proc.kill()
            out = OUTPUT_DIR / self.file
            if out.exists():
                out.unlink()

    def status(self) -> dict:
        out = {"id": self.id, "state": self.state, "progress": self.progress, "total": self.total,
               "seconds": round(time.time() - self.started, 1), "error": self.error}
        if self.state == "done":
            out.update(file=self.file, url="files/" + quote(self.file), bytes=self.result["bytes"],
                       width=self.result["width"], height=self.result["height"])
        return out


def _safe_stem(name: str) -> str:
    stem = re.sub(r"[^\w\-]+", "_", (name or "animation").rsplit(".", 1)[0]).strip("_")
    return stem[:60] or "animation"


class Handler(BaseHTTPRequestHandler):
    server_version = "plotart"
    worker: SketchWorker = None
    token: str | None = None          # required when the server is reachable from the network
    sketches: SketchFolder = None
    jobs: dict[str, ExportJob] = {}

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    def _send(self, body: bytes, ctype: str, status: int = 200, cache: bool = False):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "max-age=3600" if cache else "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status: int = 200):
        self._send(json.dumps(obj, ensure_ascii=False).encode(), "application/json", status)

    def _authorized(self) -> bool:
        if not self.token:
            return True
        given = self.headers.get("X-Plotart-Token", "")
        return hmac.compare_digest(given, self.token)

    def _authorized_query(self) -> bool:
        """Downloads are plain links, so the token may also come as ?token=…"""
        if self._authorized():
            return True
        q = urlparse(self.path).query
        given = next((v for k, v in (p.split("=", 1) for p in q.split("&") if "=" in p) if k == "token"), "")
        return hmac.compare_digest(unquote(given), self.token)

    def _send_file(self, path: Path):
        size = path.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(path.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(size))
        self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(path.name)}")
        self.end_headers()
        with open(path, "rb") as f:
            while chunk := f.read(1 << 20):
                self.wfile.write(chunk)

    def _desktop_or_none(self, cmd: str, req: dict):
        try:
            return self._desktop_command(cmd, req)
        except SketchFileError as exc:
            return {"error": str(exc)}

    def _desktop_command(self, cmd: str, req: dict):
        """Commands that only exist in the desktop server (files, export jobs)."""
        if cmd == "sketch_files":
            return {"dir": str(self.sketches.dir), "files": self.sketches.list()}
        if cmd == "sketch_file_load":
            return self.sketches.load(req.get("name", ""))
        if cmd == "sketch_file_save":
            return self.sketches.save(req.get("name", ""), req.get("source", ""), bool(req.get("overwrite", True)))
        if cmd == "sketch_file_stat":
            return self.sketches.stat(req.get("name", ""))
        if cmd == "export_start":
            fmt = req.get("format", "mp4")
            if fmt not in EXTENSIONS:
                return {"error": f"Unbekanntes Format {fmt!r}"}
            if any(j.state == "running" for j in self.jobs.values()):
                return {"error": "Es läuft bereits ein Export – bitte warten oder abbrechen."}
            stem = f"{_safe_stem(req.get('name'))}_{int(req.get('seed') or 1)}"
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            req = {**req, "out_path": str((OUTPUT_DIR / f"{stem}.{EXTENSIONS[fmt]}").resolve())}
            job = ExportJob(req)
            self.jobs[job.id] = job
            return job.status()
        if cmd in ("export_status", "export_cancel"):
            job = self.jobs.get(req.get("id", ""))
            if job is None:
                return {"error": "Unbekannter Export"}
            if cmd == "export_cancel":
                job.cancel()
            return job.status()
        return None

    def do_GET(self):
        path = urlparse(self.path).path
        if path in PAGES:
            self._send((STATIC / PAGES[path]).read_bytes(), "text/html; charset=utf-8")
        elif path in FILES:
            rel, ctype = FILES[path]
            self._send((STATIC / rel).read_bytes(), ctype, cache=True)
        elif path == "/backend.js":     # only used by the standalone web app
            self._send(b"", "text/javascript")
        elif path.startswith("/files/"):
            if not self._authorized_query():
                return self._send(b"forbidden", "text/plain", 403)
            name = unquote(path[len("/files/"):])
            target = (OUTPUT_DIR / name).resolve()
            if "/" in name or "\\" in name or target.parent != OUTPUT_DIR.resolve() or not target.is_file():
                return self._send(b"not found", "text/plain", 404)
            self._send_file(target)
        elif path == "/api/generators":
            if not self._authorized():
                return self._json({"error": "Zugangs-Token fehlt oder ist falsch"}, 403)
            self._json({**bridge.schema(), "output_dir": str(OUTPUT_DIR.resolve())})
        else:
            self._send(b"not found", "text/plain", 404)

    def do_POST(self):
        if not self._authorized():
            return self._json({"error": "Zugangs-Token fehlt oder ist falsch"}, 403)
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length) or b"{}")
            cmd = urlparse(self.path).path.removeprefix("/api/")
            if cmd == "save":
                d, svg = bridge.render_request(req)
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                path = OUTPUT_DIR / f"{d.meta['generator']}_{d.meta['seed']}.svg"
                path.write_text(svg, encoding="utf-8")
                self._json({"path": str(path.resolve())})
            elif (out := self._desktop_or_none(cmd, req)) is not None:
                self._json(out, 400 if out.get("error") and out.get("state") != "error" else 200)
            elif cmd in bridge.USER_CODE_COMMANDS:
                out = self.worker.call(cmd, req)
                self._json(out, 500 if "error" in out else 200)
            elif cmd in bridge.COMMANDS:
                self._json(bridge.dispatch(cmd, req))
            else:
                self._send(b"not found", "text/plain", 404)
        except Exception as exc:  # report errors to the UI instead of crashing
            traceback.print_exc()
            self._json({"error": str(exc)}, 500)


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True,
          timeout: float = 30.0, sketch_dir: str | Path = "skizzen"):
    Handler.worker = SketchWorker(timeout=timeout)
    Handler.sketches = SketchFolder(sketch_dir)
    Handler.token = None if host in LOCAL_HOSTS else secrets.token_urlsafe(12)
    httpd = ThreadingHTTPServer((host, port), Handler)
    shown = "localhost" if host in LOCAL_HOSTS or host == "0.0.0.0" else host
    url = f"http://{shown}:{port}/"
    if Handler.token:
        url += f"?token={Handler.token}"
        print("Achtung: Der Server ist im Netzwerk erreichbar und führt Python-Code aus.\n"
              "Nur in vertrauenswürdigen Netzen verwenden. Zugriff nur mit diesem Link:")
        if host == "0.0.0.0":
            print("  (am anderen Gerät 'localhost' durch die IP-Adresse dieses Computers ersetzen)")
    print(f"plotart läuft auf {url}  (Beenden mit Strg+C)")
    print(f"Skizzen-Ordner: {Handler.sketches.dir}   ·   Exporte: {OUTPUT_DIR.resolve()}")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        Handler.worker.close()
        for job in Handler.jobs.values():
            job.cancel()
