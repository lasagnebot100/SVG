"""Interaktiv: Partikel-Pinsel (Maus & Tastatur)"""
# 🎮 Interaktiv einschalten (Taste I), dann auf der Leinwand ziehen.
# Mausrad = Pinselgröße · Taste c = löschen · Leertaste = Farbe wechseln.
# ⏺ nimmt die Bewegungen auf – der Video-Export spielt sie genau so ab.
size(800, 800)
animation(frames=300, fps=30)

pal = palette(param("Palette", "risograph", options=palettes()))
reibung = param("Reibung", 0.94, 0.8, 0.995)

teilchen = []
groesse = 18.0
farbe = 1


def setup():
    background(pal[0])


def mouse_dragged():
    for _ in range(6):
        a = random(TAU)
        v = random(0.5, 3) + dist(mouse_x, mouse_y, pmouse_x, pmouse_y) * 0.15
        teilchen.append([mouse_x, mouse_y, cos(a) * v, sin(a) * v, random(0.4, 1) * groesse, pal[farbe]])


def mouse_wheel(delta):
    global groesse
    groesse = constrain(groesse - delta * 0.02, 3, 80)


def key_pressed():
    global farbe
    if key == "c":
        background(pal[0])
        teilchen.clear()
    elif key == " ":
        farbe = farbe % (len(pal) - 1) + 1


def draw():
    if frame_count == 1 and not teilchen:    # ohne Eingaben (Vorschau): eine Spirale zeigt die Idee
        for k in range(90):
            a = k * 0.35
            teilchen.append([width / 2 + cos(a) * k * 3, height / 2 + sin(a) * k * 3, cos(a), sin(a), 14, pal[1 + k % (len(pal) - 1)]])
    no_stroke()
    for p in teilchen:
        p[0] += p[2]; p[1] += p[3]
        p[2] *= reibung; p[3] *= reibung
        p[4] *= 0.97
        fill(p[5], 90)
        circle(p[0], p[1], p[4])
    teilchen[:] = [p for p in teilchen if p[4] > 0.6]
