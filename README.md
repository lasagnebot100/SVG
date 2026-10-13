# plotart – generative Kunst mit Python

Ein Werkzeug, um **generative und algorithmische Kunst in Python** zu erschaffen. Du schreibst Skizzen in einer Sprache **im Stil von p5.js/Processing** und siehst das Ergebnis sofort. Standbilder oder **Animationen**, Ausgabe als **PNG, SVG, MP4, GIF oder plotterfertige Linien**. Gemacht für den Computer, läuft aber auch im Browser und am iPad.

![Skizzen-Beispiele](examples/skizzen.jpg)

## Highlights

- **Skizzen-Sprache wie p5.js:** `size()`, `background()`, `fill()`, `circle()`, `begin_shape()`, `push()`/`pop()`, `translate()`, `rotate()`, `noise()`, `random()` …
- **Live-Studio im Browser:** Code-Editor mit Syntax-Hervorhebung und Autovervollständigung, Vorschau bei jeder Änderung, Fehler mit Zeilennummer, durchsuchbare API-Hilfe
- **Regler automatisch:** `n = param("Anzahl", 40, 1, 200)` erzeugt einen Schieberegler
- **Volle Python-Power:** numpy, scipy, Pillow und jede andere installierte Bibliothek; Rasterbilder per `image(array)`
- **Farbe ernst genommen:** Transparenz, HSB, Verläufe (linear/radial), Mischmodi (Multiply, Screen, …), 16 kuratierte Paletten
- **Werkzeugkasten für generative Kunst:** Voronoi, Poisson-Disc, Lloyd-Relaxation, Chaikin-Glättung, Schraffur, Vektoren
- **Animation wie in p5.js:** `setup()` und `draw()`, Zustand über Bilder hinweg, Spuren durch halbtransparenten Hintergrund, `t` für nahtlose Loops, Easing-Funktionen
- **Zeitleiste im Studio:** Abspielen, Spulen, Bild für Bild, Geschwindigkeit
- **Exporte:** Farb-SVG, PNG in jeder Auflösung (z. B. 300 dpi), **MP4, WebM, GIF, PNG-Sequenz**, **Plotter-SVG** (optimierte Linien, eine Ebene pro Farbe)
- **Desktop-Arbeitsweise:** Skizzen im Ordner `skizzen/`, Speichern mit Strg+S; bearbeitest du die Datei in VS Code o. Ä., aktualisiert sich das Studio automatisch
- **Blender-Anbindung:** Skizzen als Blender-Objekte (Flächen, Linien als Bänder oder 3D-Röhren, Text, Bilder), **Relief-Modus** für 3D-Skulpturen, Animationen auf der Zeitleiste, Add-on mit Reglern und automatischem Neuladen
- **Bilder & Daten:** Fotos laden und Pixel abfragen (Stippling, Schraffur …), CSV/JSON (auch mit Dezimalkomma), SVG-Import, **Text als Pfade** aus TrueType-Schriften
- **Pixel & Filter:** `pixels` als numpy-Array, 16 Filter (Weichzeichnen, Körnung, Dithering …), `filter()` auf die ganze Leinwand, `snapshot()` für Feedback-Effekte
- **Kuration:** Varianten-Raster, Favoriten mit Vorschaubild, Versionsverlauf, Serien-Export mit Kontaktbogen, Regler-Keyframes für Animationen
- **24 Beispiel-Skizzen** zum Lernen und Weiterbauen
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

Optional: `pip install -e ".[full]"` installiert Pillow, numpy und imageio-ffmpeg (für Videos) sowie den Befehl `plotart`.

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

## Animation

![Animation](examples/animation.gif)

Sobald eine Skizze `draw()` definiert, wird sie zur Animation. `draw()` läuft dann für jedes Bild.

```python
size(800, 800)
animation(frames=180, fps=30)          # 6 Sekunden

def draw():
    background("#0f1020")              # jedes Bild frisch – ohne background() malt es weiter
    no_stroke()
    for i in range(12):
        a = TAU * (t + i / 12)         # t läuft von 0 bis 1 → nahtloser Loop
        fill(hsb(i * 30, 70, 100))
        circle(width / 2 + cos(a) * 250, height / 2 + sin(a) * 250, 60)
```

