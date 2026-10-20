"""Edition: Fenster ins Raster"""
# Jede Variante (jeder Seed) ist ein eigenes Werk einer Edition – wie bei Art Blocks oder fxhash.
# feature() hält ihre Merkmale fest. Im Studio zeigt „Merkmale → Seltenheit prüfen“, wie selten
# jeder Wert ist; die Gewichte in random_choice() bestimmen das. Der Serien-Export schreibt dazu
# Metadaten je Werk, edition.json und eine Galerie-Seite mit Filtern.
size(800, 800)

pal_name = feature("Palette", random_choice(["kobalt", "bauhaus", "terrakotta", "nacht", "risograph"],
                                            [30, 25, 20, 15, 10]))
raster = feature("Raster", random_choice([3, 4, 5, 7], [20, 40, 30, 10]))
stil = feature("Stil", random_choice(["Bögen", "Streifen", "Kreise", "gemischt"], [35, 30, 25, 10]))
goldrand = feature("Goldrand", random_choice([True, False], [1, 19]))     # selten: 5 %

pal = palette(pal_name)
background(pal[0])
rand = 70
zelle = (width - 2 * rand) / raster
for j in range(raster):
    for i in range(raster):
        art = stil if stil != "gemischt" else random(["Bögen", "Streifen", "Kreise"])
        farbe = random(pal[1:])
        push()
        translate(rand + (i + 0.5) * zelle, rand + (j + 0.5) * zelle)
        rotate(HALF_PI * random_int(4))
        if art == "Bögen":
            no_fill()
            stroke(farbe)
            stroke_weight(zelle * 0.07)
            for k in range(1, 5):
                arc(-zelle / 2, -zelle / 2, zelle * k * 0.45, zelle * k * 0.45, 0, HALF_PI)
        elif art == "Streifen":
            no_stroke()
            fill(farbe)
            for k in range(4):
                rect(-zelle / 2, -zelle / 2 + k * zelle / 4, zelle, zelle / 8)
        else:
            no_stroke()
            fill(farbe)
            circle(0, 0, zelle * random(0.4, 0.85))
        pop()

if goldrand:
    no_fill()
    stroke("#d4a72c")
    stroke_weight(14)
    rect(rand / 2, rand / 2, width - rand, height - rand)
