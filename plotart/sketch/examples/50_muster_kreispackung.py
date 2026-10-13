"""Muster: Kreispackung in einer Form"""
# Kreise füllen eine Form so dicht wie möglich, ohne sich zu berühren.
# Hier die Form eines Noise-Flecks; jeder Kreis bekommt konzentrische Ringe für den Plotter.
size(800, 800)

min_r = param("Min. Radius", 3.0, 1.0, 20.0)
max_r = param("Max. Radius", 70.0, 10.0, 200.0)
ringe = param("Ringe", True)
pal = palette(param("Palette", "bauhaus", options=palettes()))


def innen(x, y):
    d = dist(x, y, width / 2, height / 2) / 330
    return d < 0.55 + 0.45 * noise(x * 0.006, y * 0.006)


background(pal[0])
kreise = circle_packing(width, height, min_r, max_r, attempts=8000, padding=2, inside=innen)
no_fill()
for i, (x, y, r) in enumerate(kreise):
    stroke(pal[1 + i % (len(pal) - 1)])
    stroke_weight(1.4)
    if ringe:
        k = r
        while k > 1.5:
            circle(x, y, 2 * k)
            k -= 5
    else:
        circle(x, y, 2 * r)
