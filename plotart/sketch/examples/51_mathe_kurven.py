"""Mathe: Kurven-Baukasten"""
# Klassische Kurven der Mathematik als Raster von Varianten: Lissajous-Figuren, Rosen,
# Spirograph, Superformel und Harmonograph. Jede Zelle ändert die Zahlen ein wenig.
# Alles sind Punktlisten – eine durchgehende Linie pro Figur, ideal für den Plotter.
size(800, 800)

art = param("Kurve", "spirograph", options=[("lissajous", "Lissajous"), ("rose", "Rosen"),
                                            ("spirograph", "Spirograph"), ("superformel", "Superformel"),
                                            ("harmonograph", "Harmonograph")])
zellen = param("Raster", 4, 1, 6)
dicke = param("Strichstärke", 1.0, 0.3, 3.0)
pal = palette(param("Palette", "nacht", options=palettes()))

background(pal[0])
no_fill()
stroke_weight(dicke)
zelle = width / zellen
for j in range(zellen):
    for i in range(zellen):
        k = j * zellen + i
        if art == "lissajous":
            pts = lissajous(i + 1, j + 2, PI / 2 * (k % 5) / 4)
        elif art == "rose":
            pts = rose(i + 2, j + 1)
        elif art == "spirograph":
            # Radien mit wenigen Umläufen (r / ggT(96, r)), sonst wird die Figur zu dicht
            pts = spirograph(96, random([20, 28, 30, 36, 40, 42, 44, 52, 54, 56, 60, 66, 80, 84]),
                             random(20, 90), kind=random(["hypo", "epi"]))
        elif art == "superformel":
            pts = superformula(random_int(2, 12), random(0.2, 4), random(0.3, 3), random(0.3, 3))
        else:
            pts = harmonograph(steps=5000)
        pts = fit_points(pts, i * zelle, j * zelle, zelle, zelle, margin=zelle * 0.1)
        stroke(color_ramp(pal[2:], k / max(1, zellen * zellen - 1)))
        polyline(pts)
