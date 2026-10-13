"""plotart for Blender – sidebar panel that turns plotart sketches into Blender objects.

Packaged as a Blender extension by plotart/blender/package.py (this file becomes the
extension's __init__.py, the plotart package is bundled next to it).
"""
from __future__ import annotations

import json
import os
import random
import time

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty

try:                                    # packaged extension: plotart is bundled inside
    from .plotart.blender import build as pbuild
    from .plotart.blender import scene as pscene
    from .plotart.sketch import list_examples
except ImportError:                     # running from a plotart checkout
    from . import build as pbuild
    from . import scene as pscene
    from ..sketch import list_examples

bl_info = {
    "name": "plotart",
    "author": "plotart",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "3D-Viewport › Seitenleiste (N) › plotart",
    "description": "Generative-Kunst-Skizzen (Python, p5-Stil) als Blender-Objekte",
    "category": "Import-Export",
}

PARAM_PREFIX = "plotart: "
_EXAMPLES: list = []                    # keep enum strings alive (Blender requirement)
_STATE = {"mtime": None, "path": None}


def _example_items(self, context):
    if not _EXAMPLES:
        for ex in list_examples():
            _EXAMPLES.append((ex["name"], ex["title"], ""))
    return _EXAMPLES


def _source(settings) -> tuple[str, str]:
    """(source code, display name)"""
    if settings.source == "EXAMPLE":
        for ex in list_examples():
            if ex["name"] == settings.example:
                return ex["source"], ex["title"]
        raise pscene.SceneError("Beispiel nicht gefunden")
    path = bpy.path.abspath(settings.filepath)
    if not path or not os.path.isfile(path):
        raise pscene.SceneError("Bitte eine Skizzen-Datei (.py) wählen")
    with open(path, encoding="utf-8") as f:
        return f.read(), os.path.basename(path)


def _param_values(scene) -> dict:
    out = {}
    for spec in json.loads(scene.get("plotart_specs", "[]")):
        key = PARAM_PREFIX + spec["name"]
        if key in scene.keys():
            v = scene[key]
            out[spec["name"]] = bool(v) if spec["kind"] == "bool" else v
    return out


def _sync_params(scene, specs: list):
    """Create one custom property per sketch param (with min/max) so the panel can draw it."""
    old = json.loads(scene.get("plotart_specs", "[]"))
    names = {s["name"] for s in specs}
    for s in old:
        if s["name"] not in names and PARAM_PREFIX + s["name"] in scene.keys():
            del scene[PARAM_PREFIX + s["name"]]
    for s in specs:
        key = PARAM_PREFIX + s["name"]
        if key not in scene.keys():
            scene[key] = s["default"]
        if s["kind"] in ("int", "float") and s["min"] is not None:
            ui = scene.id_properties_ui(key)
            kw = {"min": s["min"], "max": s["max"], "soft_min": s["min"], "soft_max": s["max"],
                  "description": s.get("help") or s["label"]}
            if s["kind"] == "float":
                kw["step"] = max(1, int((s.get("step") or 0.01) * 100))
                kw["precision"] = 4 if (s.get("step") or 0.01) < 0.01 else 2
            ui.update(**kw)
    scene["plotart_specs"] = json.dumps(specs)


def run_build(context) -> str:
    scene = context.scene
    st = scene.plotart
    source, name = _source(st)
    t0 = time.perf_counter()
    desc = pscene.build_scene(
        source, _param_values(scene), st.seed, width_bu=st.width,
        frame=st.frame if st.frames_mode == "SINGLE" else None,
        max_frames=st.max_frames or None)
    _sync_params(scene, desc["params"])
    opts = pbuild.Options(stroke_mode=st.stroke_mode.lower(), relief=st.relief.lower(),
                          relief_height=st.relief_height, material_mode=st.material_mode.lower(),
                          setup_scene=st.setup_scene, camera=st.camera.lower())
    stats = pbuild.build(desc, opts, scene)
    if st.source == "FILE":
        _STATE["path"] = bpy.path.abspath(st.filepath)
        _STATE["mtime"] = os.path.getmtime(_STATE["path"])
    msg = (f"{name}: {stats['objects']} Objekte, {stats['frames']} Bild(er) "
           f"in {time.perf_counter() - t0:.1f} s")
    st.status = msg
    return msg


