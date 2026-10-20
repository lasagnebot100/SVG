"""Local web UI: the Studio (live-coding sketches) and the generator page (standard library only)."""
from __future__ import annotations

import hmac
import json
import multiprocessing as mp
import os
import queue
import re
import secrets
import socket
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
from .tempo import resolve_tempo

STATIC = Path(__file__).parent / "static"
OUTPUT_DIR = Path(os.environ.get("PLOTART_OUTPUT", "output"))

PAGES = {"/": "studio.html", "/index.html": "studio.html", "/studio": "studio.html",
         "/generatoren": "generators.html", "/generatoren.html": "generators.html",
         "/ausgabe": "ausgabe.html", "/ausgabe.html": "ausgabe.html"}
FILES = {"/vendor/codemirror.js": ("vendor/codemirror.js", "text/javascript; charset=utf-8"),
         "/vendor/codemirror.css": ("vendor/codemirror.css", "text/css; charset=utf-8")}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
EXTENSIONS = {"mp4": "mp4", "webm": "webm", "gif": "gif", "png": "zip", "blend": "blend", "series": "zip",
              "tiles": "zip"}
ASSET_TYPES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".csv", ".json", ".txt",
               ".svg", ".ttf", ".ttc", ".otf"}
MAX_ASSET_BYTES = 50 * 1024 * 1024
MIME = {".mp4": "video/mp4", ".webm": "video/webm", ".gif": "image/gif", ".zip": "application/zip",
        ".svg": "image/svg+xml", ".png": "image/png", ".blend": "application/x-blender"}


