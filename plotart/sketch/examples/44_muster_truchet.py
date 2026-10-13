"""Muster: Truchet-Kacheln mit Noise-Steuerung"""
# Jede Kachel ist eine von zwei gespiegelten Varianten; ein Noise-Feld entscheidet, welche.
# join_paths() verbindet die Viertelkreise zu langen, geschwungenen Linien.
size(800, 800)

n = param("Raster", 20, 4, 60)
zoom = param("Noise-Zoom", 0.15, 0.0, 1.0)
stil = param("Stil", "boegen", options=["boegen", "diagonal", "dreiecke"])
pal = palette(param("Palette", "terrakotta", options=palettes()))

background(pal[0])
zelle = (width - 80) / n
formen = truchet(n, n, zelle, stil, 40, 40, bias=lambda c, r: noise(c * zoom, r * zoom))
if stil == "dreiecke":
    no_stroke()
    for i, f in enumerate(formen):
        fill(pal[1 + i % (len(pal) - 1)])
        polygon(f)
else:
    no_fill()
    stroke_cap(ROUND)
    linien = join_paths(formen)
    laengste = max(len(p) for p in linien)
    for p in sorted(linien, key=len):
        stroke(color_ramp(pal[1:], len(p) / laengste))
        stroke_weight(zelle * 0.18)
        polyline(p)