# ------------------------------------------------------------------------- operators
class PLOTART_OT_build(bpy.types.Operator):
    bl_idname = "plotart.build"
    bl_label = "Importieren / Aktualisieren"
    bl_description = "Skizze ausführen und als Blender-Objekte aufbauen (ersetzt den letzten Import)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            msg = run_build(context)
        except pscene.SceneError as exc:
            context.scene.plotart.status = f"Fehler: {exc}"
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except Exception as exc:  # noqa: BLE001 – show anything in the UI
            context.scene.plotart.status = f"Fehler: {type(exc).__name__}: {exc}"
            self.report({"ERROR"}, f"{type(exc).__name__}: {exc}")
            return {"CANCELLED"}
        self.report({"INFO"}, msg)
        return {"FINISHED"}


class PLOTART_OT_new_seed(bpy.types.Operator):
    bl_idname = "plotart.new_seed"
    bl_label = "Neuer Seed"
    bl_description = "Zufälligen Seed wählen und neu aufbauen"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        context.scene.plotart.seed = random.randint(1, 999_999)
        return bpy.ops.plotart.build()


class PLOTART_OT_reset_params(bpy.types.Operator):
    bl_idname = "plotart.reset_params"
    bl_label = "Standardwerte"
    bl_description = "Alle Regler auf die Standardwerte der Skizze zurücksetzen"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        for key in [k for k in scene.keys() if k.startswith(PARAM_PREFIX)]:
            del scene[key]
        scene["plotart_specs"] = "[]"
        return bpy.ops.plotart.build()


class PLOTART_OT_open_studio(bpy.types.Operator):
    bl_idname = "plotart.open_studio"
    bl_label = "Studio öffnen"
    bl_description = "Das plotart Studio im Browser öffnen (vorher `python3 -m plotart` starten)"

    def execute(self, context):
        import webbrowser
        webbrowser.open("http://localhost:8765/")
        return {"FINISHED"}


# ------------------------------------------------------------------------- auto reload
def _watch():
    try:
        scene = bpy.context.scene
        st = scene.plotart
    except AttributeError:
        return 1.0
    if not st.auto_reload or st.source != "FILE":
        return 1.0
    path = bpy.path.abspath(st.filepath)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return 1.0
    if _STATE["path"] == path and _STATE["mtime"] is not None and mtime > _STATE["mtime"]:
        _STATE["mtime"] = mtime
        try:
            run_build(bpy.context)
        except Exception as exc:  # noqa: BLE001
            st.status = f"Fehler: {exc}"
    return 1.0


