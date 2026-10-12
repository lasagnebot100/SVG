"""Strömungsfeld – Linien folgen einem Noise-Feld"""
size(900, 1200)

linien = param("Linien", 900, 50, 5000)
laenge = param("Länge (Schritte)", 70, 5, 300)
massstab = param("Maßstab", 0.0022, 0.0005, 0.01)
wirbel = param("Wirbel", 2.2, 0.3, 6.0)
pal = palette(param("Palette", "ozean", options=palettes()))

background(pal[0])
no_fill()
noise_detail(2, 0.5)

for i in range(linien):
    x, y = random(width), random(height)
    punkte = [(x, y)]
    for s in range(laenge):
        a = noise(x * massstab, y * massstab) * TAU * wirbel
        x += cos(a) * 3
        y += sin(a) * 3
        if not (0 <= x <= width and 0 <= y <= height):
            break
        punkte.append((x, y))
    stroke(color(random(pal[1:])).alpha(0.75))
    stroke_weight(random(0.5, 2.6))
    polyline(punkte)
