"""Live-Coding: Der Zustand bleibt"""
# Starte 🎮 Interaktiv und ändere den Code, während er läuft – etwa FARBE, GROESSE oder die
# Formel in bewegung(). Mit ♻ Live-Code bleiben die Teilchen, wo sie sind: Funktionen werden
# ausgetauscht, Variablen nur, wenn ihre Zeile (oder eine Zeile, von der sie abhängt) geändert
# wurde. setup() läuft nicht noch einmal – für eine neue ANZAHL also ↺ Neustart drücken.
# Ein Tippfehler hält nichts an: Die letzte funktionierende Fassung läuft weiter.
size(800, 800)
animation(frames=300, fps=30)

ANZAHL = 500
FARBE = "#f2c14e"
GROESSE = 3
WIRBEL = 2.0
teilchen = []


def setup():
    for _ in range(ANZAHL):
        teilchen.append([random(width), random(height)])


def bewegung(x, y):
    a = noise(x * 0.004, y * 0.004, frame_count * 0.004) * TAU * WIRBEL
    return cos(a) * 2, sin(a) * 2


def draw():
    background(10, 12, 30, 28)                      # halbtransparent: Spuren bleiben
    no_stroke()
    fill(FARBE)
    for p in teilchen:
        dx, dy = bewegung(p[0], p[1])
        p[0] = (p[0] + dx) % width
        p[1] = (p[1] + dy) % height
        circle(p[0], p[1], GROESSE)
