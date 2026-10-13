# plotart → TouchDesigner: callbacks for a Script TOP
#
# 1. Script TOP anlegen, im Parameter „Callbacks DAT“ diesen Text einsetzen
#    (oder: python -m plotart touchdesigner  → schreibt diese Datei mit dem richtigen Pfad).
# 2. PLOTART_PATH unten auf den Ordner setzen, der den Ordner „plotart“ enthält.
# 3. Pillow für Python 3.11 installieren und in TouchDesigner unter
#    Preferences › Python 64-bit Module Path eintragen (siehe docs/touchdesigner.md).
# 4. Auf der Parameter-Seite „plotart“ die Skizze (.py) wählen. Speichern im Studio → TD lädt neu.
#
# OSC/CHOP-Werte: einen CHOP (z. B. OSC In CHOP) bei „Werte-CHOP“ eintragen – Kanal „td/level“
# kommt in der Skizze als osc("/td/level") an. Maus: CHOP mit Kanälen u, v, select (Panel CHOP).
#
# Diese Datei ist eine Vorlage und wurde nicht in TouchDesigner selbst getestet.
# Steht das Bild auf dem Kopf, den Schalter „Vertikal spiegeln“ umlegen (oder Flip TOP).

PLOTART_PATH = r""          # z. B. r"C:\Users\du\SVG"  (der Ordner, in dem „plotart“ liegt)

import sys

if PLOTART_PATH and PLOTART_PATH not in sys.path:
    sys.path.insert(0, PLOTART_PATH)


def onSetupParameters(scriptOp):
    page = scriptOp.appendCustomPage("plotart")
    page.appendFile("Sketch", label="Skizze (.py)")
    p = page.appendInt("Seed", label="Seed")[0]
    p.default = 1
    p.normMin, p.normMax = 1, 1000
    p = page.appendFloat("Scale", label="Skalierung")[0]
    p.default = 1.0
    p.normMin, p.normMax = 0.25, 4.0
    p = page.appendToggle("Flip", label="Vertikal spiegeln")[0]
    p.default = True
    p = page.appendToggle("Play", label="Abspielen")[0]
    p.default = True
    page.appendCHOP("Valueschop", label="Werte-CHOP (→ osc())")
    page.appendCHOP("Mousechop", label="Maus-CHOP (u, v, select)")
    page.appendPulse("Restart", label="Neu starten")
    return


def _renderer(scriptOp, force=False):
    from plotart.touchdesigner import TDRenderer
    path = scriptOp.par.Sketch.eval()
    key = (path, int(scriptOp.par.Seed.eval()), float(scriptOp.par.Scale.eval()), bool(scriptOp.par.Flip.eval()))
    r = scriptOp.storage.get("plotart")
    if force or r is None or scriptOp.storage.get("plotart_key") != key:
        r = TDRenderer(path, seed=key[1], scale=key[2] if key[2] > 0 else None, flip=key[3]) if path else None
        scriptOp.storage["plotart"] = r
        scriptOp.storage["plotart_key"] = key
    return r


def onPulse(par):
    if par.name == "Restart":
        _renderer(par.owner, force=True)
    return


def onCook(scriptOp):
    if not scriptOp.par.Play.eval() and "plotart" in scriptOp.storage:
        return                                   # keep the last image
    _ = absTime.frame                            # noqa: F821 – cook every frame while playing
    try:
        r = _renderer(scriptOp)
    except Exception as exc:                     # e.g. Pillow missing, wrong path
        scriptOp.addError(f"plotart: {exc}")
        return
    if r is None:
        return
    osc = {}
    chop = scriptOp.par.Valueschop.eval()
    if chop is not None:
        for c in chop.chans():
            osc["/" + c.name.lstrip("/")] = [c.eval()]
    mouse = None
    mchop = scriptOp.par.Mousechop.eval()
    if mchop is not None and mchop.chan("u") is not None and mchop.chan("v") is not None:
        sel = mchop.chan("select")
        mouse = (mchop["u"].eval(), mchop["v"].eval(), bool(sel.eval()) if sel is not None else False)
    arr = r.next_frame(osc=osc, mouse=mouse)
    if r.error:
        scriptOp.addError("plotart: " + r.error)
    scriptOp.copyNumpyArray(arr)
    return
