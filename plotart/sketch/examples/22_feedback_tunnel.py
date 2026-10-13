"""Animation: Feedback-Tunnel mit snapshot()"""
# snapshot() macht aus dem bisher Gezeichneten ein Bild. Im nächsten Bild wird es
# leicht verkleinert und gedreht wieder gezeichnet – eine endlose Rückkopplung.
size(600, 600)
animation(frames=150, fps=30)

zoom = param("Zoom", 0.955, 0.8, 0.99)
drehung = param("Drehung", -6.0, -15.0, 15.0)
blur = param("Weichzeichnen", 0.0, 0.0, 3.0)
pal = palette(param("Palette", "neon", options=palettes()))

vorher = None


def draw():
    global vorher
    background(pal[0])
    if vorher is not None:
        with push():
            translate(width / 2, height / 2)
            rotate(radians(drehung))
            scale(zoom)
            image(vorher, -width / 2, -height / 2, width, height)
    # neue Form am Rand – wandert durch die Rückkopplung nach innen
    a = TAU * t * 2
    no_stroke()
    for k in range(2):                      # zwei gegenüberliegende Formen
        fill(color_ramp(pal[1:], wave(t + k * 0.5, 3)))
        circle(width / 2 + cos(a + k * PI) * 240, height / 2 + sin(a + k * PI) * 240, 40)
    if blur:
        filter(BLUR, blur)
    vorher = snapshot()
