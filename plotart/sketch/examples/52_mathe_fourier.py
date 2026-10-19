"""Mathe: Fourier-Epizykel"""
# Jede geschlossene Zeichnung lässt sich in rotierende Kreise zerlegen (Fourier-Reihe).
# Epicycles() rechnet die Kreise aus; die Spitze der Kreiskette zeichnet die Form nach.
# Mit wenigen Kreisen entsteht eine weiche Näherung, mit vielen die genaue Form.
size(800, 800)
animation(frames=300, fps=30)

form = param("Form", "herz", options=[("herz", "Herz"), ("stern", "Stern"), ("rose", "Rose 5/3"),
                                      ("lissajous", "Lissajous 3:2")])
anzahl = param("Kreise", 24, 1, 128)
pal = palette(param("Palette", "nacht", options=palettes()))

if form == "herz":
    umriss = [(16 * sin(a) ** 3, -(13 * cos(a) - 5 * cos(2 * a) - 2 * cos(3 * a) - cos(4 * a)))
              for a in (TAU * i / 400 for i in range(400))]
elif form == "stern":
    umriss = superformula(5, 0.35, 0.6, 0.6)
elif form == "rose":
    umriss = rose(5, 3)
else:
    umriss = lissajous(3, 2)
umriss = fit_points(umriss, -260, -260, 520, 520)
kette = Epicycles(umriss, terms=anzahl)
ziel = kette.path(1.0)                                 # die ganze Form, blass im Hintergrund


def draw():
    background(pal[0])
    translate(width / 2, height / 2)
    no_fill()
    stroke(pal[2], 40)
    stroke_weight(1)
    polyline(ziel)
    stroke(pal[2], 70)
    kreise = kette.circles(t)
    for x, y, r in kreise:
        circle(x, y, 2 * r)
    stroke(pal[-1], 200)
    polyline([(x, y) for x, y, _ in kreise] + [kette.point(t)])
    stroke(pal[3])
    stroke_weight(2.5)
    polyline(kette.path(t))
