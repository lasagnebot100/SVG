"""Processing (.pde) in plotart: run sketches with an installed Processing and convert simple ones to plotart.

Running uses the command line of Processing 4 (``Processing cli --run``, older versions ``processing-java``).
A small helper class is appended to the sketch: it sets the seed, saves every frame as PNG for the Studio
and ends the sketch after the wanted number of frames – or on an error, instead of leaving a window open.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SKETCH_NAME = "plotart_skizze"
MAX_FRAMES = 600


class ProcessingError(RuntimeError):
    pass


# ---------------------------------------------------------------------------- finding Processing
def find_processing() -> tuple[str, str] | None:
    """(executable, kind) with kind "cli" (Processing 4.4+) or "java" (processing-java), or None."""
    env = os.environ.get("PLOTART_PROCESSING")
    candidates = [env] if env else []
    for name in ("processing-java", "Processing", "processing"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    if sys.platform == "win32":
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("LOCALAPPDATA", "")):
            if base:
                candidates += [os.path.join(base, "Processing", "Processing.exe"),
                               os.path.join(base, "Programs", "Processing", "Processing.exe"),
                               os.path.join(base, "Processing", "processing-java.exe")]
    elif sys.platform == "darwin":
        candidates += ["/Applications/Processing.app/Contents/MacOS/Processing", "/usr/local/bin/processing-java"]
    else:
        candidates += ["/usr/bin/processing-java", "/opt/processing/bin/Processing",
                       os.path.expanduser("~/processing/processing-java")]
    for c in candidates:
        if c and os.path.isfile(c):
            return c, "java" if "processing-java" in os.path.basename(c).lower() else "cli"
    return None


# ---------------------------------------------------------------------------- running
_CAPTURE = """
// --- plotart: Seed, Bilder fürs Studio, Ende nach N Bildern (automatisch angehängt) ---
PlotartCapture plotartCapture = new PlotartCapture(this);
public class PlotartCapture {
  PApplet app; String dir; int frames;
  PlotartCapture(PApplet app) {
    this.app = app;
    dir = System.getenv("PLOTART_OUT");
    String n = System.getenv("PLOTART_FRAMES");
    frames = n == null ? 1 : Integer.parseInt(n);
    String s = System.getenv("PLOTART_SEED");
    if (s != null) { app.randomSeed(Long.parseLong(s)); app.noiseSeed(Long.parseLong(s)); }
    if (dir != null) app.registerMethod("post", this);
  }
  public void post() {
    app.saveFrame(dir + "/frame-#####.png");
    if (app.frameCount >= frames || !app.isLooping()) app.exit();
  }
}
"""

_ACTIVE = re.compile(r"\bvoid\s+(setup|draw|settings)\s*\(")


def prepare_sketch(source: str, folder: str | Path) -> int:
    """Write folder/plotart_skizze.pde. Static sketches (no setup/draw) are wrapped in setup().
    → number of lines added in front of the user's code (for error line numbers)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    offset = 0
    code = source.rstrip() + "\n"
    if not _ACTIVE.search(source):
        code = "void setup() {\n" + code + "}\n"
        offset = 1
    (folder / f"{SKETCH_NAME}.pde").write_text(code + _CAPTURE, encoding="utf-8")
    return offset


def has_draw(source: str) -> bool:
    return re.search(r"\bvoid\s+draw\s*\(", source) is not None


def _command(exe: str, kind: str, sketch: Path, build: Path) -> list[str]:
    if kind == "java":
        return [exe, f"--sketch={sketch}", f"--output={build}", "--force", "--run"]
    return [exe, "cli", f"--sketch={sketch}", f"--output={build}", "--force", "--run"]


# Processing reports compile AND runtime errors as "<sketch>.pde:line:col:line:col: message"
_COMPILE_ERR = re.compile(rf"{SKETCH_NAME}\.pde:(\d+):\d+:\d+:\d+:\s*(.*)")


