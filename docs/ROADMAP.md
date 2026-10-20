# plotart – To-do-Liste

Leitlinie: plotart ist in erster Linie ein Werkzeug für **generative und algorithmische Kunst**. Plotter-Funktionen sind ein schönes Zusatz-Feature.

Legende: ✅ erledigt · 🔨 in Arbeit · ⬜ geplant

## ✅ Technische Baustellen (Windows-Prüfung, 19. Oktober 2026)

Vorher: 118 Tests unter Windows 11 und Python 3.14, davon 3 Fehlschläge und 1 Fehler. Nachher: 120 Tests, alle grün, mit und ohne Pillow/numpy/shapely.

- ✅ **Kodierung:** Die Tests lesen und schreiben Dateien jetzt mit `encoding="utf-8"` (vorher `UnicodeDecodeError` unter cp1252).
- ✅ **Shader-Fehlermeldungen:** `_shader_error()` erkennt auch das NVIDIA-Format `0(12) : error C…`; neuer Test ohne GPU.
- ✅ **Portable Schriftnamen:** `"sans"` und `"sans-bold"` in `find_font()` wählen eine Schrift des jeweiligen Systems; Windows-Nutzerschriften werden gefunden. Beispiel 23 und das README nutzen `"sans-bold"`.
- ✅ **Schriften in `series.py` und `raster.py`:** über `find_font()` statt fester DejaVu-Dateien.
- ✅ **Test für Beispiel 35:** wird ohne Pillow übersprungen.
- ✅ **CI:** neuer Job `windows` (Python 3.11 und 3.14).
- ✅ **README:** Abschnitt „Unter Windows (PowerShell)“.
- ✅ **`pyproject.toml`:** `requires-python = ">=3.11"`.
- ✅ **Web-Seiten-Export (gefunden bei Block II):** Der Worker-Code in `viewer.py` war seit 1.10.0 ungültig (`\(` im JS-Template-Literal), exportierte Seiten starteten nicht. Behoben in 1.11.0, mit Regressionstest.
- ✅ **Umgeleitete Ausgabe unter Windows:** `plotart` und `tools/build_web.py` stürzten bei Ausgabe in Datei, Pipe oder CI-Log an „✓“ und „→“ ab (cp1252). Behoben in 1.11.0, mit Test.
- ✅ **Studio über „localhost“ unter Windows (gefunden bei Block E):** jede Anfrage dauerte ~300 ms, weil der Browser zuerst IPv6 (`::1`) versucht; der Live-Modus lief mit 3 Bildern/s. Der Server antwortet jetzt auch auf `::1` – 2 ms pro Anfrage. Behoben in 1.12.0, mit Test.
- ✅ **PNG-Export ohne Pillow:** freundliche Meldung „PNG-Export braucht Pillow: pip install Pillow“ statt Traceback; das SVG wird trotzdem geschrieben.
- ⬜ **Offen:** `text_paths()` in der Browser-Version (Pyodide) hat keine Systemschriften. Eine freie Schrift (z. B. DejaVu Sans) mitliefern.

## ⬜ Neue Wünsche (Oktober 2026) – noch nicht begonnen, Reihenfolge wird abgestimmt

### I – Mehrere Sprachen im Studio („Mehrsprachen-Studio“)

Gemeinsam für alle Sprachen: Seed, Regler (`param`), Varianten, Favoriten, Export (PNG/SVG/Video) und Web-Seite bleiben gleich.

- ✅ **p5.js / JavaScript-Modus** – Version 1.15.0: läuft im abgeschirmten Rahmen, auch am iPad; `plotart.param()`, Seed, PNG, WebM; p5.js 1.11.13 mitgeliefert
  - ⬜ JavaScript-Farbhervorhebung, Ausgabefenster und Web-Seiten-Export für p5-Sketches
- ✅ **Processing (Java, `.pde`)** – Version 1.14.0, `plotart/languages/`:
  - ✅ Sketches mit dem installierten Processing ausführen (`Processing cli`, sonst `processing-java`), Seed, Fehler mit Zeile
  - ✅ Bilder und Animationen ins Studio holen (Sprachwahl, Player, PNG)
  - ✅ Konverter nach plotart-Python (`pde_convert.py`, Studio „⇄ nach plotart“, `plotart pde`)
  - ⬜ Java-Farbhervorhebung im Editor (CodeMirror-Modus „clike“ müsste dazukommen)
