"""Animation: Kinetische Typografie mit Easing"""
size(1080, 1080)
animation(frames=120, fps=30)

wort = param("Wort", "PLOTART")
zeilen = param("Zeilen", 9, 3, 18)
pal = palette(param("Palette", "risograph", options=palettes()))


def draw():
    background(pal[0])
    no_stroke()
    text_style(BOLD)
    text_align(CENTER, CENTER)
    h = height / zeilen
    for r in range(zeilen):
        # jede Zeile startet etwas später → Welle durch das Bild
        phase = (t - r / zeilen * 0.5) % 1
        k = ease_in_out_cubic(ping_pong(phase))
        with push():
            translate(width / 2 + (k - 0.5) * 260 * (1 if r % 2 else -1), (r + 0.5) * h)
            scale(1, lerp(0.35, 1.0, k))
            fill(pal[1 + r % (len(pal) - 1)])
            text_size(h * 1.05)
            text(wort, 0, 0)
