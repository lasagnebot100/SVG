"""Bild: Wellen-Schraffur – plotterfreundliche Linien aus einem Bild"""
# Jede Zeile ist eine einzige Linie. Wo das Bild dunkel ist, schwingt sie
# stärker und schneller – ideal für Stiftplotter (Plotter-Export!).
size("A4")

quelle = param("Bild", "beispiel:kugeln", options=["beispiel:kugeln", "beispiel:portrait", "beispiel:schrift"])
zeilen = param("Zeilen", 70, 20, 200)
amplitude = param("Ausschlag", 1.6, 0.2, 4.0)
frequenz = param("Frequenz", 1.8, 0.2, 5.0)
rand = param("Rand (mm)", 15, 0, 50)

img = load_image(quelle)
breite, hoehe = width - 2 * rand, height - 2 * rand
s = min(breite / img.width, hoehe / img.height)
iw, ih = img.width * s, img.height * s
ox, oy = (width - iw) / 2, (height - ih) / 2

background(255)
no_fill()
stroke("#1d1d1f")
stroke_weight(0.35)
abstand = ih / zeilen
for r in range(zeilen):
    y0 = oy + (r + 0.5) * abstand
    phase = 0.0
    punkte = []
    x = ox
    while x <= ox + iw:
        d = 1 - img.brightness((x - ox) / s, (y0 - oy) / s)
        phase += 0.25 * frequenz * (0.3 + 2.5 * d)
        punkte.append((x, y0 + sin(phase) * d * abstand * 0.5 * amplitude))
        x += 0.25
    polyline(punkte)