- ⬜ **R-Kunst:**
  - R-Skripte (aRtsy, ggplot2) über `Rscript` am Computer
  - R im Browser über webR
  - Beispiele im Stil von aRtsy
- ⬜ **Kotlin (OPENRNDR):**
  - Vorlagen-Projekt
  - Datenaustausch mit plotart (SVG, JSON-Geometrie, OSC)
  - optional Start aus dem Studio, braucht Java und Gradle
- ⬜ **React:**
  - React-Komponente `<PlotartWerk>`, um interaktive Werke in Websites und React-Apps einzubetten (passt zur Website-Anbindung)
  - Vorlage für React Three Fiber (3D-Generativkunst)

### ✅ II – Mathe-Kunst (Version 1.11.0, Modul `algorithms/mathart.py`, Beispiele 51–59)

- ✅ **Numerische Integration als Bild und Animation:** `riemann()` mit links/Mitte/rechts, Trapez und Simpson, Fehlerflächen; `integrate()`; Funktions-Plotter `Graph` und `formula()` für Formeln als Text
- ✅ **Kurven-Baukasten:** `lissajous()`, `rose()`, `harmonograph()`, `spirograph()`, `superformula()`, `Epicycles` (Zeichnung → Kreise), `fourier_approx()`
- ✅ **Differentialgleichungen:** `rk4()`, `phase_portrait()`, `attractor()` (Lorenz, Rössler, Aizawa, Thomas, Halvorsen, Clifford, De Jong, Svensson, Hénon, Ikeda, Tinkerbell)
- ✅ **Fraktale:** `mandelbrot()`, `julia()` (auch als Shader, Beispiel 59), `newton_fractal()`, `ifs()`, `fractal_flame()`, `colorize()`
- ✅ **Komplexe Funktionen:** `domain_coloring()` in drei Stilen

### III – Weitere Algorithmen (Ergänzung zu B)

- ⬜ Physarum (Schleimpilz-Simulation)
- ⬜ Langtons Ameise und Turmiten
- ⬜ Aquarell-Simulation (geschichtete, verformte Polygone)
- ⬜ Glitch-Baukasten:
  - Pixel-Sortierung als Funktion
  - Kanalverschiebung, Slit-Scan
  - JPEG- und Daten-Glitch, Datamosh
- ⬜ „Pixel-Noise-Malerei“
- ⬜ Kleinformat-Plots: Postkarte, A6, Visitenkarte; Presets für feine Stifte

### IV – Wissen & Ressourcen (r/generative-Wiki)

- ⬜ `docs/ressourcen.md`: kuratierte Lernliste (Bücher, Tutorials, Communities) mit Links
- ⬜ Werkzeug-Landkarte mit Brücken zu plotart, über OSC, Dateien oder Vorlagen:
  - Processing, openFrameworks, Nannou (Rust), Three.js
  - Houdini
  - SuperCollider, TidalCycles, VCV Rack

### V – Morphogenese (nach jasonwebb/morphogenesis-resources)

Schon vorhanden: DLA, Differential Growth, L-Systeme, Reaktion-Diffusion, Space Colonization, Zellautomaten, Boids, Verlet/Stoff, Delaunay/Voronoi, Lloyd, Marching Squares, WFC, Flow Fields.

- ⬜ **Wachstum:**
  - Dielectric Breakdown (Lichtenberg-Figuren)
  - Eden-Wachstum
  - Particle Life
  - Primordial Particle System
  - Physarum
  - Spinodale Entmischung (Cahn-Hilliard)
- ⬜ **Kontinuierliche Automaten:** Lenia, SmoothLife
- ⬜ **Mathe & Physik:**
  - Phyllotaxis (goldener Winkel)
  - Fourier-Reihen
  - Chladni-Figuren (Cymatik)
  - Metaballs und Signed Distance Fields
  - Perkolation
  - Kinematik (Arme, Ketten, Tentakel)
  - Medial-Achse (Skelett einer Form)
