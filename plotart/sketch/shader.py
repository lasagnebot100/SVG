"""GPU fragment shaders in sketches (GLSL, Shadertoy style).

    sh = create_shader('''
    uniform float zoom;
    void mainImage(out vec4 fragColor, in vec2 fragCoord) {
        vec2 uv = fragCoord / iResolution.xy;
        fragColor = vec4(uv, 0.5 + 0.5 * sin(iTime * zoom), 1.0);
    }''')
    shader_image(sh, zoom=2.0)                 # whole canvas
    apply_shader(post)                         # post-process: the canvas is iChannel0

Built-in uniforms (like Shadertoy): iResolution, iTime, iTimeDelta, iFrame, iMouse,
iChannel0…iChannel3, iChannelResolution[4]. fragCoord starts bottom left (y up).
Write a full `void main()` instead, and only #version/precision is added.

The GLSL dialect is 3.30 / ES 3.00 (texture(), in/out), which runs unchanged on
  - the desktop through moderngl (pip install moderngl; headless via EGL on Linux),
  - in the browser (Studio web app, shared web pages) through WebGL2 – Pyodide's worker
    draws on an OffscreenCanvas.
The result is an ordinary image in the sketch: SVG, PNG, video, Blender work as usual;
the plotter ignores it (no lines).
"""
from __future__ import annotations

import re
import sys

from .png import _encode

MAX_CHANNELS = 4
BUILTIN = {
    "iResolution": "uniform vec3 iResolution;",
    "iTime": "uniform float iTime;",
    "iTimeDelta": "uniform float iTimeDelta;",
    "iFrame": "uniform int iFrame;",
    "iMouse": "uniform vec4 iMouse;",
    "iChannel0": "uniform sampler2D iChannel0;",
    "iChannel1": "uniform sampler2D iChannel1;",
    "iChannel2": "uniform sampler2D iChannel2;",
    "iChannel3": "uniform sampler2D iChannel3;",
    "iChannelResolution": "uniform vec3 iChannelResolution[4];",
}
VERTEX = "in vec2 plotart_pos;\nvoid main() { gl_Position = vec4(plotart_pos, 0.0, 1.0); }\n"


class ShaderError(Exception):
    pass


# ------------------------------------------------------------------------ source handling
def _head(es: bool) -> str:
    return "#version 300 es\nprecision highp float;\nprecision highp int;\nprecision highp sampler2D;\n" if es \
        else "#version 330\n"


def wrap_fragment(source: str, es: bool) -> str:
    """User code → complete fragment shader for GLSL 3.30 (desktop) or ES 3.00 (WebGL2)."""
    src = re.sub(r"^\s*#version[^\n]*\n?", "", source, flags=re.M)
    src = re.sub(r"^\s*precision\s+\w+\s+\w+\s*;[^\n]*\n?", "", src, flags=re.M)
    if re.search(r"\bvoid\s+main\s*\(", src):
        return _head(es) + "#line 1\n" + src
    decl = [d for name, d in BUILTIN.items() if not re.search(r"\buniform\s+\w+\s+" + name + r"\b", src)]
    if not re.search(r"\bvoid\s+mainImage\s*\(", src):
        raise ShaderError("Der Shader braucht eine Funktion mainImage(out vec4 fragColor, in vec2 fragCoord) "
                          "oder ein eigenes void main().")
    return (_head(es) + "\n".join(decl) + "\nout vec4 plotart_FragColor;\n#line 1\n" + src +
            "\nvoid main() { vec4 c = vec4(0.0, 0.0, 0.0, 1.0); mainImage(c, gl_FragCoord.xy); "
            "plotart_FragColor = c; }\n")


def _shader_error(kind: str, log: str) -> ShaderError:
    """Readable compiler message; '0:12(5): error …' (Mesa) / 'ERROR: 0:12: …' / '0(12) : error C…: …' (NVIDIA)
    → 'Zeile 12: …'."""
    lines = []
    for ln in str(log).replace("\0", "").strip().splitlines():
        if not ln.strip() or set(ln.strip()) <= {"="} or ln.strip() in ("GLSL Compiler failed", "fragment_shader",
                                                                          "vertex_shader"):
            continue
        m = re.search(r"(?:ERROR:\s*)?\d+(?::(\d+)(?:\(\d+\))?|\((\d+)\))\s*:\s*(?:error[^:]*:\s*)?(.*)", ln)
        lines.append(f"Zeile {m.group(1) or m.group(2)}: {m.group(3).strip()}" if m else ln.strip())
    msg = "; ".join(x for x in lines if x)[:600] or "unbekannter Fehler"
    return ShaderError(f"{kind}: {msg}")