| Was | Wie |
|---|---|
| Länge & Tempo | `animation(frames=240, fps=30)` · `duration(8)` (Sekunden) · `frame_rate(24)` |
| Zeit | `t` (0 … 1 über die ganze Animation) · `frame_count` (1, 2, 3 …) · `time` (Sekunden) · `frames`, `fps` |
| Zustand | Variablen in `setup()` anlegen, in `draw()` verändern (mit `global` für einfache Werte) |
| Spuren | `background(0, 20)` – halbtransparent, ältere Bilder verblassen langsam |
| Wachsende Bilder | kein `background()` in `draw()` – jedes Bild malt auf das vorige weiter |
| Nahtlose Loops | alles nur von `t` abhängig machen · `loop_noise(x, y, t)` · `wave(t, cycles)` · `ping_pong(t)` |
| Easing | `ease_in()` · `ease_out()` · `ease_in_out()` · `ease_in_out_cubic()` · `ease_out_elastic()` |
| Standbild trotz `draw()` | `no_loop()` |

Wie in p5.js werden Transformationen vor jedem Bild zurückgesetzt, Farben und Stile bleiben erhalten.

**Im Studio:**
- Unter der Vorschau erscheint eine **Zeitleiste**: ▶/⏸ mit der Leertaste, Spulen mit dem Regler, ← → für einzelne Bilder.
- **Rechts unter „Animation exportieren“** wählst du Format (MP4, WebM, GIF, PNG-Sequenz), Auflösung, Bildanzahl und fps.
- Der Export läuft im Hintergrund mit Fortschrittsbalken und landet im Ordner `output/`.

