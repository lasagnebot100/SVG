# plotart – generative SVG-Kunst für Stiftplotter

Ein einfach zu bedienendes Python-Tool, das algorithmische Kunst als **plotterfertige SVG-Dateien** erzeugt – mit Live-Vorschau im Browser.

![Galerie](examples/gallery.jpg)

## Highlights

- **Reines Python** – keine Abhängigkeiten (Pillow nur optional für PNG-Vorschauen)
- **Web-Oberfläche** mit Schiebereglern, Live-Vorschau und 🎲-Knopf für neue Varianten
- **7 Generatoren**, darunter das **Pixel-Raster** im Stil von Rasterdrucken mit gefüllten Balken
- **Plotter-optimiert**:
  - Maße in **Millimeter**, Papierformate A6–A1, Letter, 30×40, 50×70
  - Flächen werden mit **Schraffur passend zur Stiftbreite** gefüllt (z. B. Micron 05 ≈ 0,45 mm)
  - Füllungen als **eine durchgehende Linie** → kaum Stift-Absetzen
  - **Pfad-Optimierung**: Linien werden verbunden und so sortiert, dass Leerfahrten minimal sind
  - **Ebenen pro Stift** (Inkscape-Layer) für mehrfarbige Plots – kompatibel mit AxiDraw, iDraw, vpype, Inkscape
  - Anzeige von Linienlänge, Leerfahrt, Anzahl Pfade und geschätzter Plotzeit
- **Reproduzierbar**: gleicher Seed + gleiche Parameter = identisches Bild (wird in den SVG-Metadaten gespeichert)

## Schnellstart

```bash
git clone <repo-url> && cd SVG
python3 -m plotart
```

Der Browser öffnet sich automatisch unter `http://localhost:8765`. Dann:

1. Generator links wählen
2. **Leertaste** oder **🎲 Neu** → neue Variante
3. **✨ Alles** → alle Parameter zufällig würfeln
4. Regler anpassen, unter **Papier & Stift** Format, Rand, Stiftbreite und Farben einstellen
5. **⬇ SVG laden** oder **💾 Speichern** (landet im Ordner `output/`)

Optional als Befehl installieren: `pip install -e .` → danach einfach `plotart`.

## Am iPad, Handy oder ohne Installation (Web-App)

plotart läuft auch **komplett im Browser** – Python wird dabei per [Pyodide](https://pyodide.org) (WebAssembly) direkt im Browser ausgeführt, es braucht keinen Server.

**Online:** https://lasagnebot100.github.io/SVG/

- Am iPad in Safari öffnen → Teilen → **„Zum Home-Bildschirm“** → startet wie eine App
- Erster Start lädt Python einmalig (ca. 10 MB), danach aus dem Cache
- **📤 Teilen** öffnet das iOS-Teilen-Menü → „In Dateien sichern“, AirDrop, Mail …

**Selbst bauen:**

```bash
python3 tools/build_web.py          # → site/index.html, statisch hostbar (Netlify, eigener Webspace …)
```

**Veröffentlichung:** Der Workflow `.github/workflows/pages.yml` testet, baut und veröffentlicht die Web-App bei jedem Push auf den Standard-Branch. Einmalig nötig: im Repo unter **Settings → Pages → Source** „GitHub Actions“ auswählen.

**Im lokalen Netz** (ohne Internet): `python3 -m plotart web --host 0.0.0.0` am Computer starten und am iPad `http://<IP-des-Computers>:8765` öffnen.

## Die Generatoren

| Name | Titel | Beschreibung |
|---|---|---|
| `blocks` | Pixel-Raster | Quadrate, Striche und Punkte im Raster; dichte Zonen verschmelzen zu gefüllten Balken |
| `flowfield` | Strömungsfeld | Gleichmäßig verteilte Stromlinien durch ein Rauschfeld (Rauschen, Wirbel, Wellen, Explosion) |
| `waves` | Wellenlinien | Gestapelte Bergrücken mit verdeckten Linien („Unknown Pleasures“) |
| `topo` | Höhenlinien | Topografische Karte einer Zufallslandschaft, jede n-te Linie in Stift 2 |
| `circles` | Kreis-Packung | Dicht gepackte Kreise mit Ringen, Spiralen oder Schraffuren |
| `truchet` | Truchet-Muster | Kacheln mit Viertelkreisen, die zu endlosen Linien verschmelzen |
| `harmonograph` | Harmonograph | Gedämpfte Pendelkurve – eine einzige durchgehende Linie, optional als Moiré |

## Kommandozeile

```bash
python3 -m plotart list                                   # alle Generatoren + Parameter
python3 -m plotart render blocks --seed 42                # → output/blocks_42.svg
python3 -m plotart render blocks -s 42 -p cols=60 -p fill=outline --paper A4 --png
python3 -m plotart render topo -n 5 --landscape           # 5 zufällige Varianten (mit -s 10: Seeds 10–14)
python3 -m plotart render waves -o mein_bild.svg --pen 0.3 --margin 30
python3 -m plotart random -n 10                           # 10 Zufallsbilder, zufällige Parameter
python3 -m plotart web --port 9000 --no-browser           # Web-Oberfläche mit Optionen
```

Wichtige Optionen: `--paper`, `--landscape`, `--margin` (mm), `--pen` (Stiftbreite in mm), `--color1`, `--color2`, `--png`, `-o`.

## Als Python-Bibliothek

```python
from plotart import render, to_svg

d = render("blocks", {"cols": 40, "profile": "center"}, seed=123,
           settings={"paper": "A3", "pen_width": 0.5})
open("bild.svg", "w").write(to_svg(d))
print(d.stats())   # Linienlänge, Leerfahrt, Pfade, geschätzte Minuten
```

## Eigenen Generator hinzufügen

Neue Datei in `plotart/generators/` anlegen und in `plotart/generators/__init__.py` in der Import-Zeile ergänzen:

```python
from ..params import Param
from . import register

@register("gitter", "Mein Gitter", "Kurze Beschreibung", [
    Param("n", "Anzahl", 20, 2, 100, 1),
])
def generate(d, rng, noise, p):
    x0, y0, x1, y1 = d.box               # Zeichenfläche in mm (innerhalb des Rands)
    for i in range(p["n"] + 1):
        x = x0 + (x1 - x0) * i / p["n"]
        d.line(x, y0, x, y1)             # layer=2 für den zweiten Stift
```

Die Parameter erscheinen automatisch als Regler in der Web-Oberfläche und in `plotart list`. Clipping auf den Rand und Pfad-Optimierung passieren automatisch.

## Tipps zum Plotten

- **Stiftbreite** richtig einstellen – sie bestimmt den Abstand der Füllschraffur. Ist die Fläche nicht deckend, Regler **Schraffur-Dichte** erhöhen.
- Bei dichten Füllungen auf festeres Papier (≥ 200 g/m²) achten, sonst wellt es sich.
- **Mehrfarbig**: Stift 1 und Stift 2 sind getrennte Ebenen. In der AxiDraw-Software „Layers“ plotten oder mit vpype pro Ebene ausgeben.
- Für vpype-Workflows: `vpype read output/blocks_42.svg linesort write optimiert.svg`.
- Die geschätzte Plotzeit ist grob (30 mm/s Zeichnen, 80 mm/s Leerfahrt).

## Tests

```bash
python3 -m unittest discover -s tests
```
