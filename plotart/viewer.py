"""Share a sketch as ONE self-contained web page (seed navigation, sliders, PNG/SVG download).

The page follows the layout of the "algorithmic-art" skill viewer (Apache-2.0):
sidebar with Seed → Parameter → Farben → Aktionen, the artwork on the right.
Python runs in the visitor's browser via Pyodide (loaded from a CDN, so the page
needs internet once); plotart and the sketch are embedded in the file.

    python -m plotart sketch meine.py --html      → meine_1.html
    Studio: Export › „Als Web-Seite“
"""
from __future__ import annotations

import ast
import html
import json
from pathlib import Path

PKG = Path(__file__).resolve().parent
PYODIDE_URL = "https://cdn.jsdelivr.net/npm/pyodide@0.26.4/full/"
_SKIP_DIRS = {"blender", "touchdesigner", "examples", "static", "__pycache__"}
_SKIP_FILES = {"web.py", "cli.py", "__main__.py", "viewer.py", "worker.py", "sketchfiles.py"}


def package_files() -> dict[str, str]:
    """plotart's Python sources needed to run sketches in the browser."""
    out = {}
    for p in sorted(PKG.rglob("*.py")):
        rel = p.relative_to(PKG)
        if _SKIP_DIRS & set(rel.parts[:-1]) or p.name in _SKIP_FILES:
            continue
        out["plotart/" + rel.as_posix()] = p.read_text(encoding="utf-8")
    return out


def sketch_doc(source: str) -> tuple[str, str]:
    """(title, text) from the sketch's docstring: first line = title, rest = description/philosophy."""
    try:
        doc = ast.get_docstring(ast.parse(source)) or ""
    except SyntaxError:
        doc = ""
    lines = doc.strip().splitlines()
    if not lines:
        return "Generative Skizze", ""
    return lines[0].strip(), "\n".join(lines[1:]).strip()


