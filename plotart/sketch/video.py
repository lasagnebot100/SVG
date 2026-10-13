"""Render animated sketches to MP4, WebM, GIF or a PNG sequence."""
from __future__ import annotations

import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Callable

from .animation import Animation
from .export import make_canvas, px_per_unit

FORMATS = {
    "mp4": "MP4-Video (H.264)",
    "webm": "WebM-Video (VP9)",
    "gif": "GIF-Animation",
    "png": "PNG-Sequenz (ZIP)",
}


class ExportError(Exception):
    pass


def find_ffmpeg() -> str | None:
    """ffmpeg from PATH, or the binary bundled with the pip package imageio-ffmpeg."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def capabilities() -> dict:
    """Which export formats work on this machine."""
    ff = find_ffmpeg() is not None
    try:
        import PIL  # noqa: F401
        pil = True
    except ImportError:
        pil = False
    return {"mp4": ff and pil, "webm": ff and pil, "gif": pil, "png": pil, "ffmpeg": ff, "pillow": pil}


class _FFmpegWriter:
    def __init__(self, path: str, w: int, h: int, fps: float, fmt: str, audio: str | None = None):
        exe = find_ffmpeg()
        if not exe:
            raise ExportError("ffmpeg wurde nicht gefunden. Installieren: https://ffmpeg.org/download.html "
                              "oder `pip install imageio-ffmpeg`.")
        args = [exe, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-s", f"{w}x{h}", "-r", f"{fps:g}", "-i", "-"]
        if audio and fmt in ("mp4", "webm"):
            args += ["-i", audio, "-map", "0:v", "-map", "1:a", "-shortest"]
            args += ["-c:a", "aac", "-b:a", "192k"] if fmt == "mp4" else ["-c:a", "libopus", "-b:a", "160k"]
        even = "pad=ceil(iw/2)*2:ceil(ih/2)*2"          # yuv420p needs even dimensions
        if fmt == "mp4":
            args += ["-vf", even, "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                     "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
        elif fmt == "webm":
            args += ["-vf", even, "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "28",
                     "-pix_fmt", "yuv420p", "-row-mt", "1"]
        elif fmt == "gif":
            args += ["-filter_complex",
                     "[0:v]split[a][b];[a]palettegen=stats_mode=diff:max_colors=256[p];"
                     "[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle", "-loop", "0"]
        args.append(path)
        self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    def add(self, rgb_image):
        try:
            self.proc.stdin.write(rgb_image.tobytes())
        except BrokenPipeError:
            self.close()

    def close(self):
        if self.proc.stdin and not self.proc.stdin.closed:
            try:
                self.proc.stdin.close()
            except BrokenPipeError:
                pass
        err = self.proc.stderr.read().decode(errors="replace")
        self.proc.stderr.close()
        if self.proc.wait() != 0:
            raise ExportError(f"ffmpeg-Fehler: {err.strip()[-600:]}")

    def abort(self):
        self.proc.kill()
        self.proc.wait()
        for stream in (self.proc.stdin, self.proc.stderr):
            if stream and not stream.closed:
                stream.close()


class _GifWriter:
    """Pillow fallback when ffmpeg is missing."""

    def __init__(self, path: str, fps: float):
        self.path, self.fps, self.frames = path, fps, []

    def add(self, rgb_image):
        self.frames.append(rgb_image.quantize(colors=256, method=2, dither=1))

    def close(self):
        if self.frames:
            self.frames[0].save(self.path, save_all=True, append_images=self.frames[1:],
                                duration=round(1000 / self.fps), loop=0, optimize=False, disposal=1)

    def abort(self):
        self.frames = []


class _PngZipWriter:
    def __init__(self, path: str, stem: str):
        self.zip = zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED)
        self.stem, self.i = stem, 0

    def add(self, rgba_image):
        import io
        buf = io.BytesIO()
        rgba_image.save(buf, format="PNG", compress_level=3)
        self.zip.writestr(f"{self.stem}_{self.i:05d}.png", buf.getvalue())
        self.i += 1

    def close(self):
        self.zip.close()

    def abort(self):
        self.zip.close()


def _flatten(rgba, background=(255, 255, 255)):
    from PIL import Image
    base = Image.new("RGB", rgba.size, background)
    base.paste(rgba, mask=rgba.getchannel("A"))
    return base


def export_animation(source: str, out_path: str, fmt: str = "mp4", params: dict | None = None,
                     seed: int = 1, scale: float | None = None, frames: int | None = None,
                     fps: float | None = None, engine: str = "auto",
                     progress: Callable[[int, int], None] | None = None,
                     should_stop: Callable[[], bool] | None = None, with_audio: bool = True) -> dict:
    """Render all frames of an animated sketch into a video/GIF/PNG-ZIP.

    Returns {"path", "frames", "fps", "width", "height", "bytes"}. Raises ExportError.
    """
    if fmt not in FORMATS:
        raise ExportError(f"Unbekanntes Format {fmt!r}. Möglich: {', '.join(FORMATS)}")
    anim = Animation(source, params, seed, frames=frames, fps=fps)
    if anim.error:
        raise ExportError(_err_text(anim.error))
    if not anim.animated:
        raise ExportError("Die Skizze ist nicht animiert – definiere draw() (ohne no_loop()).")
    scale = scale or px_per_unit(anim.sk, dpi=96)
    canvas = make_canvas(anim.sk, scale, engine)
    w, h = canvas.W, canvas.H
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if fmt in ("mp4", "webm") or (fmt == "gif" and find_ffmpeg()):
        audio = None
        if with_audio and fmt in ("mp4", "webm") and anim.sk.audio_sources:
            from .audio import audio_file
            audio = str(audio_file(anim.sk.audio_sources[0]))   # the first loaded sound is the soundtrack
        writer = _FFmpegWriter(str(out), w, h, anim.fps, fmt, audio)
    elif fmt == "gif":
        writer = _GifWriter(str(out), anim.fps)
    else:
        writer = _PngZipWriter(str(out), out.stem)
    total = anim.total
    try:
        while True:
            if should_stop and should_stop():
                writer.abort()
                raise ExportError("Export abgebrochen.")
            fr = anim.next_frame()
            if fr is None:
                break
            if fr.error:
                writer.abort()
                raise ExportError(f"Fehler in Bild {fr.index + 1}: {_err_text(fr.error)}")
            if fr.clears:
                canvas.clear()
            canvas.draw(fr.items)
            img = canvas.image()
            writer.add(img if fmt == "png" else _flatten(img))
            if progress:
                progress(fr.index + 1, total)
        writer.close()
    except ExportError:
        if out.exists():
            out.unlink()
        raise
    return {"path": str(out), "frames": total, "fps": anim.fps, "width": w, "height": h,
            "bytes": os.path.getsize(out)}


def _err_text(err: dict) -> str:
    line = f"Zeile {err['line']}: " if err.get("line") else ""
    return line + err["message"]
