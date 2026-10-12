# plotart – generative Kunst mit Python

Ein Werkzeug, um **generative und algorithmische Kunst in Python** zu erschaffen. Du schreibst Skizzen in einer Sprache **im Stil von p5.js/Processing** und siehst das Ergebnis sofort. Ausgabe als **PNG, SVG oder plotterfertige Linien**. Läuft am Computer und im Browser, auch am iPad.

![Skizzen-Beispiele](examples/skizzen.jpg)

## Highlights

- **Skizzen-Sprache wie p5.js:** `size()`, `background()`, `fill()`, `circle()`, `begin_shape()`, `push()`/`pop()`, `translate()`, `rotate()`, `noise()`, `random()` …
- **Live-Studio im Browser:** Code-Editor mit Syntax-Hervorhebung und Autovervollständigung, Vorschau bei jeder Änderung, Fehler mit Zeilennummer, durchsuchbare API-Hilfe
- **Regler automatisch:** `n = param("Anzahl", 40, 1, 200)` erzeugt einen Schieberegler
- **Volle Python-Power:** numpy, scipy, Pillow und jede andere installierte Bibliothek; Rasterbilder per `image(array)`
- **Farbe ernst genommen:** Transparenz, HSB, Verläufe (linear/radial), Mischmodi (Multiply, Screen, …), 16 kuratierte Paletten
- **Werkzeugkasten für generative Kunst:** Voronoi, Poisson-Disc, Lloyd-Relaxation, Chaikin-Glättung, Schraffur, Vektoren
- **Exporte:** Farb-SVG, PNG in jeder Auflösung (z. B. 300 dpi), **Plotter-SVG** (optimierte Linien, eine Ebene pro Farbe), Skizze als `.py`
- **12 Beispiel-Skizzen** zum Lernen und Weiterbauen
- **Reproduzierbar:** gleicher Seed + gleiche Regler = identisches Bild
- **Zusätzlich: 7 fertige Plotter-Generatoren** mit Reglern, ganz ohne Code

## Schnellstart

```bash
git clone https://github.com/lasagnebot100/SVG.git && cd SVG
python3 -m plotart
```

Das **Studio** öffnet sich unter `http://localhost:8765`.

1. Oben **„Beispiele …“** wählen oder direkt im Editor losschreiben. Mit **Live** aktualisiert sich das Bild bei jeder Änderung.
2. **🎲** würfelt einen neuen Seed, **✨** würfelt alle Regler.
3. Exportieren über **SVG**, **PNG** oder **Plotter**; **💾 .py** speichert die Skizze.

Optional: `pip install -e ".[full]"` installiert Pillow und numpy und den Befehl `plotart`.

![Studio](examples/studio.jpg)

## Deine erste Skizze

```python
size(800, 800)                                  # Pixel – oder size("A3") in Millimeter
anzahl = param("Anzahl", 120, 10, 500)          # → Regler im Studio
pal = palette("risograph")                      # kuratierte Farbpalette

background(pal[0])
no_stroke()
blend_mode(MULTIPLY)                            # Farben mischen sich wie Druckfarbe
for i in range(anzahl):
    fill(color(random(pal[1:])).alpha(0.85))
    circle(random(width), random(height), random(10, 120))
```

Optional kannst du `setup()` und `draw()` definieren wie in p5.js; beide werden einmal aufgerufen.

## Die Skizzen-Sprache – Spickzettel

| Bereich | Funktionen |
|---|---|
| **Leinwand** | `size(w, h)` · `size("A4", landscape=True)` · `background(farbe)` · `width`, `height`, `seed` |
| **Farbe & Stil** | `fill()` · `no_fill()` · `stroke()` · `no_stroke()` · `stroke_weight()` · `stroke_cap()` · `stroke_join()` · `blend_mode()` · `color_mode(HSB)` · `color()` · `hsb()` · `lerp_color()` · `color_ramp()` · `palette()` · `palettes()` · `linear_gradient()` · `radial_gradient()` |
| **Formen** | `point` · `line` · `rect` · `square` · `ellipse` · `circle` · `arc` · `triangle` · `quad` · `polygon` · `polyline` · `bezier` · `curve` · `rect_mode()` · `ellipse_mode()` |
| **Eigene Formen** | `begin_shape()` · `vertex()` · `curve_vertex()` · `bezier_vertex()` · `quadratic_vertex()` · `begin_contour()`/`end_contour()` (Löcher) · `end_shape(CLOSE)` |
| **Transformation** | `push()`/`pop()` bzw. `with push():` · `translate()` · `rotate()` · `scale()` · `shear_x()` · `shear_y()` · `reset_matrix()` |
| **Text & Bild** | `text()` · `text_size()` · `text_font()` · `text_align()` · `text_style()` · `image(numpy_array \| PIL-Bild, x, y, w, h)` |
| **Zufall & Noise** | `random()` · `random_int()` · `random_gaussian()` · `random_choice()` · `chance(p)` · `shuffle()` · `noise(x, y, z)` · `noise_detail()` · `noise_seed()` |
| **Mathe** | `map_range()` · `lerp()` · `constrain()` · `dist()` · `smoothstep()` · `ease_in_out()` · `radians()` · `degrees()` · `Vector` · `sin`, `cos`, `sqrt`, … · `PI`, `TAU`, `HALF_PI` |
| **Werkzeuge** | `poisson_disc()` · `voronoi_cells()` · `relax()` · `chaikin()` · `resample()` · `hatch_polygon()` · `polygon_area()` · `centroid()` · `point_in_polygon()` · `grid()` |
| **Parameter** | `param(name, standard, min, max, step)` · `param(name, "a", options=[…])` · `param(name, True)` · `param(name, "#1f5fbf")` |

