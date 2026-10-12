"""Build the standalone web app (no server needed – Python runs in the browser via Pyodide).

    python3 tools/build_web.py                 # → site/index.html (+ manifest, icons)
    python3 tools/build_web.py --out public --pyodide-url https://…/pyodide/v0.26.4/full/

The result is a static folder that can be hosted anywhere (GitHub Pages, Netlify, …)
and opened on iPad, phone or desktop.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "plotart"
DEFAULT_PYODIDE = "https://cdn.jsdelivr.net/npm/pyodide@0.26.4/"

WORKER_JS = r"""
let py = null;
self.onmessage = async (e) => {
  const { id, cmd, arg } = e.data;
  try {
    if (cmd === "init") {
      self.postMessage({ progress: "Python wird geladen …" });
      importScripts(arg.url + "pyodide.js");
      py = await loadPyodide({ indexURL: arg.url });
      self.postMessage({ progress: "plotart wird eingerichtet …" });
      for (const [path, src] of Object.entries(arg.files)) {
        const full = "/home/pyodide/" + path;
        py.FS.mkdirTree(full.substring(0, full.lastIndexOf("/")));
        py.FS.writeFile(full, src);
      }
      py.runPython("import sys; sys.path.insert(0, '/home/pyodide'); from plotart import bridge");
      self.postMessage({ id, result: true });
    } else {
      py.globals.set("_cmd", arg.cmd);
      py.globals.set("_arg", arg.body);
      self.postMessage({ id, result: py.runPython("bridge.call_json(_cmd, _arg)") });
    }
  } catch (err) {
    self.postMessage({ id, error: String((err && err.message) || err) });
  }
};
"""

BACKEND_JS = r"""
window.PLOTART_BACKEND = (() => {
  const be = { standalone: true, onProgress: null };
  const worker = new Worker(URL.createObjectURL(new Blob([WORKER_SRC], { type: "text/javascript" })));
  const pending = new Map();
  let nextId = 1;
  worker.onmessage = (e) => {
    const m = e.data;
    if (m.progress) { if (be.onProgress) be.onProgress(m.progress); return; }
    const p = pending.get(m.id);
    pending.delete(m.id);
    if (p) m.error ? p.reject(new Error(m.error)) : p.resolve(m.result);
  };
  worker.onerror = (e) => {
    const msg = e.message || "Worker-Fehler";
    for (const p of pending.values()) p.reject(new Error(msg));
    pending.clear();
    if (be.onProgress) be.onProgress("Fehler: " + msg);
  };
  const send = (cmd, arg) => new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, cmd, arg });
  });
  // absolute URL: relative paths would resolve against the worker's blob: URL
  const ready = send("init", { url: new URL(PYODIDE_URL, location.href).href, files: FILES });

  async function raw(cmd, body) {
    await ready;
    const out = JSON.parse(await send("call", { cmd, body: JSON.stringify(body) }));
    if (out.error) throw new Error(out.error);
    return out;
  }
  // while a render is running keep only the newest request (sliders fire many)
  let busy = false, queued = null;
  async function render(body) {
    if (busy) {
      if (queued) queued.reject(new Error("veraltet"));
      return new Promise((resolve, reject) => { queued = { body, resolve, reject }; });
    }
    busy = true;
    try { return await raw("render", body); }
    finally {
      busy = false;
      if (queued) { const q = queued; queued = null; render(q.body).then(q.resolve, q.reject); }
    }
  }
  be.schema = () => raw("schema", {});
  be.call = (cmd, body) => cmd === "render" ? render(body) : raw(cmd, body);
  return be;
})();
"""


def python_files() -> dict[str, str]:
    files = {}
    for path in sorted(PKG.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        files[path.relative_to(ROOT).as_posix()] = path.read_text(encoding="utf-8")
    return files


def script_json(obj) -> str:
    """JSON that is safe inside a <script> element."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def make_icons(out: Path) -> list[str]:
    """Render app icons from the pixel-grid generator (needs Pillow; skipped otherwise)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return []
    import sys
    sys.path.insert(0, str(ROOT))
    from plotart import render

    d = render("blocks", {"cols": 12, "profile": "center", "profile_mix": 0.7}, seed=7,
               settings={"paper": "Quadrat 30", "margin": 40, "pen_width": 1.2})
    names = []
    for size, name in ((512, "icon-512.png"), (180, "apple-touch-icon.png")):
        s = size / d.width
        img = Image.new("RGB", (size, size), "#fbfaf7")
        draw = ImageDraw.Draw(img)
        for p in d.all_paths():
            draw.line([(x * s, y * s) for x, y in p], fill="#1f5fbf",
                      width=max(1, round(d.pen_width * s)))
        img.save(out / name)
        names.append(name)
    return names


def build(out: Path, pyodide_url: str) -> Path:
    if not pyodide_url.endswith("/"):
        pyodide_url += "/"
    out.mkdir(parents=True, exist_ok=True)
    html = (PKG / "static" / "index.html").read_text(encoding="utf-8")

    icons = make_icons(out)
    head = ['<link rel="manifest" href="manifest.webmanifest">']
    if icons:
        head.append('<link rel="apple-touch-icon" href="apple-touch-icon.png">')
        head.append('<link rel="icon" href="icon-512.png">')
    manifest = {
        "name": "plotart – generative Plotter-Kunst",
        "short_name": "plotart",
        "start_url": ".",
        "display": "standalone",
        "background_color": "#ecebe7",
        "theme_color": "#ecebe7",
        "icons": [{"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}] if icons else [],
    }
    (out / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                              encoding="utf-8")

    inject = (
        "<script>\n"
        f"const PYODIDE_URL = {script_json(pyodide_url)};\n"
        f"const FILES = {script_json(python_files())};\n"
        f"const WORKER_SRC = {script_json(WORKER_JS)};\n"
        f"{BACKEND_JS}"
        "</script>\n"
    )
    marker = "<script>\nconst $ ="
    if marker not in html or "</head>" not in html:
        raise SystemExit("index.html hat nicht die erwartete Struktur")
    html = html.replace("</head>", "\n".join(head) + "\n</head>", 1)
    html = html.replace(marker, inject + marker, 1)
    target = out / "index.html"
    target.write_text(html, encoding="utf-8")
    return target


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "site"), help="Ausgabeordner (Standard: site/)")
    ap.add_argument("--pyodide-url", default=DEFAULT_PYODIDE, help="Basis-URL der Pyodide-Dateien")
    args = ap.parse_args()
    target = build(Path(args.out), args.pyodide_url)
    print(f"✓ {target} ({target.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
