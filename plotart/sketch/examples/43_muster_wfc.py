"""Muster: Wave Function Collapse"""
# Jede Zelle ist zuerst „alles gleichzeitig“. Die Zelle mit den wenigsten Möglichkeiten wird
# festgelegt, die Nachbarn passen sich an – bis ein lückenloses Muster entsteht, dessen
# Kanten überall zusammenpassen. Kachelsätze: "rohre", "platine".
size(800, 800)

satz = param("Kachelsatz", "rohre", options=["rohre", "platine"])
n = param("Raster", 16, 4, 30)
pal = palette(param("Palette", "mint", options=palettes()))

background(pal[0])
zelle = (width - 80) / n
raster = wave_function_collapse(n, n, satz)
linien = join_paths(tile_paths(raster, satz, zelle, 40, 40))
no_fill()
stroke_cap(ROUND)
stroke_join(ROUND)
for breite, farbe in ((zelle * 0.34, pal[2]), (zelle * 0.22, pal[1]), (zelle * 0.06, pal[0])):
    stroke(farbe)
    stroke_weight(breite if satz == "rohre" else breite * 0.4)
    for p in linien:
        polyline(p)
