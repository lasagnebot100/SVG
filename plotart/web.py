"""Local web UI: the Studio (live-coding sketches) and the generator page (standard library only)."""
from __future__ import annotations

import hmac
import json
import os
import secrets
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import bridge
from .sketch.worker import SketchWorker

STATIC = Path(__file__).parent / "static"
OUTPUT_DIR = Path(os.environ.get("PLOTART_OUTPUT", "output"))

PAGES = {"/": "studio.html", "/index.html": "studio.html", "/studio": "studio.html",
         "/generatoren": "generators.html", "/generatoren.html": "generators.html"}
FILES = {"/vendor/codemirror.js": ("vendor/codemirror.js", "text/javascript; charset=utf-8"),
         "/vendor/codemirror.css": ("vendor/codemirror.css", "text/css; charset=utf-8")}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


class Handler(BaseHTTPRequestHandler):
    server_version = "plotart"
    worker: SketchWorker = None
    token: str | None = None          # required when the server is reachable from the network

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

    def do_GET(self):
        path = urlparse(self.path).path
        if path in PAGES:
            self._send((STATIC / PAGES[path]).read_bytes(), "text/html; charset=utf-8")
        elif path in FILES:
            rel, ctype = FILES[path]
            self._send((STATIC / rel).read_bytes(), ctype, cache=True)
        elif path == "/backend.js":     # only used by the standalone web app
            self._send(b"", "text/javascript")
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
          timeout: float = 30.0):
    Handler.worker = SketchWorker(timeout=timeout)
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
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        Handler.worker.close()