Farben: `fill(200)`, `fill(255, 0, 0)`, `fill(255, 0, 0, 128)`, `fill("#1f5fbf")`, `fill("tomato")`, `fill(color("navy").alpha(0.5))`, `fill(verlauf)`. Die vollständige Liste mit Beschreibungen steht im Studio unter **„? Hilfe“**.

## Beispiel-Skizzen

| Nr. | Skizze | Zeigt |
|---|---|---|
| 01 | Erste Schritte | Formen, Paletten, Regler, Mischmodus |
| 02 | Noise-Landschaft | Perlin-Noise, Verläufe, eigene Formen |
| 03 | Strömungsfeld | Vektorfeld aus Noise, Linien mit Transparenz |
| 04 | Kreis-Packung | Kollisionsprüfung, konzentrische Ringe |
| 05 | Pixel-Raster | Raster mit Noise-Profil, in Millimetern (A3) |
| 06 | Voronoi-Mosaik | Poisson-Disc, Lloyd-Relaxation, Voronoi, Chaikin |
| 07 | Rekursive Teilung | Rekursion, Komposition à la Mondrian |
| 08 | L-System | Ersetzungsregeln, Turtle-Grafik mit `push`/`pop` |
| 09 | Seltsamer Attraktor | numpy, Millionen Punkte, Dichte als Bild |
| 10 | Reaktion-Diffusion | numpy-Simulation (Gray-Scott), Turing-Muster |
| 11 | Wellenlinien | Verdeckung durch Füllung (Unknown Pleasures) |
| 12 | Typografie | Text, Drehung, Noise-gesteuerte Größe |

Zu finden in `plotart/sketch/examples/`, im Studio unter „Beispiele …“, oder per Kommandozeile, z. B. `python3 -m plotart sketch 06 --png`.

## Exporte

| Export | Was | Hinweis |
|---|---|---|
| **SVG** | Vektorgrafik mit Farben, Verläufen, Transparenz | Für Illustrator, Inkscape, Web |
| **PNG** | Rasterbild in wählbarer Auflösung | Bei `size("A3")` z. B. 300 dpi für den Druck |
| **Plotter** | Nur Linien in mm, optimiert, eine Ebene pro Farbe | Für AxiDraw, iDraw, vpype; Flächen werden als Umriss gezeichnet |
| **.py** | Die Skizze selbst | Mit 📂 wieder öffnen |

Überlappende Flächen werden beim Plotter-Export nicht ausgeblendet, weil ein Plotter alles zeichnet. Für Verdeckung (wie in Beispiel 11) eignen sich die fertigen Generatoren besser.

## Kommandozeile

```bash
python3 -m plotart                                   # Studio starten
python3 -m plotart sketch meine_skizze.py --png      # Skizze → output/meine_skizze_1.svg + .png
python3 -m plotart sketch 03 -s 42 -n 5 --png        # Beispiel 03, Seeds 42–46
python3 -m plotart sketch 06 -p "Zellgröße=30" --plotter --pen 0.3
python3 -m plotart sketch 05 -o druck.png --scale 23.6   # 600 dpi (Pixel pro mm)
python3 -m plotart studio --host 0.0.0.0             # im WLAN erreichbar (mit Zugangs-Token)
```

## Als Python-Bibliothek

```python
from plotart.sketch import execute, render_svg, render_png, to_plotter

sk, log, fehler, ms = execute(open("skizze.py").read(), params={"Anzahl": 200}, seed=7)
open("bild.svg", "w").write(render_svg(sk))
open("bild.png", "wb").write(render_png(sk, scale=2))
```

## Am iPad, Handy oder ohne Installation (Web-App)

