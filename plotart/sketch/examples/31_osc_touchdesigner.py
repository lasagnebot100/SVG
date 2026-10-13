"""OSC: Fernsteuerung aus TouchDesigner, TouchOSC & Co."""
# Studio so starten:  python -m plotart studio --osc-in 9000 --osc-out 127.0.0.1:9001
# In TouchDesigner: OSC Out CHOP → Host 127.0.0.1, Port 9000, Kanal „td/level“ (wird /td/level).
# osc("/td/level", standard) liefert den letzten Wert; ohne Verbindung gilt der Standard
# (hier: die Maus bzw. eine Sinuswelle). osc_send() schickt Werte zurück (OSC In CHOP, Port 9001).
size(800, 800)
animation(frames=240, fps=30)

ringe = param("Ringe", 18, 4, 40)
pal = palette(param("Palette", "eis", options=palettes()))


def draw():
    background(pal[0])
    pegel = osc("/td/level", 0.5 + 0.5 * sin(TAU * t))     # 0–1
    drehen = osc("/td/rotate", mouse_x / width)
    no_fill()
    translate(width / 2, height / 2)
    rotate(drehen * TAU)
    for i in range(ringe):
        k = i / ringe
        stroke(color_ramp(pal[1:], k))
        stroke_weight(1 + 3 * pegel)
        n = 3 + i % 5
        begin_shape()
        for j in range(n + 1):
            a = TAU * j / n + k * pegel * PI
            r = 40 + k * 320 * (0.6 + 0.4 * pegel)
            vertex(cos(a) * r, sin(a) * r)
        end_shape()
    osc_send("/plotart/frame", frame_count)
    osc_send("/plotart/maus", mouse_x / width, mouse_y / height)