def run_pde(source: str, frames: int | None = None, seed: int = 1, timeout: float = 120.0,
            workdir: str | Path | None = None) -> dict:
    """Run a .pde sketch → {"frames": [png bytes …], "width", "height", "log", "error": {message, line} or None}."""
    found = find_processing()
    if found is None:
        raise ProcessingError("Processing wurde nicht gefunden. Installieren von https://processing.org/download "
                              "oder den Pfad in der Umgebungsvariable PLOTART_PROCESSING angeben.")
    exe, kind = found
    frames = max(1, min(MAX_FRAMES, int(frames or (120 if has_draw(source) else 1))))
    tmp = tempfile.mkdtemp(prefix="plotart_pde_", dir=workdir)
    try:
        root = Path(tmp)
        sketch, build, out = root / SKETCH_NAME, root / "build", root / "bilder"
        out.mkdir()
        offset = prepare_sketch(source, sketch)
        env = {**os.environ, "PLOTART_OUT": str(out), "PLOTART_FRAMES": str(frames), "PLOTART_SEED": str(int(seed))}
        t0 = time.perf_counter()
        log, timed_out = _watch(_command(exe, kind, sketch, build), env, timeout)
        if timed_out:
            return {"frames": [], "log": _clean(log), "ms": round((time.perf_counter() - t0) * 1000),
                    "error": {"message": f"Abgebrochen: Der Sketch lief länger als {timeout:g} s.", "line": None}}
        error = None
        m = _COMPILE_ERR.search(log)
        if m:
            line = int(m.group(1)) - offset
            error = {"message": m.group(2).strip(), "line": line if 0 < line <= source.count("\n") + 1 else None}
        elif (m := _EXCEPTION.search(log)) is not None:
            error = {"message": m.group(1).strip(), "line": None}
        pngs = [p.read_bytes() for p in sorted(out.glob("frame-*.png"))]
        if not pngs and error is None:
            error = {"message": "Der Sketch hat kein Bild erzeugt.", "line": None}
        width = height = None
        if pngs:
            width, height = _png_size(pngs[0])
        return {"frames": pngs, "width": width, "height": height, "log": _clean(log), "error": error,
                "ms": round((time.perf_counter() - t0) * 1000)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


_EXCEPTION = re.compile(r"^(?:Exception in thread \"[^\"]*\" )?((?:[\w$]+\.)+[\w$]*(?:Exception|Error)\b.*)$", re.M)


def _kill_tree(proc: subprocess.Popen):
    """End Processing and the sketch's own Java process (a plain kill would leave the sketch window open)."""
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        import signal
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
    proc.wait(10)


def _watch(cmd: list[str], env: dict, timeout: float) -> tuple[str, bool]:
    """Run Processing, read its output while it runs; stop at once when the sketch throws an exception
    (Processing would print it and keep the window open). → (log, timed_out)."""
    import threading
    kwargs = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else \
        {"start_new_session": True}
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
    chunks: list[str] = []

    def read():
        for raw in iter(proc.stdout.readline, b""):
            chunks.append(raw.decode("utf-8", errors="replace"))
    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    deadline, failed_at = time.monotonic() + timeout, None
    while proc.poll() is None:
        now = time.monotonic()
        text = "".join(chunks)
        if failed_at is None and (_COMPILE_ERR.search(text) or _EXCEPTION.search(text)):
            failed_at = now                                   # let the rest of the message arrive, then stop
        if (failed_at is not None and now - failed_at > 0.8) or now > deadline:
            _kill_tree(proc)
            break
        time.sleep(0.1)
    reader.join(2)
    return "".join(chunks), failed_at is None and time.monotonic() > deadline


def _clean(log: str) -> str:
    """Drop Processing's own chatter, keep the sketch's println() output and errors."""
    skip = ("WARNING: package sun.awt", "Finished.", "Listening for transport")
    return "\n".join(l for l in log.splitlines() if l.strip() and not l.startswith(skip))[-20000:]


def _png_size(data: bytes) -> tuple[int, int]:
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


EXAMPLES_DIR = Path(__file__).resolve().parent / "examples"


def list_pde_examples() -> list[dict]:
    """The bundled Processing examples: {"name", "title", "source"}; title = first comment line."""
    out = []
    for path in sorted(EXAMPLES_DIR.glob("*.pde")):
        src = path.read_text(encoding="utf-8")
        first = src.lstrip().splitlines()[0] if src.strip() else ""
        title = first[2:].strip() if first.startswith("//") else path.stem
        out.append({"name": path.stem, "title": title, "source": src})
    return out


def frames_as_svg(pngs: list[bytes]) -> list[str]:
    """PNG frames wrapped in SVG – the Studio's player shows them like the frames of a plotart sketch."""
    import base64
    out = []
    for data in pngs:
        w, h = _png_size(data)
        out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
                   f'<image width="{w}" height="{h}" href="data:image/png;base64,'
                   f'{base64.b64encode(data).decode()}"/></svg>')
    return out
