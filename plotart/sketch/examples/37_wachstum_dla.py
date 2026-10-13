"""Wachstum: DLA-Koralle"""
# Diffusionsbegrenztes Wachstum: Teilchen irren zufällig umher und kleben fest, sobald sie
# das Gebilde berühren. Es entstehen Korallen, Eisblumen, Blitze. Gezeichnet wird nur, was
# neu dazukommt – das Bild wächst Bild für Bild (kein background() in draw()).
size(800, 800)
animation(frames=200, fps=30)

pro_bild = param("Teilchen pro Bild", 15, 1, 60)
schritt = param("Schrittweite", 3.0, 1.5, 6.0)
klebrig = param("Klebrigkeit", 1.0, 0.1, 1.0)
pal = palette(param("Palette", "neon", options=palettes()))

d = DLA(seeds=[(width / 2, height / 2)], step=schritt, stickiness=klebrig, bounds=(10, 10, width - 10, height - 10))
gezeichnet = 1
tiefe = [0]


def setup():
    background(pal[0])


def draw():
    global gezeichnet
    d.grow(pro_bild)
    stroke_weight(1.6)
    for i in range(gezeichnet, len(d.particles)):
        x, y, k = d.particles[i]
        tiefe.append(tiefe[k] + 1)
        stroke(color_ramp(pal[1:], min(1, tiefe[-1] / 120)))
        px, py, _ = d.particles[k]
        line(px, py, x, y)
    gezeichnet = len(d.particles)
