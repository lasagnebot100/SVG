"""Simulation: Game of Life mit Alters-Farben"""
# Conways Spiel des Lebens – und Verwandte über die Regel (B = geboren bei, S = überlebt bei).
# Die Farbe zeigt, wie lange eine Zelle schon lebt.
size(800, 800)
animation(frames=240, fps=15)

groesse = param("Zellgröße", 8, 3, 20)
dichte = param("Dichte", 0.3, 0.05, 0.7)
regel = param("Regel", "B3/S23", options=[("B3/S23", "Conway"), ("B36/S23", "HighLife"),
                                          ("B3678/S34678", "Tag & Nacht"), ("B35678/S5678", "Diamoeba")])
pal = palette(param("Palette", "neon", options=palettes()))

lf = Life(width // groesse, height // groesse, dichte, rule=regel)


def draw():
    background(pal[0])
    no_stroke()
    for y, row in enumerate(lf.age):
        for x, a in enumerate(row):
            if a:
                fill(color_ramp(pal[1:], min(1, a / 30)))
                square(x * groesse, y * groesse, groesse - 1)
    lf.step()
