"""Rekursive Teilung – Komposition à la Mondrian"""
size(800, 1000)

tiefe = param("Tiefe", 6, 1, 10)
teilen = param("Teil-Wahrscheinlichkeit", 0.75, 0.2, 1.0)
linie = param("Linienstärke", 8, 0, 20)
bunt = param("Farbanteil", 0.35, 0.0, 1.0)
pal = palette(param("Palette", "bauhaus", options=palettes()))

background(pal[0])
stroke(pal[-1] if linie > 0 else None)
stroke_weight(linie)
stroke_join(MITER)


def teile(x, y, w, h, stufe):
    if stufe == 0 or (stufe < tiefe and not chance(teilen)) or min(w, h) < 40:
        fill(random(pal[1:-1]) if chance(bunt) else pal[0])
        rect(x, y, w, h)
        return
    t = random_choice([0.33, 0.5, 0.62, 0.38])
    if w > h * random(0.7, 1.4):
        teile(x, y, w * t, h, stufe - 1)
        teile(x + w * t, y, w * (1 - t), h, stufe - 1)
    else:
        teile(x, y, w, h * t, stufe - 1)
        teile(x, y + h * t, w, h * (1 - t), stufe - 1)


teile(0, 0, width, height, tiefe)
