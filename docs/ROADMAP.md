# plotart – To-do-Liste

Leitlinie: plotart ist in erster Linie ein Werkzeug für **generative und algorithmische Kunst**. Plotter-Funktionen sind ein schönes Zusatz-Feature.

Legende: ✅ erledigt · 🔨 in Arbeit · ⬜ geplant

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
