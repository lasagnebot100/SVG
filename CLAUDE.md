# CLAUDE.md – Übergabe für neue Sitzungen

plotart ist ein Werkzeug für **generative und algorithmische Kunst** in Python. Es bietet:
- eine p5.js-artige Skizzen-Sprache und ein Live-Studio im Browser,
- Export als PNG, SVG, Video, 3D, Blender und Web-Seite,
- Plotter-Export als Zusatz-Feature.

Version 1.11.0. Die To-do-Liste steht in **`docs/ROADMAP.md`**, die Funktionsübersicht in **`README.md`**.

## Vorgaben des Nutzers (immer einhalten)

- **Sprache:**
  - Deutsch mit österreichischen Begriffen, z. B. „Jänner“ statt „Januar“.
  - Penible Rechtschreibung und Grammatik.
  - Direkter, ruhiger Ton auf Augenhöhe.
- **Form:**
  - Antworten klar gegliedert: Überschriften, Aufzählungen, Fettdruck.
  - Keine Textwüsten.
- **Quellen:** Bei Fakten und Rechercheergebnissen immer Quellen mit Links angeben.
- **Bei Code:**
  - Vor jeder Änderung ansagen, welche Datei bearbeitet oder neu angelegt wird und wo.
  - Bestehenden Code nie versehentlich überschreiben, sondern nachvollziehbar erweitern.
- **Schwerpunkt:**
  - Die Desktop-Version zuerst.
  - Plotter nur als Nebenfeature.
- **Vor größeren neuen Blöcken** kurz den Plan nennen und die Reihenfolge abstimmen.
- **Rechner:** Der Nutzer arbeitet unter **Windows (PowerShell)**. Befehle für ihn immer einzeln, Zeile für Zeile angeben.

## Git

- Arbeits-Branch: `claude/svg-plotter-art-generator-4fkngt`; ein PR wurde noch nicht erstellt.
- Commit-Nachrichten auf Deutsch, kurz und mit Aufzählung der Änderungen.
- Nach dem Push den GitHub-Actions-Lauf prüfen (`.github/workflows/pages.yml`):
  - Jobs: build, compat 3.11/3.13 (mit Mesa-OpenGL für Shader-Tests), blender, deploy.

## Befehle

```bash
pip install -e ".[full]"                    # Pillow, numpy, imageio-ffmpeg, shapely, moderngl
plotart                                     # Studio auf http://localhost:8765
plotart sketch 44 --png                     # Beispiel rendern → output/
python -m unittest discover -s tests        # alle Tests (Blender-Tests nur mit bpy)
python tools/build_web.py --out site        # Browser-Version (Pyodide)
```

## Architektur (Kurzfassung)

- **`plotart/sketch/`** – die Skizzen-Sprache:
  - `core.py`: Klasse `Sketch` mit dem `@api`-Dekorator und den Kategorien in `CATEGORIES`
  - `runner.py`: Ausführung, Namensraum, camelCase-Aliase
  - `animation.py`: `setup()`/`draw()`, Live-Eingaben, Aufnahme
  - `render_svg.py`, `export.py`: Renderer und Exporte, PNG über Pillow
  - `tools.py`: Helfer, registriert mit `@tool(kategorie, needs_rng)`
  - `algorithms/`: growth.py, simulation.py, patterns.py
  - `three.py` (3D), `shader.py` (GLSL über moderngl bzw. WebGL2), `audio.py`, `occlusion.py` (verdeckte Linien), `geometry2d.py` (Schraffur, shapely)
  - `examples/01–50`: die Beispiel-Skizzen; der Docstring ist das „Konzept“, seine erste Zeile der Titel
- **`plotart/bridge.py`:** gemeinsame JSON-Befehle für Server, Worker-Prozess und Pyodide. Befehle mit Nutzer-Code gehören in `USER_CODE_COMMANDS`.
- **`plotart/web.py`:** lokaler Server mit Skizzen-Worker-Prozess, Export-Jobs, OSC und SSE.
- **`plotart/static/studio.html`:** das gesamte Studio in einer Datei, mit CodeMirror 5.
- **Weitere Module:**
  - `plotart/blender/`: Brücke zu Blender
  - `plotart/touchdesigner/`: Script-TOP-Renderer
  - `plotart/osc.py`: OSC über UDP
  - `plotart/viewer.py`: Web-Seiten-Export

## Regeln im Code

- **Kern in reinem Python:**
  - Optionale Pakete (Pillow, numpy, shapely, moderngl, scipy) nur bei Bedarf importieren.
  - Fehlt ein Paket, eine freundliche deutsche Fehlermeldung mit dem Installationsbefehl ausgeben.
- **Python 3.11 kompatibel bleiben**, denn Blender und TouchDesigner nutzen 3.11.
- **Zufall immer über `sk.rng`** bzw. `needs_rng=True`, damit derselbe Seed dasselbe Bild ergibt.
- **Namen und Texte:** Texte für Nutzer und Funktionsbeschreibungen auf Deutsch; die API-Namen auf Englisch (snake_case).
- **Neue Funktionen bekommen immer:**
  - eine Beispiel-Skizze (fortlaufende Nummer, also als Nächstes 60),
  - Tests in `tests/`,
  - einen Eintrag im README.
- **Browser-Version:** Braucht eine neue Funktion ein Pyodide-Paket (numpy, shapely, Pillow), die Erkennung in `tools/build_web.py` und `plotart/viewer.py` ergänzen.
- **Studio-CSS:** `[hidden]{display:none!important}` ist gesetzt, deshalb Elemente mit `el.hidden` ein- und ausblenden.

## Offene Punkte (Stand 19. Oktober 2026)

- **Reihenfolge abgestimmt** (19. Oktober 2026), jeweils als eigener Block mit Version, Beispielen, Tests, README:
  1. ✅ II – Mathe-Kunst (1.11.0)
  2. E – Live/VJ: Ausgabefenster für den Beamer, Live-Coding ohne Neustart, Takt-Sync, Spout (Windows) zuerst
  3. D – Editionen: Merkmale und Seltenheiten, Editions-Export, Galerie-Seite, Großformat in Kacheln
  4. I – Mehrsprachen-Studio: p5.js, Processing (Konverter und Ausführung), React-Vorlagen, dann R und Kotlin
  5. C – KI-Assistent: wartet auf die Entscheidung des Nutzers zum (kostenpflichtigen) Anthropic-API-Schlüssel
- **Werkzeuge am Rechner des Nutzers:** R, Java und Processing hat er nach eigener Aussage installiert; vor Block I prüfen (`Rscript`, `java`, `processing-java`). Node ist vorhanden, aber über nvm nicht aktiviert.
- **III, V, VI** (weitere Algorithmen, Morphogenese, Processing-Bibliotheken) sind noch nicht eingeplant.
- **Zwei Reddit-Beiträge** aus r/generative waren in der Cloud nicht abrufbar. Der Nutzer soll sie beschreiben oder einen Screenshot schicken.
- **Website-Plattform** des Nutzers noch unbekannt; sie entscheidet über die Website-Anbindung und die React-Komponente.
- **Stufe 9 (Desktop-App mit Installer)** kommt bewusst später.
