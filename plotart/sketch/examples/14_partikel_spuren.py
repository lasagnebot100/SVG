"""Animation: Partikel mit Spuren im Strömungsfeld"""
# Zustand über mehrere Bilder: Partikel werden in setup() angelegt und in draw()
# bewegt. Ein halbtransparenter Hintergrund lässt Spuren stehen (wie in p5.js).
size(900, 900)
animation(frames=300, fps=30)

anzahl = param("Partikel", 700, 50, 3000)
tempo = param("Tempo", 2.2, 0.5, 6.0)
spuren = param("Spurlänge", 18, 2, 80, help="kleiner = längere Spuren")
massstab = param("Maßstab", 0.003, 0.0005, 0.01)
pal = palette(param("Palette", "ozean", options=palettes()))

teilchen = []


def setup():
    background(pal[0])
    for _ in range(anzahl):
        teilchen.append([random(width), random(height), random(pal[1:])])
    noise_detail(2)


def draw():
    background(color(pal[0]).alpha(spuren / 255))        # Spuren verblassen langsam
    stroke_weight(1.6)
    for p in teilchen:
        x, y, farbe = p
        a = noise(x * massstab, y * massstab, time * 0.15) * TAU * 2
        nx, ny = x + cos(a) * tempo, y + sin(a) * tempo
        stroke(farbe)
        line(x, y, nx, ny)
        if not (0 <= nx < width and 0 <= ny < height):     # neu einsetzen
            nx, ny = random(width), random(height)
        p[0], p[1] = nx, ny
