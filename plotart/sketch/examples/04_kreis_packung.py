"""Kreis-Packung – Kreise, die sich nicht berühren"""
size(900, 900)

versuche = param("Versuche", 3000, 200, 15000)
r_max = param("Max. Radius", 120, 10, 300)
r_min = param("Min. Radius", 3, 1, 30)
ringe = param("Ringe", True)
pal = palette(param("Palette", "bauhaus", options=palettes()))

background(pal[0])
kreise = []
for _ in range(versuche):
    x, y = random(width), random(height)
    r = min(r_max, x, y, width - x, height - y)
    for (cx, cy, cr) in kreise:
        r = min(r, dist(x, y, cx, cy) - cr - 4)
        if r < r_min:
            break
    if r >= r_min:
        kreise.append((x, y, r))

for (x, y, r) in kreise:
    farbe = random(pal[1:])
    if ringe and r > 12:
        no_fill()
        stroke(farbe)
        stroke_weight(2)
        rr = r
        while rr > 2:
            circle(x, y, rr * 2)
            rr -= 6
    else:
        no_stroke()
        fill(farbe)
        circle(x, y, r * 2)
print(len(kreise), "Kreise")
