"""Muster: Gleichmäßige Stromlinien"""
# Linien folgen einem Richtungsfeld, halten aber überall denselben Abstand zueinander
# (Jobard & Lefer). Ergibt ruhige, haarartige Flächen – ideal für Plotter und Druck.
size(800, 800)

abstand = param("Abstand", 9.0, 3.0, 30.0)
zoom = param("Feld-Zoom", 0.003, 0.0005, 0.02)
wirbel = param("Wirbel", 2.0, 0.5, 6.0)
pal = palette(param("Palette", "kobalt", options=palettes()))

background(pal[0])
noise_detail(3, 0.5)
richtung = lambda x, y: noise(x * zoom, y * zoom) * TAU * wirbel
linien = streamlines(richtung, width - 80, height - 80, abstand, step=1.5, x0=40, y0=40)
no_fill()
laengste = max(len(p) for p in linien)
for p in linien:
    k = len(p) / laengste
    stroke(color_ramp(pal[1:], k))
    stroke_weight(0.6 + 1.0 * k)
    polyline(p)
