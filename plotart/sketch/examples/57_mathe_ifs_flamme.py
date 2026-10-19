"""Mathe: IFS-Fraktale und Fractal Flames"""
# Chaos-Spiel: Ein Punkt springt zufällig zwischen wenigen Abbildungen hin und her – und
# zeichnet dabei einen Farn, ein Sierpinski-Dreieck oder einen Drachen. Fractal Flames
# (Scott Draves) verzerren die Abbildungen zusätzlich; die Dichte der Punkte wird zu Licht.
size(800, 800)

art = param("Art", "farn", options=[("farn", "Barnsley-Farn"), ("sierpinski", "Sierpinski"), ("drache", "Drache"),
                                    ("baum", "Baum"), ("koch", "Koch-Kurve"), ("kristall", "Kristall"),
                                    ("flamme", "Fractal Flame")])
punkte = param("Punkte", 120000, 10000, 600000)
aufloesung = param("Auflösung", 500, 100, 1200)
kontrast = param("Kontrast", 0.45, 0.1, 1.0)
pal = palette(param("Palette", "nacht", options=palettes()))

background(pal[0])
if art == "flamme":
    bild = fractal_flame(aufloesung, aufloesung, punkte, colors=pal[1:], gamma=1 / kontrast)
else:
    pts = fit_points(ifs(art, punkte), 0, 0, aufloesung, aufloesung, margin=aufloesung * 0.05, flip_y=True)
    bild = colorize(density(pts, aufloesung, aufloesung, kontrast), [pal[0]] + pal[1:])
image(bild, 0, 0, width, height)