# ------------------------------------------------------------------------ values
def _floats(value, n: int):
    """Python value → n floats (colours become 0–1, '#hex' allowed)."""
    from .color import Color, to_color
    if isinstance(value, str) or isinstance(value, Color):
        c = to_color((value,))
        value = (c.r / 255, c.g / 255, c.b / 255, c.a)
    if hasattr(value, "x") and hasattr(value, "y") and not isinstance(value, (tuple, list)):
        value = (value.x, value.y)
    if isinstance(value, (int, float, bool)):
        vals = [float(value)]
    else:
        vals = [float(v) for v in value]
    if n == 1:
        return vals[0]
    vals = (vals + [vals[-1] if len(vals) == 1 else 0.0] * n)[:n] if len(vals) < n else vals[:n]
    return tuple(vals)


def _is_image(v) -> bool:
    return hasattr(v, "to_pil") or (hasattr(v, "save") and hasattr(v, "size")) or \
        (hasattr(v, "shape") and hasattr(v, "dtype"))


def image_rgba(img) -> tuple[bytes, int, int]:
    """Img / PIL image / numpy array → (RGBA bytes top row first, width, height)."""
    if hasattr(img, "to_pil"):
        img = img.to_pil()
    if hasattr(img, "save") and hasattr(img, "size"):
        im = img.convert("RGBA")
        return im.tobytes(), im.width, im.height
    import numpy as np
    a = np.asarray(img)
    if a.dtype.kind == "f":
        a = np.clip(a * 255 + 0.5, 0, 255)
    a = a.astype(np.uint8)
    if a.ndim == 2:
        a = np.stack([a, a, a, np.full_like(a, 255)], axis=2)
    elif a.shape[2] == 3:
        a = np.concatenate([a, np.full(a.shape[:2] + (1,), 255, np.uint8)], axis=2)
    return np.ascontiguousarray(a).tobytes(), a.shape[1], a.shape[0]


def _flip_rows(data: bytes, w: int, h: int) -> bytes:
    row = w * 4
    return b"".join(data[(h - 1 - y) * row:(h - y) * row] for y in range(h))


# ------------------------------------------------------------------------ backends
class _ModernGL:
    name = "moderngl"

    def __init__(self):
        try:
            import moderngl
        except ImportError:
            raise ShaderError("Für Shader am Computer wird moderngl gebraucht: pip install moderngl "
                              "(https://moderngl.readthedocs.io). Im Browser-Studio laufen Shader ohne Installation.")
        last = None
        for kw in ({"require": 330}, {"require": 330, "backend": "egl"}):
            try:
                self.ctx = moderngl.create_standalone_context(**kw)
                break
            except Exception as exc:                      # no display, no driver …
                last = exc
        else:
            raise ShaderError(f"Kein OpenGL-3.3-Kontext verfügbar ({last}). Grafiktreiber aktualisieren; "
                              "unter Linux ohne Bildschirm: Pakete libegl1 und libgl1-mesa-dri installieren.")
        import struct
        self.vbo = self.ctx.buffer(struct.pack("6f", -1, -1, 3, -1, -1, 3))   # one big triangle
        self.programs: dict = {}
        self.fbos: dict = {}

    def renderer(self) -> str:
        return self.ctx.info.get("GL_RENDERER", "?")

    def _program(self, src: str):
        p = self.programs.get(src)
        if p is None:
            try:
                prog = self.ctx.program(vertex_shader="#version 330\n" + VERTEX, fragment_shader=src)
            except Exception as exc:
                raise _shader_error("Shader-Fehler (Zeilen im Shader-Text)", str(exc)) from None
            vao = self.ctx.vertex_array(prog, [(self.vbo, "2f", "plotart_pos")])
            p = self.programs[src] = (prog, vao)
            if len(self.programs) > 32:
                self.programs.pop(next(iter(self.programs)))
        return p

    def render(self, source, w, h, uniforms, textures):
        prog, vao = self._program(wrap_fragment(source, es=False))
        fbo = self.fbos.get((w, h))
        if fbo is None:
            fbo = self.fbos[(w, h)] = self.ctx.simple_framebuffer((w, h), components=4)
        fbo.use()
        fbo.clear(0.0, 0.0, 0.0, 0.0)
        texs = []
        for unit, (data, tw, th) in textures.items():
            t = self.ctx.texture((tw, th), 4, _flip_rows(data, tw, th))
            t.repeat_x = t.repeat_y = False
            t.use(location=unit)
            texs.append(t)
            name = f"iChannel{unit}"
            if name in prog:
                prog[name].value = unit
        for name, value in uniforms.items():
            if name not in prog or name.startswith("iChannel") and name != "iChannelResolution":
                continue
            u = prog[name]
            if name == "iChannelResolution":
                u.value = value
            elif u.gl_type in (0x1404, 0x8B56):                 # int, bool
                u.value = int(value)
            else:
                u.value = _floats(value, u.dimension)
        vao.render()
        data = fbo.read(components=4)
        for t in texs:
            t.release()
        return _flip_rows(data, w, h)


