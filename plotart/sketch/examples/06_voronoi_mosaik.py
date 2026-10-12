"""Voronoi-Mosaik – organische Zellen wie Buntglas"""
size(900, 900)

abstand = param("Zellgröße", 46, 15, 150)
glatt = param("Lloyd-Glättung", 2, 0, 6)
fuge = param("Fuge", 0.16, 0.0, 0.5)
rund = param("Rundung", 3, 0, 5)
pal = palette(param("Palette", "terrakotta", options=palettes()))

background(pal[-1] if pal[-1] != pal[0] else "#222")
punkte = poisson_disc(width, height, abstand)
punkte = relax(punkte, 0, 0, width, height, glatt)
no_stroke()
for p, zelle in zip(punkte, voronoi_cells(punkte, 0, 0, width, height)):
    if len(zelle) < 3:
        continue
    cx, cy = centroid(zelle)
    # Zelle zum Mittelpunkt hin schrumpfen → Fuge
    innen = [(lerp(x, cx, fuge), lerp(y, cy, fuge)) for x, y in zelle]
    form = chaikin(innen, rund, closed=True) if rund else innen
    hell = noise(cx * 0.004, cy * 0.004)
    fill(lerp_color(random(pal[:-1]), "#ffffff", hell * 0.25))
    polygon(form)
