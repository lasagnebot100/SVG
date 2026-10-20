"""R in plotart: run R scripts (base graphics, ggplot2, aRtsy …) with an installed R via Rscript.

A small prelude sets the seed, opens a PNG device and defines plotart_param() / plotart_canvas().
The script is evaluated expression by expression: visible values are printed (so ggplot objects are
drawn), errors come back with the line of the statement. Every page of the device becomes a frame.
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DEFAULT_SIZE = (800, 800)


class RError(RuntimeError):
    pass


def find_rscript() -> str | None:
    """Path of Rscript: PLOTART_RSCRIPT, PATH, then the usual install folders (newest version first)."""
    env = os.environ.get("PLOTART_RSCRIPT")
    if env and os.path.isfile(env):
        return env
    found = shutil.which("Rscript")
    if found:
        return found
    candidates: list[str] = []
    if sys.platform == "win32":
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("LOCALAPPDATA", "")):
            if base:
                candidates += glob.glob(os.path.join(base, "R", "R-*", "bin", "Rscript.exe"))
                candidates += glob.glob(os.path.join(base, "Programs", "R", "R-*", "bin", "Rscript.exe"))
        candidates.sort(key=_version_key, reverse=True)
    elif sys.platform == "darwin":
        candidates = ["/Library/Frameworks/R.framework/Resources/bin/Rscript", "/opt/homebrew/bin/Rscript",
                      "/usr/local/bin/Rscript"]
    else:
        candidates = ["/usr/bin/Rscript", "/usr/local/bin/Rscript"]
    return next((c for c in candidates if os.path.isfile(c)), None)


def _version_key(path: str):
    import re
    m = re.search(r"R-(\d+)\.(\d+)\.(\d+)", path)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def _r_value(v) -> str:
    """A Python value as R literal (for the slider values handed to plotart_param())."""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return repr(v)
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _r_path(p: Path) -> str:
    return str(p).replace("\\", "/")


PRELUDE = r"""
local({
  .p <- new.env()
  .p$specs <- list()
  .p$values <- list(__VALUES__)
  .p$out <- "__OUT__"
  .p$type <- if (capabilities("cairo")) "cairo" else getOption("bitmapType")
  .p$open <- function(w, h) {
    while (!is.null(grDevices::dev.list())) grDevices::dev.off()
    grDevices::png(file.path(.p$out, "frame-%04d.png"), width = w, height = h, type = .p$type, bg = "white")
  }
  assign(".plotart", .p, envir = globalenv())
})
plotart_seed <- __SEED__
set.seed(plotart_seed)
plotart_canvas <- function(width = 800, height = 800) invisible(.plotart$open(width, height))
plotart_param <- function(name, default, min = NULL, max = NULL, step = NULL, options = NULL) {
  kind <- if (!is.null(options)) "choice" else if (is.logical(default)) "bool" else
    if (is.character(default) && startsWith(default, "#")) "color" else if (is.character(default)) "text" else
    if (all(c(default, min, step) == round(c(default, min, step)))) "int" else "float"
  if (is.null(.plotart$specs[[name]])) {
    .plotart$specs[[name]] <- list(name = name, kind = kind, default = default, min = min, max = max,
                                   step = step, options = options)
  }
  v <- .plotart$values[[name]]
  if (is.null(v)) default else v
}
plotart_canvas(__WIDTH__, __HEIGHT__)
"""

RUNNER = r"""
.plotart_exprs <- tryCatch(parse("__SCRIPT__", keep.source = TRUE, encoding = "UTF-8"), error = function(e) {
  writeLines(c("parse", conditionMessage(e)), file.path(.plotart$out, "error.txt"), useBytes = TRUE)
  quit(save = "no", status = 2)
})
for (.plotart_i in seq_along(.plotart_exprs)) {
  .plotart_ok <- tryCatch({
    .plotart_r <- withVisible(eval(.plotart_exprs[[.plotart_i]], envir = globalenv()))
    if (.plotart_r$visible) print(.plotart_r$value)
    TRUE
  }, error = function(e) {
    line <- utils::getSrcLocation(.plotart_exprs[.plotart_i], "line")
    writeLines(c(as.character(if (is.null(line)) "" else line[1]), conditionMessage(e)),
               file.path(.plotart$out, "error.txt"), useBytes = TRUE)
    FALSE
  })
  if (!.plotart_ok) break
}
while (!is.null(grDevices::dev.list())) grDevices::dev.off()
.plotart_lines <- vapply(.plotart$specs, function(s) {
  enc <- function(x) if (is.null(x)) "" else paste(x, collapse = "\u001f")
  paste(s$name, s$kind, enc(s$default), enc(s$min), enc(s$max), enc(s$step), enc(s$options), sep = "\t")
}, character(1))
writeLines(enc2utf8(unname(.plotart_lines)), file.path(.plotart$out, "params.tsv"), useBytes = TRUE)
"""


def _parse_specs(path: Path) -> list[dict]:
    """params.tsv → Studio slider specs (same shape as plotart's Param.to_json())."""
    specs = []
    if not path.exists():
        return specs
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        name, kind, default, lo, hi, step, options = parts[:7]
        num = kind in ("int", "float")
        conv = (int if kind == "int" else float) if num else str

        def val(x, fallback=None):
            return conv(float(x)) if (num and x) else (x if x else fallback)
        d = val(default)
        if kind == "bool":
            d = default == "TRUE"
        spec = {"name": name, "label": name, "kind": kind, "default": d, "help": "", "choices": None,
                "min": None, "max": None, "step": None}
        if num:
            spec["min"] = val(lo, 0)
            spec["max"] = val(hi, max(10, d * 3) if kind == "int" else max(1.0, d * 3))
            spec["step"] = val(step, 1 if kind == "int" else round((spec["max"] - spec["min"]) / 200, 6) or 0.001)
        if kind == "choice":
            opts = options.split("\x1f") if options else []
            spec["choices"] = [[o, o] for o in opts]
        specs.append(spec)
    return specs


def run_r(source: str, params: dict | None = None, seed: int = 1, size: tuple[int, int] = DEFAULT_SIZE,
          timeout: float = 120.0) -> dict:
    """Run an R script → {"frames": [png …], "width", "height", "log", "error", "params", "ms"}."""
    rscript = find_rscript()
    if rscript is None:
        raise RError("R wurde nicht gefunden. Installieren von https://cran.r-project.org "
                     "oder den Pfad zu Rscript in der Umgebungsvariable PLOTART_RSCRIPT angeben.")
    params = {k: v for k, v in (params or {}).items() if not k.startswith("__")}
    tmp = Path(tempfile.mkdtemp(prefix="plotart_r_"))
    try:
        out = tmp / "bilder"
        out.mkdir()
        (tmp / "skizze.R").write_text(source, encoding="utf-8")
        values = ", ".join(f"`{k.replace('`', '')}` = {_r_value(v)}" for k, v in params.items())
        runner = PRELUDE + RUNNER
        for key, value in {"__VALUES__": values, "__OUT__": _r_path(out), "__SEED__": str(int(seed)),
                           "__WIDTH__": str(int(size[0])), "__HEIGHT__": str(int(size[1])),
                           "__SCRIPT__": _r_path(tmp / "skizze.R")}.items():
            runner = runner.replace(key, value)
        (tmp / "runner.R").write_text(runner, encoding="utf-8")
        t0 = time.perf_counter()
        try:
            proc = subprocess.run([rscript, "--vanilla", "--encoding=UTF-8", str(tmp / "runner.R")],
                                  capture_output=True, timeout=timeout, cwd=str(tmp),
                                  env={**os.environ, "R_LIBS_USER": os.environ.get("R_LIBS_USER", "")}
                                  if os.environ.get("R_LIBS_USER") else None,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            log = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
        except subprocess.TimeoutExpired as exc:
            log = ((exc.stdout or b"") + (exc.stderr or b"")).decode("utf-8", errors="replace")
            return {"frames": [], "log": log, "params": [], "ms": round((time.perf_counter() - t0) * 1000),
                    "error": {"message": f"Abgebrochen: Das Skript lief länger als {timeout:g} s.", "line": None}}
        ms = round((time.perf_counter() - t0) * 1000)
        error = None
        err_file = out / "error.txt"
        if err_file.exists():
            first, *rest = err_file.read_text(encoding="utf-8", errors="replace").splitlines() or [""]
            message = "\n".join(rest).strip()
            if first == "parse":
                import re
                m = re.search(r":(\d+):(\d+):", message)
                error = {"message": "Syntaxfehler: " + message.split("\n")[0].split(": ", 1)[-1],
                         "line": int(m.group(1)) if m else None}
            else:
                error = {"message": message, "line": int(first) if first.isdigit() else None}
        elif proc.returncode != 0:
            error = {"message": (log.strip().splitlines() or ["R ist mit einem Fehler beendet worden."])[-1],
                     "line": None}
        pngs = [p.read_bytes() for p in sorted(out.glob("frame-*.png"))]
        pngs = [p for p in pngs if len(p) > 0]
        width = height = None
        if pngs:
            width, height = int.from_bytes(pngs[0][16:20], "big"), int.from_bytes(pngs[0][20:24], "big")
        if not pngs and error is None:
            error = {"message": "Das Skript hat nichts gezeichnet.", "line": None}
        return {"frames": pngs, "width": width, "height": height, "log": log.strip()[-20000:], "error": error,
                "params": _parse_specs(out / "params.tsv"), "ms": ms}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