# ------------------------------------------------------------------------- export jobs
def _export_entry(q, req):
    """Runs in a separate process: render the animation, report progress via the queue."""
    from .sketch import data
    from .sketch.video import ExportError, export_animation
    data.ASSET_DIRS[:] = req.get("asset_dirs") or []
    last = [0.0]

    def progress(i, n):
        now = time.monotonic()
        if now - last[0] > 0.2 or i == n:
            last[0] = now
            q.put(("progress", i, n))
    try:
        if req["format"] == "series":
            from .sketch.series import export_series
            out_dir = Path(req["out_path"]).with_suffix("")
            res = export_series(req["source"], out_dir, req["seeds"], req.get("params"),
                                formats=req.get("formats") or ["png"], scale=req.get("scale"),
                                pen_width=float(req.get("pen_width") or 0.45),
                                hidden_lines=bool(req.get("hidden_lines")), stem=req.get("stem") or "skizze",
                                progress=progress, zip_path=req["out_path"], artist=str(req.get("artist") or ""))
            res = {**res, "bytes": os.path.getsize(req["out_path"]), "width": 0, "height": 0}
            q.put(("done", res))
            return
        if req["format"] == "tiles":
            import shutil
            from .sketch import execute
            from .sketch.tiles import TileError, export_tiles
            from .viewer import sketch_doc
            sk, _log, err, _ms = execute(req["source"], req.get("params"), int(req.get("seed") or 1))
            if err:
                raise ExportError(f"Die Skizze hat einen Fehler: {err['message']}")
            out_dir = Path(req["out_path"]).with_suffix("")
            try:
                res = export_tiles(sk, out_dir, req.get("paper") or "A4", None, req.get("print_width") or None,
                                   float(req.get("overlap") or 10), dpi=int(req.get("dpi") or 200),
                                   title=sketch_doc(req["source"])[0], progress=progress)
            except TileError as exc:
                raise ExportError(str(exc)) from exc
            shutil.make_archive(str(out_dir), "zip", out_dir.parent, out_dir.name)
            q.put(("done", {**res, "bytes": os.path.getsize(req["out_path"]), "width": 0, "height": 0}))
            return
        if req["format"] == "blend":
            from .blender.make import BlenderError, make_blend
            from .blender.scene import SceneError
            q.put(("progress", 0, 1))
            try:
                res = make_blend(req["source"], req["out_path"], params=req.get("params"),
                                 seed=int(req.get("seed") or 1), max_frames=req.get("frames"),
                                 options=req.get("blender") or {})
            except (BlenderError, SceneError) as exc:
                raise ExportError(str(exc)) from exc
            res = {**res, "bytes": os.path.getsize(req["out_path"]), "width": 0, "height": 0}
        else:
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
    osc_in = None                     # OSCServer (studio --osc-in PORT)
    osc_out = None                    # OSCClient (studio --osc-out HOST:PORT)
    listeners: list = []              # Server-Sent-Event queues of open Studio tabs

    @classmethod
    def broadcast(cls, msg: dict):
        for q in list(cls.listeners):
            try:
                q.put_nowait(msg)
            except queue.Full:
                pass

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
        """Commands that only exist in the desktop server (files, export jobs, Processing)."""
        if cmd == "pde_run":
            from .languages.processing import ProcessingError, frames_as_svg, run_pde
            try:
                r = run_pde(req.get("source", ""), req.get("frames"), int(req.get("seed") or 1))
            except ProcessingError as exc:
                return {"error": str(exc)}
            return {"frames": [{"svg": s, "clears": True} for s in frames_as_svg(r["frames"])],
                    "width": r["width"], "height": r["height"], "fps": 30, "log": r["log"], "ms": r["ms"],
                    "sketch_error": r["error"]}
        if cmd == "sketch_files":
            return {"dir": str(self.sketches.dir), "files": self.sketches.list()}
        if cmd == "sketch_file_load":
            return self.sketches.load(req.get("name", ""))
        if cmd == "sketch_file_save":
            return self.sketches.save(req.get("name", ""), req.get("source", ""), bool(req.get("overwrite", True)))
        if cmd == "sketch_file_stat":
            return self.sketches.stat(req.get("name", ""))
        if cmd == "sketch_history":
            return {"versions": self.sketches.history(req.get("name", ""))}
        if cmd == "sketch_history_load":
            return self.sketches.history_load(req.get("name", ""), req.get("version", ""))
        if cmd == "favorites_load":
            return self.sketches.meta_load(req.get("name", ""))
        if cmd == "favorites_save":
            meta = self.sketches.meta_load(req.get("name", ""))
            meta["favorites"] = req.get("favorites") or []
            return self.sketches.meta_save(req.get("name", ""), meta)
        if cmd == "asset_list":
            d = self.sketches.dir / "daten"
            files = sorted(p for p in d.iterdir() if p.is_file() and p.suffix.lower() in ASSET_TYPES) \
                if d.exists() else []
            return {"dir": str(d), "files": [{"name": p.name, "size": p.stat().st_size} for p in files]}
        if cmd == "asset_put":
            import base64
            name = Path(req.get("name", "")).name
            if not name or name.startswith(".") or Path(name).suffix.lower() not in ASSET_TYPES:
                return {"error": "Dateityp nicht erlaubt (Bilder, CSV, JSON, TXT, SVG, Schriften)"}
            data = base64.b64decode(req.get("data", ""))
            if len(data) > MAX_ASSET_BYTES:
                return {"error": "Datei zu groß (max. 50 MB)"}
            d = self.sketches.dir / "daten"
            d.mkdir(parents=True, exist_ok=True)
            (d / name).write_bytes(data)
            return {"name": name, "size": len(data)}
        if cmd == "blender_status":
            import importlib.util
            from .blender.make import find_blender
            # only look whether bpy is installed – importing it here would be slow and heavy
            via = "bpy" if importlib.util.find_spec("bpy") else ("blender" if find_blender() else None)
            return {"available": via is not None, "via": via}
        if cmd == "blender_addon":
            from .blender.package import build_addon
            path = build_addon(OUTPUT_DIR / "plotart_blender.zip")
            return {"file": path.name, "url": "files/" + quote(path.name), "bytes": path.stat().st_size}
        if cmd == "export_start":
            fmt = req.get("format", "mp4")
            if fmt not in EXTENSIONS:
                return {"error": f"Unbekanntes Format {fmt!r}"}
            if any(j.state == "running" for j in self.jobs.values()):
                return {"error": "Es läuft bereits ein Export – bitte warten oder abbrechen."}
            stem = f"{_safe_stem(req.get('name'))}_{int(req.get('seed') or 1)}"
            if fmt == "series":
                seeds = [int(s) for s in (req.get("seeds") or [])][:1000]
                if not seeds:
                    return {"error": "Keine Seeds angegeben"}
                stem = f"{_safe_stem(req.get('name'))}_serie_{seeds[0]}-{seeds[-1]}"
                req = {**req, "seeds": seeds, "frames": len(seeds), "stem": _safe_stem(req.get("name"))}
            elif fmt == "tiles":
                stem += f"_grossformat_{_safe_stem(req.get('paper') or 'A4')}"
                req = {**req, "frames": 0}
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            req = {**req, "out_path": str((OUTPUT_DIR / f"{stem}.{EXTENSIONS[fmt]}").resolve()),
                   "asset_dirs": [str(self.sketches.dir)]}
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
        elif path == "/api/events":
            if not self._authorized_query():
                return self._send(b"forbidden", "text/plain", 403)
            self._event_stream()
        elif path == "/api/generators":
            if not self._authorized():
                return self._json({"error": "Zugangs-Token fehlt oder ist falsch"}, 403)
            self._json({**bridge.schema(), "output_dir": str(OUTPUT_DIR.resolve())})
        else:
            self._send(b"not found", "text/plain", 404)

    def _event_stream(self):
        """Server-Sent Events: remote control of the Studio (OSC → slider, seed, play …)."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        q = queue.Queue(maxsize=500)
        Handler.listeners.append(q)
        hello = {"type": "hello"}
        if self.osc_in is not None:
            hello["osc"] = f"empfange auf Port {self.osc_in.port}" + (
                f", sende an {self.osc_out.addr[0]}:{self.osc_out.addr[1]}" if self.osc_out else "")
        try:
            self.wfile.write(f"data: {json.dumps(hello)}\n\n".encode())
            self.wfile.flush()
            while True:
                try:
                    msg = q.get(timeout=15)
                    self.wfile.write(f"data: {json.dumps(msg, ensure_ascii=False)}\n\n".encode())
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            Handler.listeners.remove(q)

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
                req["asset_dirs"] = [str(self.sketches.dir)]
                if self.osc_in is not None:
                    req["osc"] = self.osc_in.snapshot()
                link_error = resolve_tempo(req) if cmd == "anim_live" else None
                peers = ((req.get("input") or {}).get("tempo") or {}).get("peers")
                out = self.worker.call(cmd, req)
                if link_error:
                    out["link_error"] = link_error
                elif peers is not None and isinstance(out.get("tempo"), dict):
                    out["tempo"]["peers"] = peers
                if self.osc_out is not None and out.get("osc_out"):
                    for address, values in out["osc_out"]:
                        try:
                            self.osc_out.send(address, *values)
                        except OSError:
                            pass
                self._json(out, 500 if "error" in out else 200)
            elif cmd in bridge.COMMANDS:
                self._json(bridge.dispatch(cmd, req))
            else:
                self._send(b"not found", "text/plain", 404)
        except Exception as exc:  # report errors to the UI instead of crashing
            traceback.print_exc()
            self._json({"error": str(exc)}, 500)


def _osc_to_studio(address: str, values: list):
    """Control messages become Studio events; everything else is read by osc() in sketches."""
    v = values[0] if values else None
    if address.startswith("/param/") and v is not None:
        Handler.broadcast({"type": "param", "name": unquote(address[len("/param/"):]), "value": v})
    elif address == "/seed" and v is not None:
        Handler.broadcast({"type": "seed", "value": v})
    elif address in ("/random", "/play", "/pause"):
        Handler.broadcast({"type": address[1:]})
    elif address == "/live":
        Handler.broadcast({"type": "live", "value": bool(v) if v is not None else True})


class _IPv6Server(ThreadingHTTPServer):
    address_family = socket.AF_INET6


def _ipv6_loopback(port: int):
    """Also answer on ::1. Browsers try IPv6 first for "localhost"; on Windows a refused ::1
    connection costs about 300 ms – per request, which made the live mode crawl at 3 fps."""
    try:
        srv = _IPv6Server(("::1", port), Handler)
    except OSError:                              # no IPv6 on this machine
        return None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True,
          timeout: float = 30.0, sketch_dir: str | Path = "skizzen",
          osc_in: int | None = None, osc_out: str | None = None):
    if osc_in:
        from .osc import OSCServer
        Handler.osc_in = OSCServer(osc_in, on_message=_osc_to_studio)
        print(f"OSC: empfange auf UDP-Port {Handler.osc_in.port} (/param/<Name>, /seed, /play, /pause, osc() in Skizzen)")
    if osc_out:
        from .osc import OSCClient
        h, _, pt = osc_out.rpartition(":")
        Handler.osc_out = OSCClient(h or "127.0.0.1", int(pt))
        print(f"OSC: sende osc_send()-Nachrichten an {h or '127.0.0.1'}:{pt}")
    Handler.worker = SketchWorker(timeout=timeout)
    Handler.sketches = SketchFolder(sketch_dir)
    Handler.token = None if host in LOCAL_HOSTS else secrets.token_urlsafe(12)
    httpd = ThreadingHTTPServer((host, port), Handler)
    ipv6 = _ipv6_loopback(port) if host in ("127.0.0.1", "localhost") else None
    shown = "localhost" if host in LOCAL_HOSTS or host == "0.0.0.0" else host
    if host in ("127.0.0.1", "localhost") and ipv6 is None:
        shown = "127.0.0.1"                      # "localhost" would try ::1 first – slow on Windows
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
        if ipv6 is not None:
            ipv6.server_close()
        Handler.worker.close()
        for job in Handler.jobs.values():
            job.cancel()
