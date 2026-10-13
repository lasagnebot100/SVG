"""Wachstum: Differential Growth"""
# Eine geschlossene Linie wächst: Nachbarn halten zusammen, alles andere stößt sich ab,
# ständig kommen neue Punkte dazu – die Linie faltet sich wie eine Koralle oder ein Gehirn.
# Am Ende der Animation ist das Bild fertig (auch zum Plotten: Export › Plotter).
size(800, 800)
animation(frames=240, fps=30)

schritte = param("Schritte pro Bild", 3, 1, 6)
wachstum = param("Wachstum", 0.02, 0.0, 0.08)
abstand = param("Kantenlänge", 6.0, 3.0, 12.0)
pal = palette(param("Palette", "ozean", options=palettes()))

start = [(width / 2 + 140 * cos(a), height / 2 + 140 * sin(a)) for a in (TAU * i / 60 for i in range(60))]
g = DifferentialGrowth(start, max_edge=abstand, growth=wachstum, bounds=(40, 40, width - 40, height - 40),
                       max_nodes=7000)


def draw():
    g.step(schritte)
    background(pal[0])
    stroke(pal[2])
    stroke_weight(1.4)
    fill(pal[1])
    polygon(g.points)
