"""Seltsamer Attraktor – Millionen Punkte mit numpy"""
import numpy as np

size(900, 900)
a = param("a", -1.7, -3.0, 3.0)
b = param("b", 1.3, -3.0, 3.0)
c = param("c", -0.1, -3.0, 3.0)
d = param("d", -1.21, -3.0, 3.0)
dichte = param("Kontrast", 0.35, 0.1, 1.0)
pal = palette(param("Palette", "nacht", options=palettes()))

# Clifford-Attraktor: viele Startpunkte parallel iterieren (schnell dank numpy)
n, schritte, res = 200_000, 30, 900
x = np.random.uniform(-1, 1, n)
y = np.random.uniform(-1, 1, n)
bild = np.zeros((res, res))
for i in range(schritte):
    x, y = np.sin(a * y) + c * np.cos(a * x), np.sin(b * x) + d * np.cos(b * y)
    if i > 5:
        h, _, _ = np.histogram2d(y, x, bins=res, range=[[-2.6, 2.6], [-2.6, 2.6]])
        bild += h

wert = np.log1p(bild) / np.log1p(bild.max())
wert = wert ** dichte
farben = [color(p) for p in pal]
rgb = np.zeros((res, res, 3))
stufen = np.linspace(0, 1, len(farben))
for k, kanal in enumerate("rgb"):
    rgb[..., k] = np.interp(wert, stufen, [getattr(f, kanal) for f in farben]) / 255

image(rgb, 0, 0, width, height)