plotart läuft auch **komplett im Browser**. Python wird dabei per [Pyodide](https://pyodide.org) (WebAssembly) direkt im Browser ausgeführt, ein Server ist nicht nötig. Importiert eine Skizze numpy, lädt die Web-App es automatisch nach.

**Online:** https://lasagnebot100.github.io/SVG/

- Am iPad in Safari öffnen, dann Teilen → **„Zum Home-Bildschirm“**. plotart startet dann wie eine App.
- Der erste Start lädt Python einmalig (ca. 10 MB), danach kommt es aus dem Cache.
- Beim Export öffnet sich das iOS-Teilen-Menü: „In Dateien sichern“, AirDrop, Mail …
- Eine hängende Skizze lässt sich mit **✕ Abbrechen** stoppen.

**Selbst bauen:** `python3 tools/build_web.py` erzeugt `site/`, das du statisch hosten kannst (Netlify, eigener Webspace …).

**Veröffentlichung:** Der Workflow `.github/workflows/pages.yml` testet, baut und veröffentlicht die Web-App bei jedem Push auf den Standard-Branch. Einmalig nötig: im Repo unter **Settings → Pages → Source** „GitHub Actions“ auswählen.

**Im lokalen Netz:** `python3 -m plotart studio --host 0.0.0.0` am Computer starten und den angezeigten Link (mit `?token=…`) am iPad öffnen; `localhost` dabei durch die IP des Computers ersetzen. Das Token schützt davor, dass andere Geräte im WLAN Code auf deinem Computer ausführen.

## Fertige Plotter-Generatoren (ohne Code)

Im Studio oben rechts **„Generatoren“**: sieben fertige Generatoren mit Reglern, optimiert für Stiftplotter.

![Generatoren](examples/gallery.jpg)

| Name | Titel | Beschreibung |
|---|---|---|
| `blocks` | Pixel-Raster | Quadrate, Striche und Punkte im Raster; dichte Zonen verschmelzen zu gefüllten Balken |
| `flowfield` | Strömungsfeld | Gleichmäßig verteilte Stromlinien durch ein Rauschfeld |
| `waves` | Wellenlinien | Gestapelte Bergrücken mit verdeckten Linien |
| `topo` | Höhenlinien | Topografische Karte einer Zufallslandschaft |
| `circles` | Kreis-Packung | Dicht gepackte Kreise mit Ringen, Spiralen oder Schraffuren |
| `truchet` | Truchet-Muster | Kacheln mit Viertelkreisen, die zu endlosen Linien verschmelzen |
| `harmonograph` | Harmonograph | Gedämpfte Pendelkurve, eine einzige durchgehende Linie |

Plotter-Optimierungen:
- Flächen werden mit Schraffur passend zur **Stiftbreite** gefüllt, als eine durchgehende Linie.
- Linien werden verbunden und so sortiert, dass möglichst wenig Leerfahrt entsteht.
- Jeder Stift bekommt eine eigene Ebene (Inkscape-Layer).
- Angezeigt werden Linienlänge, Leerfahrt und geschätzte Plotzeit.

```bash
python3 -m plotart list                                   # alle Generatoren + Parameter
python3 -m plotart render blocks -s 42 -p cols=60 --paper A4 --png
python3 -m plotart random -n 10                           # 10 Zufallsbilder
```

Eigener Generator: neue Datei in `plotart/generators/` anlegen und in `plotart/generators/__init__.py` importieren.

```python
from ..params import Param
from . import register

@register("gitter", "Mein Gitter", "Kurze Beschreibung", [Param("n", "Anzahl", 20, 2, 100, 1)])
def generate(d, rng, noise, p):
    x0, y0, x1, y1 = d.box               # Zeichenfläche in mm
    for i in range(p["n"] + 1):
        x = x0 + (x1 - x0) * i / p["n"]
        d.line(x, y0, x, y1)             # layer=2 für den zweiten Stift
```

## Projektaufbau

```
plotart/
├── sketch/            Skizzen-Sprache (p5-ähnliche API), Renderer, Exporte, Beispiele
├── generators/        fertige Plotter-Generatoren
├── static/            Studio, Generator-Seite, Code-Editor (CodeMirror 5, MIT)
├── bridge.py          gemeinsame Schnittstelle für Server, Worker-Prozess und Browser
├── web.py             lokaler Server (Skizzen laufen in eigenem Prozess mit Zeitlimit)
└── cli.py             Kommandozeile
tools/build_web.py     baut die Browser-Version (Pyodide)
```

## Ausblick

- **Stufe 2 – Animation:** zeitbasierte Skizzen (`frame_count`, `t`), Zeitleiste, Export als GIF/MP4/Bildsequenz
- **Stufe 3 – Blender:** Add-on, das Skizzen als Kurven, Meshes oder Grease Pencil mit Keyframes nach Blender bringt

## Tests

```bash
python3 -m unittest discover -s tests
```
