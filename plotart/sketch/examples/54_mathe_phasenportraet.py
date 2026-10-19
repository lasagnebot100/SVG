"""Mathe: Phasenporträt"""
# Ein dynamisches System sagt für jeden Punkt (x, y), wohin er sich bewegt. Die Bahnen
# zeigen, wie sich Pendel, Oszillatoren oder Räuber und Beute entwickeln. Gelöst wird mit
# dem Runge-Kutta-Verfahren (RK4). Linien pur – gut für den Plotter.
size(800, 800)

system = param("System", "pendel", options=[("pendel", "Gedämpftes Pendel"), ("vdp", "Van-der-Pol-Oszillator"),
                                            ("lv", "Räuber und Beute"), ("wirbel", "Doppelwirbel")])
dichte = param("Startpunkte je Seite", 14, 4, 30)
staerke = param("Dämpfung / Stärke", 0.25, 0.0, 2.0)
pal = palette(param("Palette", "nacht", options=palettes()))

if system == "pendel":
    feld = lambda x, y: (y, -sin(x) - staerke * y)
    bereich = (-2 * PI, 2 * PI, -4, 4)
elif system == "vdp":
    feld = lambda x, y: (y, staerke * 2 * (1 - x * x) * y - x)
    bereich = (-4, 4, -5, 5)
elif system == "lv":
    feld = lambda x, y: (x * (1.1 - 0.5 * y), y * (0.2 * x - 0.6 - staerke * 0.1 * y))
    bereich = (0.05, 12, 0.05, 7)
else:
    feld = lambda x, y: (sin(y) - staerke * 0.2 * x, sin(x) - staerke * 0.2 * y)
    bereich = (-PI, PI, -PI, PI)

g = Graph(*bereich, 40, 40, width - 80, height - 80)
bahnen = phase_portrait(feld, *bereich, n=dichte, steps=250, dt=0.03)

background(pal[0])
no_fill()
stroke_weight(1)
for k, bahn in enumerate(bahnen):
    stroke(color_ramp(pal[1:], k / max(1, len(bahnen) - 1)), 200)
    polyline(g.pts(bahn))