MP4 und WebM brauchen **ffmpeg**: entweder installieren (https://ffmpeg.org/download.html) oder `pip install imageio-ffmpeg`. GIF und PNG-Sequenz funktionieren auch ohne ffmpeg.

## Bilder & Daten

![Bilder, Daten, Pixel](examples/bilder_daten.jpg)

Dateien legst du in den Ordner `skizzen/daten/` (im Studio: Bereich **„Daten“**, „＋ Datei“ oder einfach auf die Vorschau ziehen). Ein Klick auf eine Datei fügt den passenden Befehl in den Code ein. Für erste Versuche gibt es eingebaute Beispiele: `"beispiel:portrait"`, `"beispiel:kugeln"`, `"beispiel:verlauf"`, `"beispiel:schrift"`, `"beispiel:temperaturen.csv"`, `"beispiel:zufall.json"`, `"beispiel:gedicht.txt"`.

```python
img = load_image("foto.jpg")                  # aus skizzen/daten/
img.brightness(x, y)                          # 0 (schwarz) … 1 (weiß)
img.get(x, y)                                 # Farbe des Pixels
img.grid(40)                                  # mittlere Helligkeit pro Rasterzelle
image(img.filter(BLUR, 3), 0, 0, width, height)

rows = load_csv("messwerte.csv")              # Liste von Dicts, 12,5 → 12.5
svg = load_svg("logo.svg"); draw_svg(svg, 100, 100, w=300)
umrisse = text_paths("Hallo", 50, 200, 120, font="DejaVuSans-Bold")   # Buchstaben als Punktlisten
text_shape("Hallo", 50, 200, 120)             # Text als echte Form (Plotter, Blender)
```

| Funktion | Zweck |
|---|---|
| `load_image(pfad)` | Bild laden → `.width`, `.height`, `.get()`, `.brightness()`, `.sample(u, v)`, `.grid()`, `.pixels`, `.resize()`, `.crop()`, `.rotate()`, `.filter()`, `.dither()` |
| `load_csv` · `load_json` · `load_text` · `load_lines` | Daten laden (CSV erkennt `;`, `,`, Tab und Dezimalkomma) |
| `load_svg` · `draw_svg` | SVG-Grafiken als Punktlisten importieren und zeichnen |
| `text_paths` · `text_shape` | Text als Umrisse (TrueType-Schriften des Systems oder eigene `.ttf` aus `daten/`) |

## Pixel & Filter

| Funktion | Zweck |
|---|---|
| `create_image(w, h)` | Leeres Bild für Pixel-Algorithmen |
| `img.pixels` / `img.set_pixels(arr)` | Pixel als numpy-Array H × W × 4 (0 … 1) lesen und schreiben |
| `img.filter(art, stärke)` | `BLUR`, `SHARPEN`, `EDGES`, `EMBOSS`, `GRAY`, `INVERT`, `POSTERIZE`, `THRESHOLD`, `CONTRAST`, `BRIGHTNESS`, `SATURATION`, `PIXELATE`, `GRAIN`, `DITHER`, `SEPIA`, `LEVELS` |
| `filter(art, stärke)` | Filter auf die ganze Leinwand (wie in p5) |
| `snapshot()` | Bisher Gezeichnetes als Bild – im nächsten Animationsbild wieder zeichnen = Feedback-Effekte (Beispiel 22) |

`filter(funktion, liste)` funktioniert weiterhin wie Pythons eingebautes `filter`.

## Kuration & Serien

- **🔲 Varianten** (Taste V): Das Studio rendert 9, 16 oder 25 Seeds als Vorschau. Mit „Regler auch würfeln“ werden auch die Regler zufällig gewählt. Ein Klick übernimmt die Variante.
- **★ Favoriten** (Taste F): Seed, Regler und Keyframes werden mit Vorschaubild und Notiz gespeichert. Bei gespeicherten Skizzen landen sie in `skizzen/.plotart/<name>.json`, wandern also mit der Datei mit.
- **🕘 Verlauf:** Jedes Speichern archiviert die vorige Fassung (die letzten 50) in `skizzen/.plotart/verlauf/`. Ältere Fassungen lassen sich mit einem Klick laden.
- **🗂 Serie exportieren:** Viele Seeds auf einmal als PNG, SVG und/oder Plotter-SVG, mit **Kontaktbogen** und `serie.json`. Per Kommandozeile: `python3 -m plotart sketch 06 -n 24 --sheet --png`.
- **◆ Regler-Keyframes** (Animationen): Bild wählen, Regler einstellen, ◆ klicken – zwischen den Keyframes wird weich übergeblendet. Das wirkt für alle `param()`, die in `draw()` abgefragt werden; es gilt auch für Video- und Blender-Export.

## Am Computer arbeiten

- **Skizzen-Ordner:** Oben links unter **„📁 Meine Skizzen“** liegen deine Dateien aus `./skizzen/` (anderer Ordner: `python3 -m plotart --ordner pfad`). Dort gibt es auch „Neue Skizze“, „Neue Animation“ und „Speichern unter“.
- **Speichern:** **Strg/⌘ + S** speichert, **Umschalt + Strg/⌘ + S** speichert unter neuem Namen. Ein ● zeigt ungespeicherte Änderungen.
- **Eigener Editor:** Öffne die `.py`-Datei zusätzlich in VS Code, PyCharm & Co. Jede Änderung, die du dort speicherst, erscheint sofort im Studio.
- **Sicherheit:** Skizzen laufen in einem eigenen Prozess. Endlosschleifen werden nach 30 s abgebrochen (`--timeout`).

| Kürzel | Funktion |
|---|---|
| Strg/⌘ + Enter | Ausführen |
| Strg/⌘ + Umschalt + Enter | Neuer Seed |
| Strg/⌘ + S / + Umschalt | Speichern / Speichern unter |
| Strg/⌘ + O | Skizzen-Liste öffnen |
| Strg/⌘ + / | Zeile auskommentieren |
| Strg + Leertaste | Autovervollständigung |
| Leertaste · ← → · Pos1 | Animation: Play/Pause · Bild zurück/vor · zum Anfang |
| V · F | Varianten-Raster · als Favorit merken |
| F1 | Hilfe |

## Blender

![Von der Skizze zur 3D-Szene](examples/blender.jpg)

plotart bringt deine Skizzen nach Blender (ab Version 4.2). Das geht auf drei Wegen.

**1. Add-on mit Live-Verbindung (empfohlen)**

1. Add-on bauen: im Studio rechts **„⬇ Blender-Add-on (ZIP)“** oder `python3 -m plotart blender-addon`.
2. In Blender: **Bearbeiten › Einstellungen › Erweiterungen › ▾ (oben rechts) › „Von Datenträger installieren …“** → ZIP wählen.
3. Im 3D-Viewport die Seitenleiste öffnen (**Taste N**) → Reiter **„plotart“**.
4. Skizzen-Datei wählen (z. B. aus `skizzen/`) oder ein Beispiel → **„Importieren / Aktualisieren“**.
5. Mit **„Automatisch neu laden“** baut Blender die Szene neu, sobald du die Skizze im Studio (💾) oder in VS Code speicherst.

Die Regler aus `param()` erscheinen auch in Blender.

**2. Im Studio:** rechts unter **„Blender“** Relief, Linien, Kamera und Material wählen und **„🧊 Als .blend erzeugen“** klicken. Das braucht ein installiertes Blender.

**3. Kommandozeile:**

```bash
python3 -m plotart sketch 18 --blend stadt.blend --relief brightness --relief-height 2.5 --camera perspective --material physical
python3 -m plotart sketch 14 --blend spuren.blend --render frames/bild_####.png --engine CYCLES   # Animation rendern
```

| Option | Wirkung |
|---|---|
| Linien: Flach / Röhren | flache Bänder wie in 2D oder runde 3D-Röhren |
| Material: Flach / Physikalisch | leuchtende Farben exakt wie im 2D-Bild oder Material, das auf Licht und Schatten reagiert |
| Relief: Aus / Gleich hoch / Nach Reihenfolge / Nach Helligkeit | Flächen werden zu 3D-Körpern; Höhe frei wählbar |
| Kamera: Draufsicht / Perspektive | orthografisch exakt wie das Bild oder schräg von vorne |
| Animation: Ganze Animation / Ein Bild | jedes Bild auf der Zeitleiste (Sichtbarkeits-Keyframes, Spuren inklusive) oder ein einzelnes Bild |

**Blender finden:** plotart sucht im `PATH`, in den üblichen Installationsordnern und in der Umgebungsvariable `PLOTART_BLENDER`. Alternativ kann Blender als Python-Modul installiert werden: `pip install bpy`, nur für die passende Python-Version.

**Grenzen:**
- Verläufe werden zur Durchschnittsfarbe.
- Mischmodi (Multiply …) gibt es in Blender nicht.
- Halbtransparente Formen sind in Eevee nicht immer korrekt sortiert; Cycles rendert sie exakt.
- Skizzen laufen in Blender ohne Zeitlimit. Eine Endlosschleife friert Blender ein.

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
| 13 | Animation: Loop-Kreise | Nahtloser Loop über `t`, `wave()` |
| 14 | Animation: Partikel-Spuren | Zustand in `setup()`/`draw()`, Spuren durch halbtransparenten Hintergrund |
| 15 | Animation: Wellen-Loop | `loop_noise()` für organische, nahtlose Bewegung |
| 16 | Animation: Wachsendes Bild | Ohne `background()` – die Zeichnung entsteht Strich für Strich |
| 17 | Animation: Kinetische Typografie | Easing, `ping_pong()`, Versatz pro Zeile |
| 18 | Relief-Stadt | gedacht für Blender: Helligkeit wird zur Höhe |
| 19 | Bild: Stippling | `load_image()`, Helligkeit → Punktdichte |
| 20 | Bild: Wellen-Schraffur | ein Bild als plotterfreundliche Wellenlinien |
| 21 | Daten: Jahreskreis | `load_csv()` mit Dezimalkomma, radiale Darstellung |
| 22 | Animation: Feedback-Tunnel | `snapshot()` + gedrehtes `image()` = Rückkopplung |
| 23 | Text als Pfade | `text_paths()`, verformt und schraffiert für den Plotter |
| 24 | Pixel-Sortierung | `img.pixels` mit numpy, Glitch-Effekt, Körnung |

Zu finden in `plotart/sketch/examples/`, im Studio unter „Beispiele …“, oder per Kommandozeile, z. B. `python3 -m plotart sketch 06 --png`.

## Exporte

| Export | Was | Hinweis |
|---|---|---|
| **SVG** | Vektorgrafik mit Farben, Verläufen, Transparenz | Für Illustrator, Inkscape, Web |
| **PNG** | Rasterbild in wählbarer Auflösung | Bei `size("A3")` z. B. 300 dpi für den Druck |
| **Plotter** | Nur Linien in mm, optimiert, eine Ebene pro Farbe | Für AxiDraw, iDraw, vpype; Flächen werden als Umriss gezeichnet |
| **MP4 / WebM** | Video der Animation | braucht ffmpeg |
| **GIF** | Animation als GIF (Endlosschleife) | mit ffmpeg optimierte Farbpalette, sonst Pillow |
| **PNG-Sequenz** | Jedes Bild als PNG mit Transparenz, als ZIP | Zum Weiterbearbeiten in After Effects, Blender & Co. |
| **.py** | Die Skizze selbst | Mit 📂 wieder öffnen |

Überlappende Flächen werden beim Plotter-Export nicht ausgeblendet, weil ein Plotter alles zeichnet. Für Verdeckung (wie in Beispiel 11) eignen sich die fertigen Generatoren besser.

## Kommandozeile

```bash
python3 -m plotart                                   # Studio starten
python3 -m plotart sketch meine_skizze.py --png      # Skizze → output/meine_skizze_1.svg + .png
python3 -m plotart sketch 03 -s 42 -n 5 --png        # Beispiel 03, Seeds 42–46
python3 -m plotart sketch 06 -p "Zellgröße=30" --plotter --pen 0.3
python3 -m plotart sketch 05 -o druck.png --scale 23.6   # 600 dpi (Pixel pro mm)
python3 -m plotart sketch 14 --mp4 --gif             # Animation → output/14_partikel_spuren_1.mp4 + .gif
python3 -m plotart sketch anim.py --mp4 --frames 600 --fps 60 --scale 2   # 10 s, 60 fps, doppelte Auflösung
python3 -m plotart sketch anim.py --png-seq          # alle Bilder als PNG (ZIP)
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
│   ├── animation.py   Bild-für-Bild-Ausführung (setup/draw)
│   └── video.py       MP4/WebM/GIF/PNG-Sequenz-Export
├── blender/           Blender-Anbindung: Szene, Geometrie, Aufbau (bpy), Add-on, Paket
├── generators/        fertige Plotter-Generatoren
├── static/            Studio, Generator-Seite, Code-Editor (CodeMirror 5, MIT)
├── bridge.py          gemeinsame Schnittstelle für Server, Worker-Prozess und Browser
├── web.py             lokaler Server (Skizzen in eigenem Prozess mit Zeitlimit, Export-Jobs)
├── sketchfiles.py     Skizzen-Ordner (Speichern/Laden)
└── cli.py             Kommandozeile
tools/build_web.py     baut die Browser-Version (Pyodide)
```

## Ausblick

- ~~Stufe 2 – Animation~~ ✓
- ~~Stufe 3 – Blender~~ ✓
- ~~Stufe 4 – Bilder & Daten~~ ✓ · ~~Stufe 5 – Pixel & Filter~~ ✓ · ~~Stufe 6 – Kuration & Serien~~ ✓
- **Stufe 7 – Ton & Interaktion:** Audio-reaktive Animationen, Maus/Tastatur in der Vorschau, MIDI-Controller
- **Stufe 8 – 3D in der Skizze:** `box()`, `sphere()`, Kamera & Licht, glTF/OBJ-Export
- **Stufe 9 – Desktop-App:** eigenes Programmfenster mit Installer

## Tests

```bash
python3 -m unittest discover -s tests          # Blender-Tests laufen mit, wenn `bpy` installiert ist
```
