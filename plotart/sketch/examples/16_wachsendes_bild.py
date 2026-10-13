"""Animation: Wachsendes Bild – Harmonograph zeichnet sich selbst"""
# Kein background() in draw(): jedes Bild malt auf das vorige weiter –
# so entsteht die Zeichnung Strich für Strich.
size(900, 900)
animation(frames=360, fps=30)

f1 = param("Frequenz x", 3.0, 1.0, 6.0, 0.001)
f2 = param("Frequenz y", 2.0, 1.0, 6.0, 0.001)
daempfung = param("Dämpfung", 0.004, 0.0005, 0.02)
schritte = param("Striche pro Bild", 60, 5, 300)
pal = palette(param("Palette", "sonnenuntergang", options=palettes()))

p1, p2, p3 = random(TAU), random(TAU), random(TAU)
zeit = 0.0
letzter = None


def punkt(z):
    e = exp(-daempfung * z)
    x = (sin(f1 * z + p1) + 0.6 * sin(f2 * z + p3)) * e
    y = (sin(f2 * z + p2) + 0.6 * sin(f1 * z)) * e
    return width / 2 + x * 260, height / 2 + y * 260


def setup():
    background(pal[0])


def draw():
    global zeit, letzter
    no_fill()
    stroke_weight(1.2)
    for _ in range(schritte):
        zeit += 0.02
        p = punkt(zeit)
        if letzter:
            stroke(color(color_ramp(pal[1:], (zeit * 0.01) % 1)).alpha(0.6))
            line(*letzter, *p)
        letzter = p