class _WebGL:
    """WebGL2 on an OffscreenCanvas – inside Pyodide's web worker."""
    name = "webgl2"

    def __init__(self):
        from js import Object, OffscreenCanvas
        from pyodide.ffi import to_js
        self.to_js = to_js
        self.canvas = OffscreenCanvas.new(16, 16)
        opts = to_js({"preserveDrawingBuffer": True, "premultipliedAlpha": False, "antialias": False},
                     dict_converter=Object.fromEntries)
        gl = self.canvas.getContext("webgl2", opts)
        if gl is None:
            raise ShaderError("Dieser Browser kann kein WebGL2 in Web-Workern (OffscreenCanvas). "
                              "Aktuelles Chrome, Edge, Firefox oder Safari ab 17 verwenden.")
        self.gl = gl
        self.programs: dict = {}
        from js import Float32Array
        self.vbo = gl.createBuffer()
        gl.bindBuffer(gl.ARRAY_BUFFER, self.vbo)
        gl.bufferData(gl.ARRAY_BUFFER, Float32Array.new(to_js([-1, -1, 3, -1, -1, 3])), gl.STATIC_DRAW)

    def renderer(self) -> str:
        return "WebGL2"

    def _compile(self, kind, src):
        gl = self.gl
        sh = gl.createShader(kind)
        gl.shaderSource(sh, src)
        gl.compileShader(sh)
        if not gl.getShaderParameter(sh, gl.COMPILE_STATUS):
            raise _shader_error("Shader-Fehler (Zeilen im Shader-Text)", gl.getShaderInfoLog(sh))
        return sh

    def _program(self, src):
        p = self.programs.get(src)
        if p is not None:
            return p
        gl = self.gl
        prog = gl.createProgram()
        gl.attachShader(prog, self._compile(gl.VERTEX_SHADER, _head(True) + VERTEX))
        gl.attachShader(prog, self._compile(gl.FRAGMENT_SHADER, src))
        gl.bindAttribLocation(prog, 0, "plotart_pos")
        gl.linkProgram(prog)
        if not gl.getProgramParameter(prog, gl.LINK_STATUS):
            raise _shader_error("Shader-Fehler", gl.getProgramInfoLog(prog))
        info = {}
        for i in range(gl.getProgramParameter(prog, gl.ACTIVE_UNIFORMS)):
            u = gl.getActiveUniform(prog, i)
            info[u.name.split("[")[0]] = (u.type, gl.getUniformLocation(prog, u.name))
        p = self.programs[src] = (prog, info)
        return p

    def render(self, source, w, h, uniforms, textures):
        from js import Float32Array, Uint8Array
        gl, to_js = self.gl, self.to_js
        prog, info = self._program(wrap_fragment(source, es=True))
        if self.canvas.width != w or self.canvas.height != h:
            self.canvas.width, self.canvas.height = w, h
        gl.viewport(0, 0, w, h)
        gl.useProgram(prog)
        gl.bindBuffer(gl.ARRAY_BUFFER, self.vbo)
        gl.enableVertexAttribArray(0)
        gl.vertexAttribPointer(0, 2, gl.FLOAT, False, 0, 0)
        texs = []
        for unit, (data, tw, th) in textures.items():
            t = gl.createTexture()
            gl.activeTexture(gl.TEXTURE0 + unit)
            gl.bindTexture(gl.TEXTURE_2D, t)
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, tw, th, 0, gl.RGBA, gl.UNSIGNED_BYTE,
                          to_js(_flip_rows(data, tw, th)))
            for p, v in ((gl.TEXTURE_MIN_FILTER, gl.LINEAR), (gl.TEXTURE_MAG_FILTER, gl.LINEAR),
                         (gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE), (gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)):
                gl.texParameteri(gl.TEXTURE_2D, p, v)
            texs.append(t)
            if f"iChannel{unit}" in info:
                gl.uniform1i(info[f"iChannel{unit}"][1], unit)
        sizes = {gl.FLOAT: 1, gl.FLOAT_VEC2: 2, gl.FLOAT_VEC3: 3, gl.FLOAT_VEC4: 4}
        for name, value in uniforms.items():
            if name not in info or (name.startswith("iChannel") and name != "iChannelResolution"):
                continue
            typ, loc = info[name]
            if name == "iChannelResolution":
                gl.uniform3fv(loc, Float32Array.new(to_js([c for v in value for c in v])))
            elif typ in (gl.INT, gl.BOOL):
                gl.uniform1i(loc, int(value))
            elif typ in sizes:
                v = _floats(value, sizes[typ])
                getattr(gl, f"uniform{sizes[typ]}f")(loc, *(v if isinstance(v, tuple) else (v,)))
        gl.drawArrays(gl.TRIANGLES, 0, 3)
        buf = Uint8Array.new(w * h * 4)
        gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, buf)
        for t in texs:
            gl.deleteTexture(t)
        return _flip_rows(buf.to_bytes(), w, h)


