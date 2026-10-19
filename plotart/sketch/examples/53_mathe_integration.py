"""Mathe: Numerische Integration"""
# Die Fläche unter einer Kurve, angenähert durch Streifen: Rechtecke (links, Mitte, rechts),
# Trapeze oder Simpson-Parabeln. Die Animation erhöht die Zahl der Streifen – rot ist die
# Abweichung, sie schrumpft. Die Formel ist frei wählbar (^ = hoch, z. B. x^2).
size(900, 600)
animation(frames=240, fps=30)

text_formel = param("Formel f(x)", "sin(x) + 0.4*sin(3*x) + 1.3")
a = param("von a", 0.0, -10.0, 10.0)
b = param("bis b", 6.0, -10.0, 10.0)
regel = param("Regel", "mitte", options=[("links", "Rechteck links"), ("mitte", "Rechteck Mitte"),
                                         ("rechts", "Rechteck rechts"), ("trapez", "Trapez"),
                                         ("simpson", "Simpson")])
max_n = param("Streifen höchstens", 40, 2, 120)
pal = palette(param("Palette", "kobalt", options=palettes()))

f = formula(text_formel)
werte = [y for y in (f(a + (b - a) * i / 200) for i in range(201))]
y_lo, y_hi = min(0, min(werte)), max(0, max(werte))
rand = (y_hi - y_lo) * 0.15 or 1
g = Graph(a - (b - a) * 0.05, b + (b - a) * 0.05, y_lo - rand, y_hi + rand, 60, 40, width - 100, height - 110)


def draw():
    background(pal[0])
    n = 1 + int((max_n - 1) * ease_in_out(ping_pong(t + 0.5)))   # viele Streifen → einer → viele
    r = riemann(f, a, b, n, regel)
    stroke(pal[1])
    stroke_weight(1)
    fill(pal[3], 110)
    for s in r.shapes:
        polygon(g.pts(s))
    no_stroke()
    fill("#d1495b", 150)
    for s in r.error_shapes:
        polygon(g.pts(s))
    stroke(pal[1], 120)
    for line in g.axes():
        polyline(line)
    no_fill()
    stroke(pal[2])
    stroke_weight(2.5)
    for piece in g.curve(f):
        polyline(piece)
    fill(pal[1])
    no_stroke()
    text_size(11)
    text_align(CENTER, CENTER)
    for x, y, s in g.labels():
        text(s, x, y)
    text_size(18)
    text_align(LEFT, BASELINE)
    text(f"{regel}, n = {r.n}:  {r.value:.5f}   genau ≈ {r.exact:.5f}   Fehler {r.error:+.5f}", 60, height - 28)
