"""Animation: Wellen-Loop mit loop_noise"""
# loop_noise(x, y, t) wiederholt sich bei t = 1 nahtlos – organische Bewegung,
# die trotzdem perfekt loopt.
size(800, 1000)
animation(frames=150, fps=30)

linien = param("Linien", 46, 10, 120)
hoehe = param("Höhe", 150, 20, 400)
breite = param("Breite der Zone", 0.25, 0.05, 0.6)
tempo = param("Tempo", 1.5, 0.2, 4.0)
hell = param("Hell", False)

papier, tinte = ("#f4f1ea", "#151515") if hell else ("#0d0d0d", "#f0f0f0")
noise_detail(2)                      # weniger Detailstufen = schneller


def draw():
    background(papier)
    stroke(tinte)
    stroke_weight(1.6)
    fill(papier)
    oben, unten, rand = 230, height - 90, 110
    for i in range(linien):
        y0 = lerp(oben, unten, i / (linien - 1))
        begin_shape()
        vertex(rand, y0)
        for x in range(rand, width - rand + 1, 8):
            u = (x - width / 2) / (width - 2 * rand)
            huelle = exp(-(u / breite) ** 2 * 2)
            n = loop_noise(x * 0.012, i * 0.3, t, speed=tempo) * 1.15
            vertex(x, y0 - (n ** 2.4) * huelle * hoehe)
        vertex(width - rand, y0)
        end_shape()