- ⬜ **Code-Muster:**
  - gewichtetes Voronoi-Stippling
  - Fluid-Simulation
  - Soft-Body-Physik
  - Polygon-Clipping und CSG
  - Kollisionen, Metaballs
- ⬜ **3D-Morphogenese:**
  - Marching Cubes (Isoflächen)
  - Laplace-Glättung von Meshes
  - Polyeder und Conway-Operatoren
  - Geodätische Kuppeln
  - Minimalflächen
- ⬜ Lern-Abschnitt in `docs/ressourcen.md` mit den Original-Papers und Links

### VI – Processing-Bibliotheken als plotart-Gegenstücke

Ziel: Was diese Bibliotheken in Processing können, soll es in plotart auch geben, mit ähnlicher Bedienung.

- ⬜ **Geomerative** (Schrift und Vektorformen):
  - Schrift-Konturen in Punkte und Segmente zerlegen, gleichmäßig neu abtasten
  - Punkte auf Pfaden, Pfade teilen
  - Formen aus SVG verändern
  - „Caligraft“-artige wachsende Schrift
- ⬜ **toxiclibs:**
  - *verletphysics:* 3D-Physik, Verhalten (Anziehung, Schwerkraft-Zonen), Federnetze
  - *geom:* Meshes, Unterteilung, Splines, Wellen-Generatoren
  - *volumeutils:* Voxel, Isoflächen
  - *colorutils:* Farbharmonien, Farbtheorie, Sortieren, Farblisten-Strategien
- ⬜ **HE_Mesh:** Mesh-Modellierung mit Unterteilen, Extrudieren, Gittern und Conway-Operatoren; Export als GLB/OBJ
- ⬜ **HYPE:**
  - Layouts: Raster, Kreis, Schwarm, Form
  - Oszillatoren, Farb-Pools
  - Tweens und Proxy-Objekte
- ⬜ **Weitere:**
  - Box2D (Starrkörper-Physik)
  - Mesh (Lee Byron: Voronoi, Delaunay, Hülle)
  - Ani (Tweening)
  - PostFX (Nachbearbeitung, gibt es schon über Shader)
- ✅ Schon abgedeckt:
  - PeasyCam → `orbit_control()`
  - ControlP5 → `param()`-Regler
  - Minim/Sound → `load_audio()`
- ⬜ Spickzettel „Von Processing zu plotart“: welche Bibliotheksfunktion welcher plotart-Funktion entspricht

### Offene Fragen

- ⬜ Zwei Reddit-Beiträge (r/generative) konnten nicht geöffnet werden. Beschreibung oder Screenshot nötig, um sie gezielt umzusetzen.

## ⬜ Website-Anbindung (eigene Website des Künstlers)

- 🔨 Serien und Favoriten als **Galerie-Paket** exportieren:
  - ✅ Serie mit `galerie.html`, `edition.json` und Metadaten je Werk (Titel, Konzept-Text, Seed, Merkmale) – Block D
  - ⬜ Bilder zusätzlich in Web-Größe (Vorschaubilder), Datum
  - ⬜ Favoriten als Galerie-Paket
- ⬜ **Einbettbare Werke:** Web-Seite einer Skizze als `<iframe>`-Schnipsel zum Kopieren
- ⬜ **Automatisch veröffentlichen**, je nach Plattform:
  - GitHub Pages / Netlify: per Git-Push
  - WordPress: über die REST-API
  - sonst: ZIP zum Hochladen

## ⬜ A – Plotter zu Ende denken

- ⬜ Direkt plotten aus dem Studio (AxiDraw, iDraw, GRBL):
  - Start, Pause, Fortsetzen
  - Stiftwechsel pro Farbe
  - Zeitschätzung pro Ebene
- ⬜ Plot-Simulation: Vorschau Strich für Strich, inklusive Leerfahrten
- ⬜ Flächen automatisch füllen: Schraffur, Kreuzschraffur, Spirale, Stippling (pro Farbe einstellbar)
- ⬜ Einstrich-Schriften (Hershey) für Text

## ⬜ C – KI-Assistent im Studio (Claude)

