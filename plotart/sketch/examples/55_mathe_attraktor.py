"""Mathe: Seltsamer Attraktor in 3D"""
# Der Lorenz-Attraktor und seine Verwandten: drei gekoppelte Differentialgleichungen,
# gelöst mit RK4. Die Bahn kommt nie zur Ruhe und wiederholt sich nie. Die Animation dreht
# den Attraktor einmal um die senkrechte Achse; die Farbe zeigt den Verlauf der Zeit.
size(800, 800)
animation(frames=240, fps=30)

name = param("Attraktor", "lorenz", options=[("lorenz", "Lorenz"), ("rossler", "Rössler"), ("aizawa", "Aizawa"),
                                             ("halvorsen", "Halvorsen"), ("thomas", "Thomas")])
punkte = param("Punkte", 12000, 2000, 40000)
abschnitte = param("Farbabschnitte", 60, 4, 200)
pal = palette(param("Palette", "neon", options=palettes()))

bahn = attractor(name, punkte)
if name in ("lorenz", "rossler", "aizawa"):
    bahn = [(x, y, z) for x, y, z in bahn]               # z zeigt nach oben
else:
    bahn = [(x, z, y) for x, y, z in bahn]
mx = sum(p[0] for p in bahn) / len(bahn)
my = sum(p[1] for p in bahn) / len(bahn)
mz = sum(p[2] for p in bahn) / len(bahn)
bahn = [(x - mx, y - my, z - mz) for x, y, z in bahn]
radius = max(max(abs(x), abs(y), abs(z)) for x, y, z in bahn)
massstab = width * 0.42 / radius


def draw():
    background(pal[0])
    translate(width / 2, height / 2)
    a = TAU * t
    flach = [((x * cos(a) - y * sin(a)) * massstab, -z * massstab) for x, y, z in bahn]
    no_fill()
    stroke_weight(0.8)
    stueck = max(2, len(flach) // abschnitte)
    for i in range(0, len(flach) - 1, stueck):
        stroke(color_ramp(pal[1:], i / len(flach)), 200)
        polyline(flach[i:i + stueck + 1])
