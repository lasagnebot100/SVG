"""Create .blend files (and renders) from sketches without opening Blender's UI.

Uses the `bpy` module if it is importable (pip install bpy), otherwise runs a Blender
executable in the background (found via $PLOTART_BLENDER, PATH or the usual install folders).
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent      # folder that contains `plotart`


class BlenderError(Exception):
    pass


def find_blender() -> str | None:
    env = os.environ.get("PLOTART_BLENDER")
    if env and os.path.isfile(env):
        return env
    exe = shutil.which("blender")
    if exe:
        return exe
    candidates = ["/Applications/Blender.app/Contents/MacOS/Blender"]
    candidates += sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender*\blender.exe"), reverse=True)
    candidates += sorted(glob.glob("/snap/bin/blender") + glob.glob(os.path.expanduser("~/blender*/blender")),
                         reverse=True)
    return next((c for c in candidates if os.path.isfile(c)), None)


def _main(args: dict) -> dict:
    """Runs inside Blender (or with the bpy module)."""
    import bpy

    from . import build, scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    desc = scene.build_scene(args["source"], args.get("params"), int(args.get("seed") or 1),
                             width_bu=float(args.get("width") or 10.0), frame=args.get("frame"),
                             max_frames=args.get("max_frames"))
    stats = build.build(desc, build.Options(**args.get("options", {})))
    sc = bpy.context.scene
    if args.get("engine"):
        sc.render.engine = args["engine"]
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args["out"]))
    render = args.get("render")
    if render:
        if sc.render.engine == "CYCLES":
            sc.cycles.samples = int(args.get("samples") or 32)
        if desc["animated"]:
            # image sequence render: path ends with ####
            sc.render.filepath = os.path.abspath(render)
            bpy.ops.render.render(animation=True)
        else:
            sc.render.filepath = os.path.abspath(render)
            bpy.ops.render.render(write_still=True)
    return {"out": os.path.abspath(args["out"]), **stats}


_DRIVER = """
import json, sys
args = json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8"))
sys.path.insert(0, args["root"])
from plotart.blender.make import _main
res = _main(args)
print("PLOTART_RESULT " + json.dumps(res))
"""


def make_blend(source: str, out: str, *, params: dict | None = None, seed: int = 1, width: float = 10.0,
               frame: int | None = None, max_frames: int | None = None, options: dict | None = None,
               render: str | None = None, engine: str | None = None, samples: int | None = None) -> dict:
    args = {"source": source, "out": out, "params": params or {}, "seed": seed, "width": width,
            "frame": frame, "max_frames": max_frames, "options": options or {}, "render": render,
            "engine": engine, "samples": samples, "root": str(ROOT)}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    try:
        import bpy  # noqa: F401
    except ImportError:
        pass
    else:
        return _main(args)
    exe = find_blender()
    if not exe:
        raise BlenderError("Blender wurde nicht gefunden. Installieren (https://www.blender.org/download/), "
                           "Pfad in PLOTART_BLENDER setzen oder `pip install bpy`.")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(args, f)
        argfile = f.name
    try:
        proc = subprocess.run([exe, "--background", "--factory-startup", "--python-expr", _DRIVER, "--", argfile],
                              capture_output=True, text=True)
    finally:
        os.unlink(argfile)
    for line in proc.stdout.splitlines():
        if line.startswith("PLOTART_RESULT "):
            return json.loads(line[len("PLOTART_RESULT "):])
    tail = (proc.stderr or proc.stdout).strip().splitlines()[-12:]
    raise BlenderError("Blender-Fehler:\n" + "\n".join(tail))


if __name__ == "__main__":  # pragma: no cover - manual use: python -m plotart.blender.make args.json
    print(json.dumps(_main(json.load(open(sys.argv[1], encoding="utf-8")))))
