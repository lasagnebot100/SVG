"""Noise-Landschaft – Bergketten aus Perlin-Noise"""
size(1000, 700)

schichten = param("Bergketten", 7, 2, 16)
rauheit = param("Rauheit", 0.0035, 0.0005, 0.015)
hoehe = param("Höhe", 260, 40, 500)
pal = palette(param("Palette", "sonnenuntergang", options=palettes()))
himmel_oben, himmel_unten, fern, nah = pal[3], pal[2], pal[1], pal[0]

no_stroke()
background(linear_gradient(0, 0, 0, height, [himmel_oben, himmel_unten]))

# Sonne mit weichem Schein
sx, sy = width * 0.68, height * 0.22
fill(radial_gradient(sx, sy, 230, [color(himmel_unten).lighter(0.7), color(himmel_unten).alpha(0)]))
circle(sx, sy, 460)
fill(color(himmel_unten).lighter(0.55))
circle(sx, sy, 120)

noise_detail(5, 0.5)
for i in range(schichten):
    t = i / max(1, schichten - 1)            # 0 = hinten, 1 = vorne
    basis = lerp(height * 0.5, height * 0.95, t)
    amp = lerp(hoehe, hoehe * 0.35, t)
    fill(lerp_color(fern, nah, t ** 0.8))
    begin_shape()
    vertex(0, height)
    for x in range(0, width + 1, 4):
        y = basis - noise(x * rauheit * (1 + t), i * 7.3) * amp
        vertex(x, y)
    vertex(width, height)
    end_shape(CLOSE)
