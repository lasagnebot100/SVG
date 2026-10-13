"""Muster: L-System-Wiese"""
# Ersetzungsregeln wachsen über Generationen zu Pflanzen; die Turtle zeichnet sie.
# Zufällige Regeln (Gewichte) und kleine Winkelabweichungen machen jede Pflanze einzigartig.
size(900, 600)

pflanzen = param("Pflanzen", 5, 1, 15)
generationen = param("Generationen", 5, 2, 6)
winkel = param("Winkel", 24.0, 10.0, 45.0)
pal = palette(param("Palette", "wald", options=palettes()))

background(pal[0])
regeln = {"X": [("F[+X][-X]FX", 0.5), ("F[+X]F[-X]+X", 0.3), ("F[-X]FX", 0.2)], "F": "FF"}
no_fill()
stroke_cap(ROUND)
for i in range(pflanzen):
    x = width * (i + 0.5) / pflanzen + random(-20, 20)
    text_ = lsystem("X", regeln, generationen)
    schritt = random(6.0, 8.0) * 2 ** (5 - generationen)
    aeste = turtle(text_, x, height - 20, step=schritt, angle=winkel, jitter=7, shrink=0.97)
    for p in aeste:
        stroke(lerp_color(pal[1], pal[2], random()), 230)
        stroke_weight(1.8)
        polyline(p)
