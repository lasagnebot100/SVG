"""Mathe: Mandelbrot, Julia und Newton"""
# Drei Fraktale aus komplexen Zahlen. Mandelbrot und Julia: Wie schnell entkommt ein Punkt
# bei z → z² + c? Newton: Zu welcher Nullstelle läuft das Newton-Verfahren?
# Bei Julia und Newton wird die Mitte um +0,6 verschoben, damit (0, 0) in der Bildmitte liegt.
# Mit numpy geht es deutlich schneller; ohne numpy die Auflösung lieber klein halten.
size(800, 800)

art = param("Fraktal", "mandelbrot", options=[("mandelbrot", "Mandelbrot"), ("julia", "Julia"),
                                             ("newton", "Newton")])
mitte_x = param("Mitte x", -0.6, -2.0, 2.0)
mitte_y = param("Mitte y", 0.0, -2.0, 2.0)
zoom = param("Zoom", 1.0, 0.5, 200.0)
c_re = param("Julia c (Realteil)", -0.8, -1.5, 1.5)
c_im = param("Julia c (Imaginärteil)", 0.156, -1.5, 1.5)
tiefe = param("Iterationen", 200, 20, 1000)
baender = param("Farbbänder", 4, 1, 20)
aufloesung = param("Auflösung", 400, 100, 1200)
pal = palette(param("Palette", "nacht", options=palettes()))

if art == "mandelbrot":
    feld = mandelbrot(aufloesung, aufloesung, (mitte_x, mitte_y), zoom, tiefe)
    bild = colorize(feld, pal[1:] + [pal[0]], cycles=baender, inside=pal[0])
elif art == "julia":
    feld = julia(aufloesung, aufloesung, (c_re, c_im), (mitte_x + 0.6, mitte_y), zoom, tiefe)
    bild = colorize(feld, pal[1:] + [pal[0]], cycles=baender, inside=pal[0])
else:
    bild = newton_fractal(aufloesung, aufloesung, 3 + int(baender) % 5, pal[1:], (mitte_x + 0.6, mitte_y), zoom)
image(bild, 0, 0, width, height)
