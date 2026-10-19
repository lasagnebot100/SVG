"""Mathe: Julia-Flug (GPU-Shader)"""
# Dieselbe Rechnung wie bei julia(), nur für jedes Pixel gleichzeitig auf der Grafikkarte.
# Der Parameter c wandert auf einem Kreis um die Mandelbrot-Menge – die Julia-Menge
# verwandelt sich dabei fließend. Nahtloser Loop über t.
# Am Computer braucht es einmalig: pip install moderngl. Im Browser-Studio läuft es sofort.
size(800, 800)
animation(frames=360, fps=30)

julia_gpu = create_shader("""
uniform float zoom;
uniform float radius;
uniform float phase;
uniform float baender;
uniform vec3 farbe_a;
uniform vec3 farbe_b;
uniform vec3 farbe_c;

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 z = (fragCoord - 0.5 * iResolution.xy) / iResolution.y * 3.0 / zoom;
    float a = (phase + 0.5) * 6.2831853;                 // Start bei c = -radius (zusammenhängende Menge)
    vec2 c = radius * vec2(cos(a), sin(a));
    float n = 0.0;
    for (int i = 0; i < 300; i++) {
        z = vec2(z.x * z.x - z.y * z.y, 2.0 * z.x * z.y) + c;
        if (dot(z, z) > 256.0) break;
        n += 1.0;
    }
    if (n >= 300.0) {
        fragColor = vec4(farbe_a, 1.0);                  // in der Menge
        return;
    }
    float mu = n + 1.0 - log(log(length(z))) / log(2.0);  // weiche Iterationszahl
    float s = clamp(sqrt(mu / 60.0), 0.0, 1.0);           // dunkel weit weg, hell am Rand der Menge
    vec3 col = mix(farbe_a, farbe_b, smoothstep(0.0, 0.55, s));
    col = mix(col, farbe_c, smoothstep(0.55, 1.0, s));
    col *= 0.8 + 0.2 * cos(mu * baender * 0.3);            // feine Bänder
    fragColor = vec4(col, 1.0);
}
""")

pal = palette(param("Palette", "nacht", options=palettes()))


def draw():
    shader_image(julia_gpu,
                 zoom=param("Zoom", 1.2, 0.5, 20.0),
                 radius=param("Radius von c", 0.7885, 0.3, 1.2),
                 baender=param("Farbbänder", 4.0, 1.0, 20.0),
                 phase=t,
                 farbe_a=pal[0], farbe_b=pal[-1], farbe_c=pal[3])
