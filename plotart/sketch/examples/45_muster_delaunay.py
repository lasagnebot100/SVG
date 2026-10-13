"""Muster: Low-Poly aus Delaunay-Dreiecken"""
# Punkte (Poisson-Disc, am Rand verdichtet) werden zu Dreiecken verbunden, deren Umkreise
# leer sind. Die Farbe jedes Dreiecks kommt aus einem Verlauf plus Noise – wie Kristall.
size(800, 800)

abstand = param("Punktabstand", 34.0, 12.0, 80.0)
noise_anteil = param("Noise", 0.35, 0.0, 1.0)
kanten = param("Kanten", True)
pal = palette(param("Palette", "sonnenuntergang", options=palettes()))

punkte = poisson_disc(width, height, abstand)
punkte += [(x, y) for x in (0, width) for y in range(0, height + 1, int(abstand))]
punkte += [(x, y) for y in (0, height) for x in range(0, width + 1, int(abstand))]
for a, b, c in delaunay(punkte):
    (x1, y1), (x2, y2), (x3, y3) = punkte[a], punkte[b], punkte[c]
    mx, my = (x1 + x2 + x3) / 3, (y1 + y2 + y3) / 3
    v = (1 - noise_anteil) * (mx + my) / (width + height) + noise_anteil * noise(mx * 0.004, my * 0.004)
    fill(color_ramp(pal, v))
    if kanten:
        stroke(pal[0], 90)
        stroke_weight(0.8)
    else:
        stroke(color_ramp(pal, v))
        stroke_weight(0.5)
    triangle(x1, y1, x2, y2, x3, y3)
