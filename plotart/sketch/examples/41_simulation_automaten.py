"""Simulation: Elementare Zellautomaten (Wolfram)"""
# Jede Zeile entsteht aus der vorigen nach einer von 256 Regeln (nur drei Nachbarn zählen).
# Regel 30 ist chaotisch, 90 ergibt Sierpinski-Dreiecke, 110 ist sogar „Turing-vollständig“.
size(800, 800)

regel = param("Regel", 30, 0, 255)
zellen = param("Zellen", 160, 40, 400)
start = param("Start", "mitte", options=["mitte", "zufall"])
pal = palette(param("Palette", "bauhaus", options=palettes()))

background(pal[0])
no_stroke()
k = width / zellen
zeilen = elementary_ca(regel, zellen, int(height / k), start=start)
for y, row in enumerate(zeilen):
    fill(color_ramp(pal[1:], y / len(zeilen)))
    x = 0
    while x < zellen:                     # zusammenhängende Läufe als ein Rechteck (schneller, plotbar)
        if row[x]:
            s = x
            while x < zellen and row[x]:
                x += 1
            rect(s * k, y * k, (x - s) * k + 0.3, k + 0.3)
        x += 1
