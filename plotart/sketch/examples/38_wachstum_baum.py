"""Wachstum: Baum aus Space Colonization"""
# Äste wachsen zu Lichtpunkten in der Krone hin; erreichte Punkte verschwinden.
# Die Dicke folgt dem „Pipe-Modell“: je mehr Spitzen ein Ast trägt, desto dicker ist er.
size(800, 800)

lichter = param("Lichtpunkte", 900, 100, 3000)
segment = param("Segment", 5.0, 2.0, 12.0)
reichweite = param("Reichweite", 80.0, 20.0, 200.0)
dicke = param("Dicke", 1.1, 0.3, 3.0)
pal = palette(param("Palette", "herbst", options=palettes()))

background(pal[0])
# Krone: Punkte in einer leicht verbeulten Ellipse
krone = []
while len(krone) < lichter:
    x, y = random(80, 720), random(60, 520)
    dx, dy = (x - 400) / 320, (y - 300) / 230
    if dx * dx + dy * dy < 0.7 + 0.3 * noise(x * 0.01, y * 0.01):
        krone.append((x, y))

baum = SpaceColonization(krone, [(400, 780)], segment=segment, influence=reichweite, kill=segment * 1.6).grow(600)
stroke_cap(ROUND)
for x1, y1, x2, y2, w in baum.branches:
    stroke(lerp_color(pal[2], pal[-1], min(1, w / 14)))
    stroke_weight(max(0.6, min(30, w ** 0.85 * dicke * 0.7)))
    line(x1, y1, x2, y2)
# Blätter an den Spitzen
no_stroke()
for x1, y1, x2, y2, w in baum.branches:
    if w <= 1.0 and random() < 0.6:
        fill(random_choice(pal[2:]), 180)
        circle(x2, y2, random(3, 7))
