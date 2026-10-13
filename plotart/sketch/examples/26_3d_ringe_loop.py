"""3D-Animation: Ringe im Licht (Loop)"""
# Tori drehen sich phasenversetzt; zwei farbige Lichter geben Tiefe.
# t läuft von 0 bis 1 – nach einer Runde schließt der Loop nahtlos.
size(720, 720)
animation(frames=120, fps=30)

anzahl = param("Ringe", 7, 1, 14)
dicke = param("Dicke", 14.0, 4.0, 40.0)
versatz = param("Versatz", 0.35, 0.0, 1.0)
pal = palette(param("Palette", "neon", options=palettes()))


def draw():
    background(pal[0])
    ambient_light(50)
    directional_light(pal[1], 0.5, 0.4, -1)
    directional_light(pal[2], -0.7, -0.2, -0.6)
    no_stroke()
    fill(235)
    translate(width / 2, height / 2)
    rotate_x(0.5)
    for k in range(anzahl):
        with push():
            a = TAU * (t + k * versatz / anzahl)
            rotate_y(a)
            rotate_x(a * 2)
            torus(60 + k * 34, dicke, 40, 12)
