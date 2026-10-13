"""Animation: Nahtloser Loop – Kreise im Tanz"""
# Animationen: definiere draw() – es wird für jedes Bild aufgerufen.
# t läuft von 0 bis 1 über die ganze Animation → alles, was nur von t abhängt,
# wiederholt sich nahtlos (perfekt für GIFs und Social Media).
size(800, 800)
animation(frames=180, fps=30)                  # 6 Sekunden

ringe = param("Ringe", 9, 2, 20)
punkte = param("Punkte pro Ring", 24, 6, 64)
drehung = param("Verdrehung", 1.5, 0.0, 4.0)
pal = palette(param("Palette", "nacht", options=palettes()))


def draw():
    background(pal[0])
    no_stroke()
    translate(width / 2, height / 2)
    for r in range(1, ringe + 1):
        radius = r * 340 / ringe
        for i in range(punkte):
            a = TAU * i / punkte + TAU * t * (1 if r % 2 else -1) + sin(TAU * t + r * 0.4) * drehung * 0.2
            puls = wave(t, 2, r / ringe + i / punkte)      # 2 Schwingungen pro Loop
            fill(color_ramp(pal[1:], r / ringe))
            circle(cos(a) * radius, sin(a) * radius, 4 + 14 * puls * r / ringe)
