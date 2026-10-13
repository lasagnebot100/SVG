"""Geordnete Unruhe
Ein Raster aus Quadraten in Quadraten – und ein unsichtbares Feld, das bestimmt, wie viel Abweichung jede Zelle erträgt. Fern der Bruchlinie bleibt ein einziges Prozent Unruhe, nahe am Bruch kippen Ringe, verschieben sich Ecken, fallen Quadrate aus.

Alles ist Strich: gedacht für die Feder des Plotters, in Kobalt, mit einer zweiten Tinte dort, wo die Störung eine Schwelle überschreitet. Jeder Seed ist ein anderes Gelände; derselbe Seed immer dasselbe Blatt.
"""
# Philosophie ausführlich: docs/algorithmic-art/geordnete-unruhe.md
# Plotter: Export › Plotter – zwei Ebenen (eine pro Tinte).
size(800, 800)

n = param("Raster", 12, 4, 30)
ringe = param("Ringe", 6, 2, 14)
grund = param("Grundunruhe", 0.01, 0.0, 0.2, step=0.005)
bruch = param("Bruch", 0.9, 0.0, 2.0)
gefaelle = param("Gefälle", 0.2, 0.0, 1.5)
schwelle = param("Zweite Tinte ab", 0.55, 0.0, 1.05)
tinte = param("Tinte", "#1d3f9e")
tinte2 = param("Zweite Tinte", "#d9472b")
papier = param("Papier", "#f6f1e7")

background(papier)
no_fill()
stroke_weight(1.1)
stroke_join(ROUND)

rand = 70
zelle = (width - 2 * rand) / n

# das Gelände: ein Gefälle in zufälliger Richtung und eine gewundene Bruchlinie
richtung = random(TAU)
bruch_lage = random(0.3, 0.7)
bruch_amp = random(0.06, 0.18)
bruch_freq = random(0.8, 2.2)
bruch_phase = random(TAU)
bruch_dreh = random(-0.7, 0.7)


def unruhe(u, v):
    """Störung 0 … ~1.5 an der Stelle (u, v) des Blatts (0–1)."""
    g = 0.5 + (u - 0.5) * cos(richtung) + (v - 0.5) * sin(richtung)      # Gefälle 0–1
    x = 0.5 + (u - 0.5) * cos(bruch_dreh) - (v - 0.5) * sin(bruch_dreh)
    y = 0.5 + (u - 0.5) * sin(bruch_dreh) + (v - 0.5) * cos(bruch_dreh)
    d = abs(y - (bruch_lage + bruch_amp * sin(TAU * bruch_freq * x + bruch_phase)))
    band = exp(-(d / 0.11) ** 2)                                          # nahe am Bruch → 1
    textur = noise(u * 4, v * 4)
    return grund + gefaelle * max(0, g) ** 2 * 0.6 + bruch * band * (0.35 + 0.65 * textur)


for j in range(n):
    for i in range(n):
        cx = rand + (i + 0.5) * zelle
        cy = rand + (j + 0.5) * zelle
        s = unruhe((i + 0.5) / n, (j + 0.5) / n)
        for k in range(ringe):
            if k > 0 and random() < s * 0.3:
                continue                                  # ein ausgefallenes Quadrat
            halb = zelle * 0.46 * (ringe - k) / ringe
            dreh = random_gaussian(0, s * 0.35)
            dx = random_gaussian(0, s * zelle * 0.06)
            dy = random_gaussian(0, s * zelle * 0.06)
            zweite = s > schwelle and random() < (s - schwelle) * 1.6
            stroke(tinte2 if zweite else tinte)
            begin_shape()
            for ex, ey in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                px = ex * halb + random(-1, 1) * s * zelle * 0.07
                py = ey * halb + random(-1, 1) * s * zelle * 0.07
                vertex(cx + dx + px * cos(dreh) - py * sin(dreh), cy + dy + px * sin(dreh) + py * cos(dreh))
            end_shape(CLOSE)
