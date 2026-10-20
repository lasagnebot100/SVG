"""Großformat: Höhenlinien-Plakat in A2"""
# Ein Plakat in Millimetern, gedacht für den Druck auf mehreren Blättern. Im Studio unter
# „Großformat drucken“ (oder per Kommandozeile: plotart sketch 63 --tiles A4) wird es auf
# A4-Blätter verteilt – mit Schnittmarken, Klebe-Markierungen, PDF und Übersicht.
# Eine größere Druckbreite (z. B. 1000 mm) vergrößert es verlustfrei, weil alles Vektoren sind.
size("A2")

stufen = param("Höhenstufen", 26, 8, 60)
zoom = param("Noise-Zoom", 0.006, 0.002, 0.02)
pal = palette(param("Palette", "erde", options=palettes()))

background(pal[0])
noise_detail(5, 0.5)
raster = 3


def hoehe(x, y):
    d = dist(x, y, width / 2, height / 2) / width
    return noise(x * zoom, y * zoom) * (1.3 - d)


feld = [[hoehe(x * raster, y * raster) for x in range(int(width // raster) + 1)]
        for y in range(int(height // raster) + 1)]
lo, hi = min(map(min, feld)), max(map(max, feld))
no_fill()
for i in range(stufen):
    stroke(color_ramp(pal[1:], i / max(1, stufen - 1)))
    stroke_weight(0.6 if i % 5 else 1.4)                  # jede fünfte Linie kräftiger, wie auf der Karte
    for linie in contour_lines(feld, lo + (hi - lo) * (i + 0.5) / stufen, 0, 0, raster):
        polyline(linie)
