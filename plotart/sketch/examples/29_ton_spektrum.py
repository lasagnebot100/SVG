"""Ton: Spektrum-Ring mit Beat-Puls"""
# load_audio() lädt eine Tondatei aus dem daten/-Ordner (WAV; MP3/OGG mit ffmpeg).
# "beispiel:beat.wav" ist eingebaut. Die Animation dauert so lang wie der Ton,
# im Studio läuft er synchron mit (🔊), und der MP4/WebM-Export enthält ihn.
size(800, 800)

ton = load_audio(param("Ton", "beispiel:beat.wav"))
baender = param("Bänder", 48, 8, 96)
pal = palette(param("Palette", "neon", options=palettes()))


def draw():
    background(pal[0], 90)             # leichte Spuren
    translate(width / 2, height / 2)
    puls = exp(-ton.since_beat() * 6)           # 1 im Beat, klingt dann ab
    no_fill()
    stroke(pal[1], 60 + 195 * puls)
    stroke_weight(2 + 10 * puls)
    circle(0, 0, 220 + 120 * puls)
    spek = ton.spectrum(baender)
    stroke_weight(4)
    for i, v in enumerate(spek):
        a = TAU * i / baender - HALF_PI
        r0 = 150 + 40 * ton.bass()
        r1 = r0 + 20 + 230 * v
        stroke(color_ramp(pal[1:], i / baender))
        line(cos(a) * r0, sin(a) * r0, cos(a) * r1, sin(a) * r1)
    # Oszilloskop in der Mitte
    welle = ton.waveform(160)
    stroke(255, 200)
    stroke_weight(1.5)
    begin_shape()
    for i, s in enumerate(welle):
        vertex(-110 + 220 * i / 159, s * 90)
    end_shape()
