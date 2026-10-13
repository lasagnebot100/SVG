"""Simulation: Schwarm (Boids)"""
# Drei einfache Regeln – Abstand halten, in dieselbe Richtung fliegen, zusammenbleiben – und
# es entsteht Schwarmverhalten. Halbtransparenter Hintergrund = Spuren.
# 🎮 Interaktiv: der Schwarm folgt der gedrückten Maus.
size(800, 800)
animation(frames=300, fps=30)

anzahl = param("Anzahl", 250, 20, 800)
pal = palette(param("Palette", "eis", options=palettes()))
f = Flock(anzahl, width, height, max_speed=3.2, perception=38)


def draw():
    f.separation = param("Trennung", 1.5, 0.0, 4.0)
    f.alignment = param("Ausrichtung", 1.0, 0.0, 4.0)
    f.cohesion = param("Zusammenhalt", 1.0, 0.0, 4.0)
    f.target = (mouse_x, mouse_y) if mouse_is_pressed else None
    f.step()
    background(pal[0], 40)
    no_stroke()
    for b in f.boids:
        fill(color_ramp(pal[1:], b.speed / f.max_speed))
        with push():
            translate(b.x, b.y)
            rotate(b.angle)
            triangle(7, 0, -5, -3.5, -5, 3.5)
