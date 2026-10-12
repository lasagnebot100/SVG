"""Wellenlinien – Bergrücken mit Verdeckung (Unknown Pleasures)"""
size(800, 1000)

linien = param("Linien", 60, 10, 160)
hoehe = param("Höhe der Spitzen", 120, 10, 400)
breite = param("Breite der Zone", 0.22, 0.05, 0.6)
massstab = param("Maßstab", 0.02, 0.003, 0.08)
hell = param("Hell", False)

papier, tinte = ("#f4f1ea", "#151515") if hell else ("#0d0d0d", "#f0f0f0")
background(papier)
stroke(tinte)
stroke_weight(1.6)
fill(papier)                     # jede Linie verdeckt die dahinter liegenden

oben, unten, rand = 200, height - 80, 110
for i in range(linien):
    y0 = lerp(oben, unten, i / (linien - 1))
    begin_shape()
    vertex(rand, y0)
    for x in range(rand, width - rand + 1, 3):
        u = (x - width / 2) / (width - 2 * rand)
        huelle = exp(-(u / breite) ** 2 * 2)
        n = noise(x * massstab, i * 0.35)
        vertex(x, y0 - (n ** 2.2) * huelle * hoehe - noise(x * 0.3, i) * 3)
    vertex(width - rand, y0)
    end_shape()
