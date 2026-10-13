# plotart und TouchDesigner

TouchDesigner (TD) ist eine knotenbasierte Echtzeit-Umgebung für Installationen, Projektionen und Live-Visuals. plotart ist codebasiert und auf Skizzen, Druck, Plotter und Video ausgerichtet. Beide ergänzen sich: **plotart erzeugt die Form, TouchDesigner spielt sie live aus** – oder umgekehrt.

## 1. Begriffe: TD-Operatoren ↔ plotart

| TouchDesigner | Was es ist | Gegenstück in plotart |
|---|---|---|
| **TOP** (Texture Operator) | Bilder/Texturen auf der GPU | gerendertes Bild einer Skizze (PNG, Video-Frame) |
| **CHOP** (Channel Operator) | Kanäle mit Zahlen über die Zeit (LFO, Audio, MIDI, OSC) | `param()`-Regler, `osc()`, `midi()`, `load_audio()` |
| **SOP** (Surface Operator) | 3D-Geometrie | `box()`, `sphere()`, `mesh()` → `.obj`/`.glb` |
| **DAT** (Data Operator) | Text, Tabellen, Python-Skripte | die Skizze selbst (`.py`), CSV/JSON über `load_csv()` |
| **COMP** | Container, 3D-Objekte, Bedienoberflächen | Studio mit Reglern |
| Timeline / `absTime.frame` | Zeit | `frame_count`, `t`, `time` |

## 2. Drei Wege der Zusammenarbeit

### A) Live per OSC (empfohlen zum Einstieg – nichts zu installieren)

Das Studio spricht **OSC** (Open Sound Control) über UDP, genau wie TD.

```bash
python -m plotart studio --osc-in 9000 --osc-out 127.0.0.1:9001
```

**TouchDesigner → plotart**
- **OSC Out CHOP** anlegen: Network Address `127.0.0.1`, Port `9000`.
- Kanal `td/level` wird zur Adresse `/td/level` und ist in der Skizze mit `osc("/td/level", 0)` lesbar.
- Sonderadressen steuern das Studio selbst:
  - `/param/<Reglername>` setzt einen Regler,
  - `/seed`, `/random`, `/play`, `/pause` und `/live 1` steuern Seed, Wiedergabe und Interaktiv-Modus.

**plotart → TouchDesigner**
- In der Skizze `osc_send("/plotart/x", wert)` aufrufen.
- In TD einen **OSC In CHOP** auf Port `9001` anlegen; für vollständige Nachrichten (auch Text) einen **OSC In DAT**.
- Gesendet wird im 🎮-Interaktiv-Modus, einmal pro Bild.

Beispiel: `31_osc_touchdesigner.py` (im Studio unter „Beispiele“).

### B) plotart als Textur in TouchDesigner (Script TOP)

TD bringt sein eigenes Python 3.11 samt numpy mit. Ein **Script TOP** kann in seinem `onCook()`-Callback ein numpy-Array als Bild ausgeben (`copyNumpyArray`, Form *Höhe × Breite × Kanäle*, uint8/uint16/float32). `plotart.touchdesigner.TDRenderer` liefert genau so ein Array – Bild für Bild, mit Animation, `osc()`-Werten aus einem CHOP und Maus.

1. **Pillow für Python 3.11 installieren** (plotart braucht es zum Rastern). Zum Beispiel in einen eigenen Ordner:
   ```bash
   py -3.11 -m pip install --target C:\td-python Pillow        # Windows
   python3.11 -m pip install --target ~/td-python Pillow       # macOS
   ```
   Diesen Ordner in TD unter **Edit › Preferences › Python 64-bit Module Path** eintragen.
2. **Callbacks-Datei erzeugen** – der Pfad zu plotart wird automatisch eingetragen:
   ```bash
   python -m plotart touchdesigner        # → output/plotart_script_top.py
   ```
3. **In TD einrichten:**
   - Einen **Script TOP** anlegen.
   - Dessen Callbacks-DAT (Text DAT) mit der Datei verknüpfen (Parameter *File*).
   - Auf der Parameter-Seite **plotart** die Skizze wählen.
