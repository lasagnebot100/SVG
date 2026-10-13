# plotart – To-do-Liste

Leitlinie: plotart ist in erster Linie ein Werkzeug für **generative und algorithmische Kunst**. Plotter-Funktionen sind ein schönes Zusatz-Feature.

Legende: ✅ erledigt · 🔨 in Arbeit · ⬜ geplant

## ⬜ Neue Wünsche (Oktober 2026) – noch nicht begonnen, Reihenfolge wird abgestimmt

### I – Mehrere Sprachen im Studio („Mehrsprachen-Studio“)

Gemeinsam für alle Sprachen: Seed, Regler (`param`), Varianten, Favoriten, Export (PNG/SVG/Video) und Web-Seite bleiben gleich.

- ⬜ **p5.js / JavaScript-Modus:** Skizzen in p5.js schreiben; sie laufen direkt im Browser, auch am iPad.
- ⬜ **Processing (Java, `.pde`):**
  - Sketches über `processing-java` ausführen, sofern Processing installiert ist
  - Bilder und Animationen ins Studio holen
  - Konverter einfacher Processing-Sketches nach plotart-Python
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

### II – Mathe-Kunst

- ⬜ **Numerische Integration als Bild und Animation:**
  - Riemann-Summen, Mittelpunkt-, Trapez- und Simpson-Regel
  - Fehlerflächen und Konvergenz
  - dazu ein Funktions-Plotter für beliebige Formeln
- ⬜ **Kurven-Baukasten:** Lissajous, Rosen, Harmonograph, Spirograph, Superformel, Fourier-Epizykel (Zeichnung → Kreise)
- ⬜ **Differentialgleichungen:** RK4-Löser, Phasenporträts, seltsame Attraktoren als Funktionen
- ⬜ **Fraktale:**
  - Mandelbrot- und Julia-Mengen (auch als Shader)
  - IFS und Fractal Flames
  - Newton-Fraktale
- ⬜ **Komplexe Funktionen:** Domain Coloring

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

### Offene Fragen

- ⬜ Zwei Reddit-Beiträge (r/generative) konnten nicht geöffnet werden. Beschreibung oder Screenshot nötig, um sie gezielt umzusetzen.

## ⬜ Website-Anbindung (eigene Website des Künstlers)

- ⬜ Serien und Favoriten als **Galerie-Paket** exportieren:
  - Bilder in Web-Größe und Originalgröße
  - Titel, Konzept-Text, Seed, Datum
  - `galerie.json` für die Website
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

## ⬜ D – Editionen & Präsentation

- ⬜ Editionen wie bei Art Blocks und fxhash: `feature("Palette", name)`, Seltenheiten, Metadaten
- ⬜ Galerie-Seite einer Serie (siehe Website-Anbindung)
- ⬜ Großformat-Druck: auf mehrere Blätter aufteilen

## ⬜ E – Live-Auftritt & VJ

- ⬜ Vollbild-Ausgabe auf einem zweiten Bildschirm oder Beamer
- ⬜ Live-Coding ohne Neustart (der Zustand der Animation bleibt erhalten)
- ⬜ Takt-Sync: Ableton Link, Tap-Tempo
- ⬜ Video an andere Programme: Spout (Windows), Syphon (macOS), NDI

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
- Weitere Bausteine:
  - OSC/TouchDesigner
  - Algorithmic-Art-Workflow
  - Web-Seiten-Export
  - shapely-Geometrie
