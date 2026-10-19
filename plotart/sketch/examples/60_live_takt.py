"""Live: Visuals im Takt"""
# Für Auftritte: bpm, beat, beat_phase und bar kommen aus tempo() – oder live aus dem Studio
# (🎮 Interaktiv → Takt: Tap oder Ableton Link). on_beat() läuft bei jedem Schlag,
# beat_pulse() blitzt auf dem Schlag auf und klingt bis zum nächsten ab.
# Für den Beamer: 📺 Ausgabe öffnen und dort mit F ins Vollbild.
size(1280, 720)
bpm_skizze = param("Tempo (BPM)", 120, 60, 180)
tempo(bpm_skizze)
animation(frames=round(16 * 60 / bpm_skizze * 30), fps=30)      # genau 16 Schläge → nahtloser Loop

ringe = param("Ringe", 12, 3, 30)
pal = palette(param("Palette", "neon", options=palettes()))
farbe = 1
ecken = 3


def on_beat(n):
    global farbe, ecken
    farbe = 1 + n % (len(pal) - 1)
    if n % 4 == 0:                                   # jeder Taktanfang: neue Form
        ecken = 3 + (n // 4) % 4


def draw():
    background(pal[0])
    translate(width / 2, height / 2)
    rotate(TAU * beat / 16)                          # eine Umdrehung in 16 Schlägen
    no_fill()
    puls = beat_pulse(5)
    for i in range(ringe):
        k = i / ringe
        stroke(pal[1 + (farbe + i) % (len(pal) - 1)])
        stroke_weight(1.5 + 9 * puls * (1 - k))
        r = 40 + k * 330 + 40 * puls * sin(TAU * (k + beat_phase))
        polygon([(r * cos(TAU * j / ecken + k), r * sin(TAU * j / ecken + k)) for j in range(ecken)])