def _js(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def build_viewer(source: str, seed: int = 1, params: dict | None = None, title: str | None = None,
                 description: str | None = None, pyodide_url: str = PYODIDE_URL) -> str:
    """→ HTML text of the stand-alone viewer."""
    t, d = sketch_doc(source)
    title = title or t
    description = d if description is None else description
    params = {k: v for k, v in (params or {}).items() if not k.startswith("__")}
    paras = "".join(f"<p>{html.escape(p)}</p>" for p in description.split("\n\n") if p.strip())
    page = TEMPLATE
    for key, val in {
        "%%TITLE%%": html.escape(title),
        "%%DESCRIPTION%%": paras or '<p>Jeder Seed ergibt ein anderes Bild – derselbe Seed immer dasselbe.</p>',
        "%%SOURCE%%": _js(source),
        "%%SEED%%": _js(int(seed)),
        "%%PARAMS%%": _js(params),
        "%%FILES%%": _js(package_files()),
        "%%PYODIDE%%": _js(pyodide_url),
    }.items():
        page = page.replace(key, val)
    return page


TEMPLATE = r"""<!DOCTYPE html>
<!-- Erzeugt mit plotart. Layout nach der Viewer-Vorlage des „algorithmic-art“-Skills (Apache-2.0). -->
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%%TITLE%%</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&family=Lora:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root { --dark: #141413; --light: #faf9f5; --mid-gray: #b0aea5; --light-gray: #e8e6dc;
          --orange: #d97757; --blue: #6a9bcc; --green: #788c5d; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Poppins', sans-serif; background: linear-gradient(135deg, var(--light) 0%, #f5f3ee 100%);
         min-height: 100vh; color: var(--dark); }
  .container { display: flex; min-height: 100vh; padding: 20px; gap: 20px; }
  .sidebar { width: 320px; flex-shrink: 0; background: rgba(255,255,255,.95); backdrop-filter: blur(10px);
             padding: 24px; border-radius: 12px; box-shadow: 0 10px 30px rgba(20,20,19,.1);
             overflow-y: auto; overflow-x: hidden; max-height: calc(100vh - 40px); position: sticky; top: 20px; }
  .sidebar h1 { font-family: 'Lora', serif; font-size: 24px; font-weight: 500; margin-bottom: 8px; }
  .subtitle { color: #77756c; font-size: 13px; margin-bottom: 28px; line-height: 1.5; font-family: 'Lora', serif; }
  .subtitle p + p { margin-top: 8px; }
  .control-section { margin-bottom: 28px; }
  .control-section h3 { font-size: 16px; font-weight: 600; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }
  .control-section h3::before { content: '•'; color: var(--orange); font-weight: bold; }
  .seed-input { width: 100%; background: var(--light); padding: 12px; border-radius: 8px; font-family: 'Courier New', monospace;
                font-size: 14px; margin-bottom: 12px; border: 1px solid var(--light-gray); text-align: center; }
  .seed-input:focus { outline: none; border-color: var(--orange); box-shadow: 0 0 0 2px rgba(217,119,87,.1); background: #fff; }
  .seed-controls { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 8px; }
  .control-group { margin-bottom: 18px; }
  .control-group label { display: block; font-size: 14px; font-weight: 500; margin-bottom: 8px; }
  .slider-container { display: flex; align-items: center; gap: 12px; }
  .slider-container input[type="range"] { flex: 1; height: 4px; background: var(--light-gray); border-radius: 2px;
                                           outline: none; -webkit-appearance: none; }
  .slider-container input[type="range"]::-webkit-slider-thumb { -webkit-appearance: none; width: 16px; height: 16px;
      background: var(--orange); border-radius: 50%; cursor: pointer; }
  .slider-container input[type="range"]::-moz-range-thumb { width: 16px; height: 16px; background: var(--orange);
      border-radius: 50%; border: none; cursor: pointer; }
  .value-display { font-family: 'Courier New', monospace; font-size: 12px; color: var(--mid-gray); min-width: 60px; text-align: right; }
  .control-group select, .control-group input[type="text"] { width: 100%; padding: 8px; border-radius: 6px;
      border: 1px solid var(--light-gray); background: var(--light); font: inherit; font-size: 14px; }
  .color-group { margin-bottom: 14px; }
  .color-group label { display: block; font-size: 12px; color: var(--mid-gray); margin-bottom: 4px; }
  .color-picker-container { display: flex; align-items: center; gap: 8px; }
  .color-picker-container input[type="color"] { width: 32px; height: 32px; border: none; border-radius: 6px; cursor: pointer; background: none; padding: 0; }
  .color-value { font-family: 'Courier New', monospace; font-size: 12px; color: var(--mid-gray); }
  .button { background: var(--orange); color: #fff; border: none; padding: 10px 16px; border-radius: 6px; font-size: 14px;
            font-weight: 500; cursor: pointer; transition: all .2s ease; width: 100%; font-family: inherit; }
  .button:hover { background: #c86641; transform: translateY(-1px); }
  .button.secondary { background: var(--blue); } .button.secondary:hover { background: #5a8bb8; }
  .button.tertiary { background: var(--green); } .button.tertiary:hover { background: #6b7b52; }
  .button-row { display: flex; gap: 8px; margin-bottom: 8px; } .button-row .button { flex: 1; }
  .canvas-area { flex: 1; display: flex; align-items: center; justify-content: center; min-width: 0; flex-direction: column; gap: 12px; }
  #canvas-container { width: 100%; max-width: 1000px; border-radius: 12px; overflow: hidden;
                      box-shadow: 0 20px 40px rgba(20,20,19,.1); background: #fff; position: relative; }
  #canvas-container svg, #canvas-container canvas { display: block; width: 100% !important; height: auto !important; }
  .loading { display: flex; align-items: center; justify-content: center; font-size: 16px; color: var(--mid-gray);
             min-height: 420px; padding: 24px; text-align: center; }
  .busy { position: absolute; right: 12px; top: 12px; background: rgba(255,255,255,.9); border-radius: 6px; padding: 4px 10px;
          font-size: 12px; color: var(--mid-gray); display: none; } .busy.on { display: block; }
  .note { font-size: 12px; color: var(--mid-gray); }
  .err { color: #b3261e; font-size: 13px; white-space: pre-wrap; font-family: 'Courier New', monospace; }
  @media (max-width: 700px) { .container { flex-direction: column; } .sidebar { width: 100%; position: static; max-height: none; } }
</style>
</head>
<body>
<div class="container">
  <div class="sidebar">
    <h1>%%TITLE%%</h1>
    <div class="subtitle">%%DESCRIPTION%%</div>

    <div class="control-section">
      <h3>Seed</h3>
      <input type="number" id="seed-input" class="seed-input" min="1" onchange="updateSeed()">
      <div class="seed-controls">
        <button class="button secondary" onclick="previousSeed()">← Zurück</button>
        <button class="button secondary" onclick="nextSeed()">Weiter →</button>
      </div>
      <button class="button tertiary" onclick="randomSeedAndUpdate()">↻ Zufällig</button>
    </div>

    <div class="control-section" id="param-section" hidden>
      <h3>Parameter</h3>
      <div id="params"></div>
    </div>

    <div class="control-section" id="color-section" hidden>
      <h3>Farben</h3>
      <div id="colors"></div>
    </div>

    <div class="control-section">
      <h3>Aktionen</h3>
      <div class="button-row">
        <button class="button" onclick="regenerate()">Neu erzeugen</button>
        <button class="button" onclick="resetParameters()">Zurücksetzen</button>
      </div>
      <div class="button-row">
        <button class="button secondary" onclick="downloadPNG()">PNG laden</button>
        <button class="button secondary" onclick="downloadSVG()">SVG laden</button>
      </div>
    </div>
    <p class="note">Gerechnet mit Python im Browser (Pyodide) · erstellt mit plotart</p>
  </div>

  <div class="canvas-area">
    <div id="canvas-container">
      <div class="loading" id="loading">Python wird geladen …</div>
      <div class="busy" id="busy">rechnet …</div>
    </div>
    <div class="err" id="error"></div>
  </div>
</div>

<script>
const SOURCE = %%SOURCE%%;
const FILES = %%FILES%%;
const PYODIDE_URL = %%PYODIDE%%;
const START = { seed: %%SEED%%, params: %%PARAMS%% };
let state = { seed: START.seed, params: { ...START.params }, specs: [], svg: null, animated: false };

// ---------------------------------------------------------------- Python in a worker (UI stays responsive)
const WORKER = `
let py = null;
self.onmessage = async (e) => {
  const { id, cmd, arg } = e.data;
  try {
    if (cmd === "init") {
      importScripts(arg.url + "pyodide.js");
      py = await loadPyodide({ indexURL: arg.url });
      for (const [path, src] of Object.entries(arg.files)) {
        const full = "/home/pyodide/" + path;
        py.FS.mkdirTree(full.substring(0, full.lastIndexOf("/")));
        py.FS.writeFile(full, src);
      }
      await py.loadPackagesFromImports(arg.source);
      if (/load_image|create_image|snapshot\\(|apply_shader|filter\\(|load_svg|draw_svg|text_shape/.test(arg.source)) await py.loadPackage("pillow");
      if (/shape_union|shape_difference|shape_intersection|offset_shape|draw_geometry/.test(arg.source)) await py.loadPackage("shapely");
      if (/reaction_diffusion\\(|mandelbrot\\(|julia\\(|newton_fractal\\(|domain_coloring\\(|density\\(|colorize\\(/.test(arg.source)) await py.loadPackage("numpy");
      py.runPython("import sys; sys.path.insert(0, '/home/pyodide'); from plotart import bridge");
      self.postMessage({ id, result: true });
    } else {
      py.globals.set("_cmd", cmd); py.globals.set("_arg", arg);
      self.postMessage({ id, result: py.runPython("bridge.call_json(_cmd, _arg)") });
    }
  } catch (err) { self.postMessage({ id, error: String((err && err.message) || err) }); }
};`;
const worker = new Worker(URL.createObjectURL(new Blob([WORKER], { type: "text/javascript" })));
const pending = new Map(); let nextId = 1;
worker.onmessage = (e) => { const p = pending.get(e.data.id); pending.delete(e.data.id);
  if (p) e.data.error ? p.reject(new Error(e.data.error)) : p.resolve(e.data.result); };
function send(cmd, arg) { return new Promise((resolve, reject) => { const id = nextId++; pending.set(id, { resolve, reject }); worker.postMessage({ id, cmd, arg }); }); }
async function call(cmd, body) { await ready; const out = JSON.parse(await send(cmd, JSON.stringify(body))); if (out.error) throw new Error(out.error); return out; }
const ready = send("init", { url: PYODIDE_URL, files: FILES, source: SOURCE });

// ---------------------------------------------------------------- rendering
const box = document.getElementById("canvas-container");
let gen = 0, renderBusy = false, renderAgain = false;
function payload() { return { source: SOURCE, params: state.params, seed: state.seed }; }
function setBusy(on) { document.getElementById("busy").classList.toggle("on", on); }
function showError(e) { document.getElementById("error").textContent = e ? (e.line ? "Zeile " + e.line + ": " : "") + (e.message || e) : ""; }

async function initializeSystem() {
  if (renderBusy) { renderAgain = true; return; }
  renderBusy = true; setBusy(true);
  const my = ++gen;
  try {
    const r = await call("sketch_run", payload());
    document.getElementById("loading")?.remove();
    showError(r.sketch_error);
    if (r.sketch_error) return;
    if (!state.specs.length) buildControls(r.params);
    state.animated = r.animated;
    if (r.animated) startAnimation(my, r); else { stopCanvas(); setSvg(r.svg); }
  } catch (e) { showError(e); }
  finally { renderBusy = false; setBusy(false); if (renderAgain) { renderAgain = false; initializeSystem(); } }
}
function setSvg(svg) {
  state.svg = svg;
  let holder = document.getElementById("art");
  if (!holder) { holder = document.createElement("div"); holder.id = "art"; box.prepend(holder); }
  holder.innerHTML = svg.replace(/^<\?xml[^>]*>\s*/, "");
}

// animation: frames arrive as SVG and are composited (translucent backgrounds → trails, as in p5)
let canvas = null, ctx = null, frames = [], cur = -1, total = 1, fps = 30, lastT = 0;
function stopCanvas() { frames = []; cur = -1; if (canvas) { canvas.remove(); canvas = null; } }
function decode(svg) { return new Promise((res, rej) => { const u = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
  const i = new Image(); i.onload = () => { URL.revokeObjectURL(u); res(i); }; i.onerror = rej; i.src = u; }); }
async function startAnimation(my, r) {
  document.getElementById("art")?.remove();
  stopCanvas();
  canvas = document.createElement("canvas"); box.prepend(canvas); ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1, w = Math.min(1000, box.clientWidth || 800);
  canvas.width = Math.round(w * dpr); canvas.height = Math.round(w * r.height / r.width * dpr);
  total = r.frames; fps = r.fps; frames = [];
  let next = 0;
  while (my === gen && next < total) {
    const f = await call("anim_frames", { ...payload(), start: next, count: 8, budget_ms: 250 });
    if (my !== gen) return;
    if (f.sketch_error) { showError(f.sketch_error); return; }
    for (const fr of f.frames) frames.push(await decode(fr.svg).then(img => ({ img, clears: fr.clears })));
    next = f.next;
    if (f.done) break;
  }
}
async function tick(t) {
  requestAnimationFrame(tick);
  if (!canvas || !frames.length || t - lastT < 1000 / fps) return;
  lastT = t;
  let n = cur + 1;
  if (n >= total) n = 0;
  if (n >= frames.length) return;
  if (n === 0 || frames[n].clears) ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(frames[n].img, 0, 0, canvas.width, canvas.height);
  cur = n;
}
requestAnimationFrame(tick);

// ---------------------------------------------------------------- controls (built from the sketch's param() calls)
function fmt(p, v) { return p.kind === "float" ? Number(v).toFixed(Math.max(0, Math.min(4, Math.ceil(-Math.log10(p.step || 0.01))))) : v; }
function buildControls(specs) {
  state.specs = specs;
  const pBox = document.getElementById("params"), cBox = document.getElementById("colors");
  pBox.innerHTML = ""; cBox.innerHTML = "";
  for (const p of specs) {
    const value = p.name in state.params ? state.params[p.name] : p.default;
    const id = "p_" + specs.indexOf(p);
    if (p.kind === "color") {
      const g = document.createElement("div"); g.className = "color-group";
      g.innerHTML = `<label></label><div class="color-picker-container"><input type="color" id="${id}"><span class="color-value"></span></div>`;
      g.querySelector("label").textContent = p.label;
      const inp = g.querySelector("input"), val = g.querySelector(".color-value");
      inp.value = value; val.textContent = value;
      inp.onchange = () => { val.textContent = inp.value; updateParam(p.name, inp.value); };
      cBox.appendChild(g); continue;
    }
    const g = document.createElement("div"); g.className = "control-group";
    const label = document.createElement("label"); label.textContent = p.label; g.appendChild(label);
    if (p.kind === "int" || p.kind === "float") {
      const c = document.createElement("div"); c.className = "slider-container";
      c.innerHTML = `<input type="range" id="${id}"><span class="value-display"></span>`;
      const inp = c.querySelector("input"), val = c.querySelector(".value-display");
      Object.assign(inp, { min: p.min, max: p.max, step: p.step || (p.kind === "int" ? 1 : 0.01), value });
      val.textContent = fmt(p, value);
      inp.oninput = () => { const x = p.kind === "int" ? parseInt(inp.value) : parseFloat(inp.value); val.textContent = fmt(p, x); updateParam(p.name, x); };
      g.appendChild(c);
    } else if (p.kind === "choice") {
      const sel = document.createElement("select"); sel.id = id;
      for (const [v, l] of p.choices) sel.add(new Option(l, v));
      sel.value = value; sel.onchange = () => updateParam(p.name, sel.value); g.appendChild(sel);
    } else if (p.kind === "bool") {
      const cb = document.createElement("input"); cb.type = "checkbox"; cb.id = id; cb.checked = !!value;
      cb.style.marginRight = "8px"; label.prepend(cb); cb.onchange = () => updateParam(p.name, cb.checked);
    } else {
      const t = document.createElement("input"); t.type = "text"; t.id = id; t.value = value;
      t.onchange = () => updateParam(p.name, t.value); g.appendChild(t);
    }
    pBox.appendChild(g);
  }
  document.getElementById("param-section").hidden = !pBox.children.length;
  document.getElementById("color-section").hidden = !cBox.children.length;
}
let paramTimer = null;
function updateParam(name, value) { state.params[name] = value; clearTimeout(paramTimer); paramTimer = setTimeout(initializeSystem, 120); }

// ---------------------------------------------------------------- seed (as in the skill's viewer)
function updateSeedDisplay() { document.getElementById("seed-input").value = state.seed; }
function updateSeed() { const v = parseInt(document.getElementById("seed-input").value);
  if (v && v > 0) { state.seed = v; initializeSystem(); } else updateSeedDisplay(); }
function previousSeed() { state.seed = Math.max(1, state.seed - 1); updateSeedDisplay(); initializeSystem(); }
function nextSeed() { state.seed = state.seed + 1; updateSeedDisplay(); initializeSystem(); }
function randomSeedAndUpdate() { state.seed = Math.floor(Math.random() * 999999) + 1; updateSeedDisplay(); initializeSystem(); }
function regenerate() { initializeSystem(); }
function resetParameters() { state.params = { ...START.params }; state.seed = START.seed; state.specs = []; updateSeedDisplay(); initializeSystem(); }

// ---------------------------------------------------------------- downloads
function stem() { return (document.title || "skizze").toLowerCase()
  .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss").replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "").slice(0, 40) + "_" + state.seed; }
function save(blob, name) { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name;
  document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 5000); }
async function downloadPNG() {
  if (canvas) { canvas.toBlob(b => save(b, stem() + ".png")); return; }
  if (!state.svg) return;
  const img = await decode(state.svg);
  const c = document.createElement("canvas"), k = 2400 / Math.max(img.width, img.height);
  c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
  c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
  c.toBlob(b => save(b, stem() + ".png"));
}
function downloadSVG() { if (state.svg) save(new Blob([state.svg], { type: "image/svg+xml" }), stem() + ".svg"); }

window.addEventListener("load", () => { updateSeedDisplay(); initializeSystem(); });
</script>
</body>
</html>
"""
