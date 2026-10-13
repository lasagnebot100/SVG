"""Simulation: Stoff im Wind"""
# Verlet-Physik: ein Gitter aus Teilchen und Federn, an zwei Ecken aufgehängt, Wind aus Noise.
# 🎮 Interaktiv: mit gedrückter Maus durch den Stoff fahren – ab einer Dehnung reißt er.
size(800, 800)
animation(frames=300, fps=30)

spalten = param("Spalten", 34, 8, 60)
zeilen = param("Zeilen", 26, 6, 50)
pal = palette(param("Palette", "pastell", options=palettes()))

welt = Physics(gravity=(0, 0.12), drag=0.02, iterations=16)
abstand = 560 / spalten
gitter = welt.cloth(120, 90, spalten, zeilen, abstand * 0.92, pin="corners", tear=2.2)


def draw():
    wind = param("Wind", 0.25, 0.0, 1.0)
    welt.gravity = (wind * (noise(frame_count * 0.03) * 2 - 0.8) + 0.15 * wind * sin(frame_count * 0.2), 0.12)
    if mouse_is_pressed:
        welt.attract(mouse_x, mouse_y, -14, 45)       # negativ = wegdrücken (reißt den Stoff)
    welt.step()
    background(pal[0])
    stroke(pal[2])
    stroke_weight(1)
    for x1, y1, x2, y2 in welt.lines:
        line(x1, y1, x2, y2)
    no_stroke()
    fill(pal[1])
    for i in (gitter[0][0], gitter[0][-1]):
        p = welt.particles[i]
        circle(p.x, p.y, 10)