_BACKEND = None


def backend():
    """The GPU backend of this process (created on first use)."""
    global _BACKEND
    if _BACKEND is None:
        _BACKEND = _WebGL() if sys.platform == "emscripten" else _ModernGL()
    return _BACKEND


# ------------------------------------------------------------------------ public objects
class Shader:
    """A fragment shader. Uniform values: sh.set_uniform("zoom", 2) or as keywords when drawing."""

    def __init__(self, source: str, name: str = "Shader"):
        self.source = source
        self.name = name
        self.uniforms: dict = {}

    def __repr__(self):
        return f"<Shader {self.name}>"

    def set_uniform(self, name, value):
        self.uniforms[str(name)] = value
        return self

    setUniform = set_uniform

    def render(self, width: int, height: int, **uniforms) -> bytes:
        """Raw RGBA pixels (top row first) of the shader at width × height."""
        return render(self, width, height, uniforms)


def render(sh: Shader, w: int, h: int, uniforms: dict) -> bytes:
    w, h = max(1, int(round(w))), max(1, int(round(h)))
    if w * h > 8192 * 8192:
        raise ShaderError(f"Shader-Bild zu groß ({w} × {h} Pixel)")
    values = {**sh.uniforms, **uniforms}
    textures, res = {}, [(0.0, 0.0, 1.0)] * MAX_CHANNELS
    for key in list(values):
        m = re.fullmatch(r"iChannel([0-3])", key)
        if m and _is_image(values[key]):
            data, tw, th = image_rgba(values.pop(key))
            textures[int(m.group(1))] = (data, tw, th)
            res[int(m.group(1))] = (float(tw), float(th), 1.0)
    values.setdefault("iResolution", (float(w), float(h), 1.0))
    values["iChannelResolution"] = res
    return backend().render(sh.source, w, h, values, textures)


def to_png(rgba: bytes, w: int, h: int) -> bytes:
    row = w * 4
    return _encode(w, h, 4, (rgba[y * row:(y + 1) * row] for y in range(h)))
