"""3D interaktiv: Kugelwolke mit Orbit-Kamera"""
# orbit_control(): im 🎮-Interaktiv-Modus mit der Maus drehen, mit dem Mausrad zoomen.
# Ohne Interaktion dreht sich die Szene langsam von selbst.
size(800, 800)
animation(frames=240, fps=30)

anzahl = param("Kugeln", 70, 10, 200)
radius = param("Radius", 230.0, 80.0, 360.0)
pal = palette(param("Palette", "sonnenuntergang", options=palettes()))

punkte = []
for i in range(anzahl):
    # Fibonacci-Kugel: gleichmäßig verteilte Punkte
    y = 1 - 2 * (i + 0.5) / anzahl
    r = sqrt(1 - y * y)
    a = i * 2.39996
    punkte.append((cos(a) * r, y, sin(a) * r, random(0.6, 1.0)))


def draw():
    background(pal[0])
    orbit_control()
    ambient_light(70)
    directional_light(255, 255, 255, -0.4, 0.6, -1)
    point_light(pal[1], 0, 0, 0)
    no_stroke()
    translate(width / 2, height / 2)
    if not mouse_is_pressed:
        rotate_y(TAU * t)
    fill(pal[2])
    sphere(40, 16, 12)
    for k, (x, y, z, s) in enumerate(punkte):
        with push():
            translate(x * radius, y * radius, z * radius)
            fill(color_ramp(pal[1:], k / anzahl))
            sphere(14 * s, 10, 8)