# ------------------------------------------------------------------------- settings & panel
class PlotartSettings(bpy.types.PropertyGroup):
    source: EnumProperty(name="Quelle", items=[("FILE", "Datei", "Eigene Skizze (.py)"),
                                               ("EXAMPLE", "Beispiel", "Mitgelieferte Beispiel-Skizze")])
    filepath: StringProperty(name="Skizze", subtype="FILE_PATH", description="plotart-Skizze (.py)")
    example: EnumProperty(name="Beispiel", items=_example_items)
    seed: IntProperty(name="Seed", default=1, min=1, description="Gleicher Seed = gleiches Ergebnis")
    width: FloatProperty(name="Breite", default=10.0, min=0.01, unit="LENGTH",
                         description="Breite der Leinwand in Blender-Einheiten")
    frames_mode: EnumProperty(name="Bilder", items=[
        ("ALL", "Ganze Animation", "Jedes Bild auf der Zeitleiste (Sichtbarkeits-Keyframes)"),
        ("SINGLE", "Ein Bild", "Nur ein einzelnes Bild der Animation (inkl. Spuren)")])
    frame: IntProperty(name="Bild", default=1, min=1)
    max_frames: IntProperty(name="Max. Bilder", default=0, min=0, description="0 = alle")
    stroke_mode: EnumProperty(name="Linien", items=[("FLAT", "Flach", "Flache Bänder wie in 2D"),
                                                    ("TUBE", "Röhren", "Runde 3D-Röhren (Kurven mit Bevel)")])
    relief: EnumProperty(name="Relief", items=[
        ("NONE", "Aus", "Flach wie das 2D-Bild"),
        ("CONSTANT", "Gleich hoch", "Alle Formen gleich hoch"),
        ("ORDER", "Nach Reihenfolge", "Später gezeichnete Formen sind höher"),
        ("BRIGHTNESS", "Nach Helligkeit", "Helle Formen sind höher")])
    relief_height: FloatProperty(name="Höhe", default=0.5, min=0.0, unit="LENGTH")
    material_mode: EnumProperty(name="Material", items=[
        ("FLAT", "Flach", "Leuchtende Farben – exakt wie das 2D-Bild"),
        ("PHYSICAL", "Physikalisch", "Principled BSDF – reagiert auf Licht und Schatten")])
    camera: EnumProperty(name="Kamera", items=[("TOP", "Draufsicht", "Orthografisch, exakt das 2D-Bild"),
                                               ("PERSPECTIVE", "Perspektive", "Schräg von vorne – zeigt Relief")])
    setup_scene: BoolProperty(name="Kamera & Render einrichten", default=True,
                              description="Kamera, Auflösung, fps und Bildbereich setzen")
    auto_reload: BoolProperty(name="Automatisch neu laden", default=True,
                              description="Neu aufbauen, sobald die Skizzen-Datei gespeichert wird")
    status: StringProperty(name="Status", default="")


class VIEW3D_PT_plotart(bpy.types.Panel):
    bl_label = "plotart"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "plotart"

    def draw(self, context):
        scene = context.scene
        st = scene.plotart
        col = self.layout.column()
        col.prop(st, "source", expand=True)
        col.prop(st, "filepath" if st.source == "FILE" else "example", text="")
        row = col.row(align=True)
        row.prop(st, "seed")
        row.operator("plotart.new_seed", text="", icon="FILE_REFRESH")
        col.operator("plotart.build", icon="IMPORT")
        if st.source == "FILE":
            col.prop(st, "auto_reload")

        specs = json.loads(scene.get("plotart_specs", "[]"))
        if specs:
            box = self.layout.box()
            head = box.row()
            head.label(text="Parameter", icon="OPTIONS")
            head.operator("plotart.reset_params", text="", icon="LOOP_BACK")
            for s in specs:
                key = PARAM_PREFIX + s["name"]
                if key in scene.keys():
                    box.prop(scene, f'["{key}"]', text=s["label"])
                    if s["kind"] == "choice":
                        box.label(text="  " + " · ".join(v for v, _ in s["choices"][:8]))
            box.label(text="Änderungen: „Importieren / Aktualisieren“", icon="INFO")

        box = self.layout.box()
        box.label(text="Darstellung", icon="SHADING_RENDERED")
        box.prop(st, "width")
        box.prop(st, "stroke_mode")
        box.prop(st, "material_mode")
        box.prop(st, "relief")
        if st.relief != "NONE":
            box.prop(st, "relief_height")
        box.prop(st, "camera")

        box = self.layout.box()
        box.label(text="Animation", icon="RENDER_ANIMATION")
        box.prop(st, "frames_mode", text="")
        box.prop(st, "frame" if st.frames_mode == "SINGLE" else "max_frames")
        self.layout.prop(st, "setup_scene")
        if st.status:
            self.layout.label(text=st.status, icon="ERROR" if st.status.startswith("Fehler") else "CHECKMARK")
        self.layout.operator("plotart.open_studio", icon="URL")


CLASSES = (PlotartSettings, PLOTART_OT_build, PLOTART_OT_new_seed, PLOTART_OT_reset_params,
           PLOTART_OT_open_studio, VIEW3D_PT_plotart)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.plotart = PointerProperty(type=PlotartSettings)
    if not bpy.app.timers.is_registered(_watch):
        bpy.app.timers.register(_watch, first_interval=1.0, persistent=True)


def unregister():
    if bpy.app.timers.is_registered(_watch):
        bpy.app.timers.unregister(_watch)
    del bpy.types.Scene.plotart
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
