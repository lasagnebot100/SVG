"""Small local web UI with live preview (standard library only)."""
from __future__ import annotations

import json
import os
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .api import GLOBAL_PARAMS, new_seed, random_params, render
from .generators import REGISTRY
from .svg import to_svg

STATIC = Path(__file__).parent / "static"
OUTPUT_DIR = Path(os.environ.get("PLOTART_OUTPUT", "output"))


class Handler(BaseHTTPRequestHandler):
    server_version = "plotart"

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    def _send(self, body: bytes, ctype: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status: int = 200):
        self._send(json.dumps(obj, ensure_ascii=False).encode(), "application/json", status)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send((STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/generators":
            self._json({
                "generators": [g.to_json() for g in REGISTRY.values()],
                "settings": [p.to_json() for p in GLOBAL_PARAMS],
                "output_dir": str(OUTPUT_DIR.resolve()),
            })
        else:
            self._send(b"not found", "text/plain", 404)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/random":
                name = req["generator"]
                self._json({"params": random_params(name, new_seed()), "seed": new_seed()})
                return
            if self.path not in ("/api/render", "/api/save"):
                self._send(b"not found", "text/plain", 404)
                return
            d = render(req["generator"], req.get("params"), req.get("seed"), req.get("settings"))
            svg = to_svg(d)
            if self.path == "/api/save":
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                path = OUTPUT_DIR / f"{d.meta['generator']}_{d.meta['seed']}.svg"
                path.write_text(svg, encoding="utf-8")
                self._json({"path": str(path.resolve())})
            else:
                self._json({"svg": svg, "stats": d.stats(), "seed": d.meta["seed"]})
        except Exception as exc:  # report errors to the UI instead of crashing
            traceback.print_exc()
            self._json({"error": str(exc)}, 500)


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True):
    httpd = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{'localhost' if host in ('127.0.0.1', '0.0.0.0') else host}:{port}/"
    print(f"plotart läuft auf {url}  (Beenden mit Strg+C)")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
