# Python-Bibliotheken für generative Kunst – und wie sie mit plotart zusammenspielen

plotart ist absichtlich **reines Python ohne Pflicht-Abhängigkeiten**. Damit läuft es überall:
- am Desktop,
- im Browser über Pyodide,
- in Blender,
- in TouchDesigner.

Viele spezialisierte Bibliotheken lassen sich aber direkt **in Skizzen importieren**. Diese Übersicht sagt, wofür sich welche lohnt.

## Überblick

| Bibliothek | Wofür | Verhältnis zu plotart | Einbinden |
|---|---|---|---|
| **py5** | Processing (Java) in Python, sehr vollständig, GPU, schnell | Vorbild für die API; plotart versteht dieselben camelCase-Namen (`noFill`, `strokeWeight` …) | eigenes Programm (braucht Java); Skizzen lassen sich meist mit wenigen Änderungen portieren |
| **p5** (p5py) | Python-Port der Processing-API, Fenster mit OpenGL | ähnlich; plotart nutzt dieselben snake_case-Namen | eigenes Programm |
| **vsketch** + **vpype** | Plotter-Kunst: Processing-artige API, Pipeline für Plotter-Dateien (sortieren, verschmelzen, Layer) | gleiche Zielgruppe; plotart-Plotter-SVGs lassen sich mit vpype weiterverarbeiten | `vpype read skizze_plotter.svg linemerge linesort write out.svg` |
| **shapely** | 2D-Geometrie: Vereinigung, Differenz, Versatz (Buffer), Schnitt | **eingebaut** über `shape_union()`, `shape_difference()`, `offset_shape()`, `draw_geometry()` | `pip install shapely` (Browser: automatisch) |
| **numpy** | schnelle Zahlenfelder (Pixel, Felder, Simulationen) | **eingebaut**: `img.pixels`, Reaktion-Diffusion, Seeds werden mitgesetzt | `import numpy as np` in der Skizze |
| **Pillow** | Bilder laden/rastern | **eingebaut** für PNG, Video, Filter | `pip install Pillow` |
| **opensimplex** | Simplex-Noise (2D–4D) | Alternative zu `noise()`; 4D erlaubt nahtlose Noise-Loops | `from opensimplex import OpenSimplex` |
| **trimesh** | 3D-Meshes laden, prüfen, exportieren (STL, PLY …) | ergänzt `mesh()` und den GLB/OBJ-Export (z. B. für 3D-Druck) | `trimesh.load("x.glb")` → Punkte in `mesh()` |
| **drawsvg** | SVG-Erzeugung in Python, auch Animationen | plotart erzeugt SVG selbst; drawsvg ist eine schlanke Alternative ohne Studio | – |
| **pycairo** / **skia-python** | sehr schnelles 2D-Rendering | plotart nutzt Cairo automatisch, wenn `cairosvg` installiert ist | `pip install cairosvg` |
| **taichi** | Python-Code auf der GPU (Partikel, Fluide) | für Simulationen mit Millionen Teilchen; Ergebnis als Punkte/Bild in plotart zeichnen | `import taichi as ti` |

## Rezepte

**vpype nach plotart** – Plotter-Datei für große Formate optimieren:

```bash
python -m plotart sketch meine.py --plotter --verdeckt
vpype read meine_1_plotter.svg linemerge --tolerance 0.1mm linesort reloop write --page-size a3 fertig.svg
```

**opensimplex für einen nahtlosen Loop** – Noise auf einem Kreis in 4D:

```python
from opensimplex import OpenSimplex
os = OpenSimplex(seed)
def draw():
    background(255)
    a = TAU * t
    for i in range(200):
        n = os.noise4(i * 0.05, 0, cos(a) * 0.8, sin(a) * 0.8)
        circle(width / 2 + i * 2 - 200, height / 2 + n * 150, 4)
```

**trimesh-Modell in plotart zeichnen:**

```python
import trimesh
m = trimesh.load("daten/hase.stl")
lights()
translate(width / 2, height / 2)
scale(200)
mesh(m.vertices.tolist(), m.faces.tolist(), closed=True)
```

## Quellen

- py5: https://py5coding.org/ · https://github.com/py5coding
- p5 (p5py): https://p5.readthedocs.io/ · für Processing-Umsteiger: https://p5.readthedocs.io/en/latest/guides/for-processing-users.html
- vsketch: https://vsketch.readthedocs.io/ · https://pypi.org/project/vsketch
- vpype: https://pypi.org/project/vpype/ · https://vpype.readthedocs.io/
- shapely: https://shapely.readthedocs.io/en/2.1.2/reference/shapely.union.html
- opensimplex: https://pypi.python.org/pypi/opensimplex · https://github.com/lmas/opensimplex (archiviert, umgezogen nach code.larus.se)
- trimesh: https://pypi.org/project/trimesh/
- drawsvg: https://pypi.org/project/drawsvg · https://github.com/cduck/drawsvg
- taichi: https://docs.taichi-lang.org/docs/
