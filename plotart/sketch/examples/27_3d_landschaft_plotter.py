"""3D für den Plotter: Noise-Landschaft als Gitter"""
# Ein eigenes Mesh: ein Höhenfeld aus Noise. Weiße Flächen mit schwarzen Kanten –
# mit „Verdeckte Linien entfernen“ wird daraus eine saubere Strichzeichnung.
size("A4", landscape=True)

n = param("Auflösung", 48, 10, 90)
amp = param("Höhe", 40.0, 0.0, 90.0)
zoom = param("Noise-Zoom", 0.07, 0.01, 0.3)
neigung = param("Neigung", 0.95, 0.2, 1.5)

background(255)
fill(255)
stroke(0)
stroke_weight(0.3)

breite = 205
punkte, flaechen = [], []
for j in range(n + 1):
    for i in range(n + 1):
        x = (i / n - 0.5) * breite
        z = (j / n - 0.5) * breite
        y = -amp * (noise(i * zoom, j * zoom) ** 1.6) * 1.8
        punkte.append((x, y, z))
for j in range(n):
    for i in range(n):
        a = j * (n + 1) + i
        flaechen.append((a, a + 1, a + n + 2, a + n + 1))

translate(width / 2, height * 0.55, -70)
rotate_x(-neigung)
mesh(punkte, flaechen)