- ⬜ „Beschreib, was du willst“ → Skizze schreiben oder ändern
- ⬜ Fehler erklären lassen, Varianten vorschlagen, Code kommentieren
- ⬜ KI-Kurator: aus vielen Seeds die stärksten auswählen

## ✅ D – Editionen & Präsentation (Version 1.13.0, Beispiele 62–63)

- ✅ Editionen wie bei Art Blocks und fxhash: `feature()`, Seltenheiten im Studio („Merkmale → Seltenheit prüfen“), Metadaten je Werk (`metadata/<seed>.json`, `edition.json`)
- ✅ Galerie-Seite einer Serie: `galerie.html` mit Filtern, Sortierung nach Seltenheit, Detailansicht
- ✅ Großformat-Druck: auf mehrere Blätter aufteilen (`tiles.py`, Studio „Großformat drucken“, `--tiles`), mit Schnittmarken, Klebe-Markierungen, PDF, SVG und Übersicht

## ✅ E – Live-Auftritt & VJ (Version 1.12.0, Beispiele 60–61)

- ✅ Vollbild-Ausgabe auf einem zweiten Bildschirm oder Beamer: `ausgabe.html` (📺 Ausgabe), scharf in voller Auflösung, Vollbild auf dem anderen Bildschirm per Window-Management-API
- ✅ Live-Coding ohne Neustart: `Animation.hot_swap()`, Zustand bleibt, Tippfehler halten nichts an
- ✅ Takt-Sync: `tempo()`, `bpm`, `beat`, `beat_phase`, `bar`, `on_beat()`, `beat_pulse()`; Tap-Tempo im Studio; Ableton Link über `plotart/tempo.py`
- ✅ Video an andere Programme: NDI und Spout (`plotart/videoout.py`)
- ⬜ Syphon (macOS) – fehlt noch, ohne Mac nicht testbar
- ⬜ Spout unter Python 3.14 – sobald es SpoutGL-Pakete dafür gibt

## ⬜ F – Neue Eingaben

- ⬜ Webcam als Bildquelle, auch live
- ⬜ Körper- und Hand-Tracking
- ⬜ Sensoren über Arduino (seriell)
- ⬜ Live-Daten: Wetter, Uhrzeit, APIs

## ⬜ G – Weitere Ausgabemaschinen

- ⬜ Laser-Cutter und Schneideplotter (SVG mit Schneid- und Gravurfarben)
- ⬜ Stickmaschine (DST/PES)
- ⬜ CNC (G-Code)
- ⬜ 3D-Druck (STL aus 3D-Formen und Reliefs)

## ⬜ H – Lernen im Studio

- ⬜ Eingebauter Kurs: 15 bis 20 Lektionen mit Aufgaben, vom ersten Kreis bis zum Shader

## ⬜ Stufe 9 – Desktop-App

- ⬜ Eigenes Programmfenster
- ⬜ Installer für Windows und macOS; bringt Python, Pillow, numpy, ffmpeg und moderngl mit
- ⬜ Dateien per Doppelklick öffnen, zuletzt geöffnete Skizzen

## ✅ Erledigt

- Stufe 1: Skizzen-Sprache und Studio
- Stufe 2: Animation
- Stufe 3: Blender
- Stufe 4: Bilder & Daten
- Stufe 5: Pixel & Filter
- Stufe 6: Kuration
- Stufe 7: Ton & Interaktion
- Stufe 8: 3D
- Stufe 10: GPU-Shader
- **B – Algorithmen-Baukasten:**
  - Wachstum: Differential Growth, DLA, Space Colonization
  - Simulation: Verlet-Physik, Boids, Zellautomaten, Game of Life, Reaktion-Diffusion
  - Muster: Wave Function Collapse, Truchet, Delaunay, TSP, Höhenlinien, Stromlinien, L-Systeme, Kreispackung
  - 15 Beispiele (36–50)
- **II – Mathe-Kunst** (siehe oben), 9 Beispiele (51–59)
- Weitere Bausteine:
  - OSC/TouchDesigner
  - Algorithmic-Art-Workflow
  - Web-Seiten-Export
  - shapely-Geometrie