4. **Arbeiten:** Speichern im Studio lädt die Skizze in TD neu.
   - Werte-CHOP (z. B. OSC In, Audio-Analyse, LFO) → `osc("/kanalname")`.
   - Maus-CHOP mit `u`, `v`, `select` (z. B. Panel CHOP) → `mouse_x`, `mouse_y`.

> **Ehrlicher Hinweis:** Die Callbacks-Vorlage ist gegen einen nachgebauten Script TOP getestet, **nicht in TouchDesigner selbst**.
> - Steht das Bild auf dem Kopf, den Schalter „Vertikal spiegeln“ umlegen.
> - Ruckelt es: Skalierung verkleinern. Das Rastern läuft auf der CPU – für 4K in Echtzeit ist plotart nicht gebaut.

### C) Dateiaustausch (am robustesten)

| Von plotart | Nach TD |
|---|---|
| PNG-Sequenz (ZIP) oder MP4 aus „Animation exportieren“ | **Movie File In TOP** |
| 3D-Formen als `.obj` (Studio: ⇧ + Knopf „3D“, CLI `--3d obj`) | **File In SOP** |
| 3D-Formen als `.glb` (Studio: Knopf „3D“) | Import in neueren TD-Builds; sicher in Blender, three.js |
| Plotter-SVG | als Vorlage (TD arbeitet nicht vektorbasiert) |
| CSV/JSON aus `daten/` | **Table DAT** / **File In DAT** |

Umgekehrt landen TD-Aufnahmen (Movie File Out TOP → PNG) in `skizzen/daten/` und sind dort mit `load_image()` nutzbar.

## 3. TouchDesigner lernen – ein Weg in vier Schritten

1. **Grundlagen (offiziell, gratis):**
   - Das *TouchDesigner Curriculum* von Derivative und SudoMagic: über 80 Einheiten mit kurzen Videos und Beispieldateien.
   - Start mit der „100 Series: Fundamentals“, danach die „200 Series“.
   - Links: [learn.derivative.ca – Ankündigung](https://derivative.ca/community-post/introducing-touchdesigner-curriculum/67560) · [Learning TouchDesigner](https://docs.derivative.ca/Learning_TouchDesigner)
2. **Erstes Projekt:** Ein Audio-reaktives Visual bauen.
   - Kette: **Audio Device In CHOP → Analyze CHOP → Noise TOP**.
   - Danach dasselbe mit plotart: `29_ton_spektrum.py` – dieselbe Idee in Code.
3. **Community-Kurse:** Die Derivative-Doku empfiehlt die Einsteiger-Playlists von *The Interactive & Immersive HQ* und *Bileam Tschepe (elekktronaut)* ([Tutorials-Übersicht](https://derivative.ca/UserGuide/Tutorials)).
4. **Python in TD:** Danach Script-Operatoren und numpy.
   - Lesestoff: [Script TOP](https://derivative.ca/UserGuide/Script_TOP) · [ScriptTOP Class (copyNumpyArray)](https://derivative.ca/UserGuide/ScriptTOP_Class) · [NumPy in TD](https://derivative.ca/UserGuide/NumPy)
   - Hier kommt Weg B ins Spiel.

**Faustregel:**
- Was **Echtzeit, GPU, Projektion, Sensoren** braucht → TouchDesigner.
- Was **reproduzierbar, druck-/plotterfertig, seed-basiert, versioniert** sein soll → plotart.

## Quellen

- Script TOP: https://derivative.ca/UserGuide/Script_TOP
- ScriptTOP Class (`copyNumpyArray`, nur in `onCook`, Form h × w × c, uint8/uint16/float32): https://derivative.ca/UserGuide/ScriptTOP_Class
- NumPy in TouchDesigner: https://derivative.ca/UserGuide/NumPy
- OSC In CHOP: https://derivative.ca/UserGuide/OSC_In_CHOP · OSC Out CHOP: https://derivative.ca/UserGuide/OSC_Out_CHOP
- TouchDesigner Curriculum: https://derivative.ca/community-post/introducing-touchdesigner-curriculum/67560
- OSC-1.0-Spezifikation: https://opensoundcontrol.stanford.edu/spec-1_0.html
