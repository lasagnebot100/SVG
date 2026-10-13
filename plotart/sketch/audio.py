"""Audio-reactive sketches: load a sound file and read level, spectrum and beats per frame.

    musik = load_audio("song.mp3")       # WAV directly, everything else via ffmpeg
    def draw():
        background(0)
        circle(width / 2, height / 2, 100 + 300 * musik.level())
        for i, v in enumerate(musik.spectrum(32)): …
        if musik.beat(): …

All analysis is deterministic and frame based (time = frame / fps), so a video
export shows exactly what the preview showed – and the sound is muxed into MP4/WebM.
Pure Python; numpy speeds up the FFT when available.
"""
from __future__ import annotations

import array
import cmath
import io
import math
import os
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

from .data import SAMPLE_PREFIX, DataError, resolve

RATE = 22050                     # analysis sample rate (mono)
WINDOW = 1024                    # FFT window (~46 ms)
SAMPLES = ("beat.wav",)
_CACHE: dict = {}


# ------------------------------------------------------------------------ decoding
def _decode_wav(data: bytes) -> tuple[array.array, int]:
    with wave.open(io.BytesIO(data)) as w:
        ch, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if width == 1:
        vals = [(b - 128) / 128 for b in raw]
    elif width == 2:
        a = array.array("h")
        a.frombytes(raw[: len(raw) // 2 * 2])
        if struct.pack("=h", 1) != struct.pack("<h", 1):
            a.byteswap()
        vals = [v / 32768 for v in a]
    elif width == 3:
        vals = [int.from_bytes(raw[i:i + 3], "little", signed=True) / 8388608 for i in range(0, len(raw) - 2, 3)]
    elif width == 4:
        a = array.array("i")
        a.frombytes(raw[: len(raw) // 4 * 4])
        if struct.pack("=i", 1) != struct.pack("<i", 1):
            a.byteswap()
        vals = [v / 2147483648 for v in a]
    else:
        raise DataError(f"WAV mit {width * 8} Bit wird nicht unterstützt")
    if ch > 1:
        vals = [sum(vals[i:i + ch]) / ch for i in range(0, len(vals) - ch + 1, ch)]
    return _resample(vals, rate), RATE


def _resample(vals, rate) -> array.array:
    if rate == RATE:
        return array.array("f", vals)
    step = rate / RATE
    n = int(len(vals) / step)
    out = array.array("f", bytes(4 * n))
    for i in range(n):
        x = i * step
        k = int(x)
        f = x - k
        a = vals[k]
        b = vals[k + 1] if k + 1 < len(vals) else a
        out[i] = a + (b - a) * f
    return out


def _decode_ffmpeg(path: Path) -> tuple[array.array, int]:
    from .video import find_ffmpeg
    exe = find_ffmpeg()
    if not exe:
        raise DataError(f"{path.name}: Für MP3/OGG/… wird ffmpeg gebraucht (oder die Datei als WAV speichern). "
                        "Installieren: https://ffmpeg.org/download.html oder `pip install imageio-ffmpeg`.")
    res = subprocess.run([exe, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"],
                         capture_output=True)
    if res.returncode != 0:
        raise DataError(f"{path.name} konnte nicht gelesen werden: {res.stderr.decode(errors='replace')[-300:]}")
    a = array.array("h")
    a.frombytes(res.stdout[: len(res.stdout) // 2 * 2])
    return array.array("f", (v / 32768 for v in a)), RATE


def sample_wav(name: str) -> bytes:
    """Built-in synthetic music: 'beat.wav' – 8 s, 120 BPM, kick + hi-hat + bass line."""
    if name != "beat.wav":
        raise DataError(f"Unbekanntes Beispiel '{SAMPLE_PREFIX}{name}'. Möglich: "
                        + ", ".join(SAMPLE_PREFIX + s for s in SAMPLES))
    rate, dur, bpm = RATE, 8.0, 120
    n = int(rate * dur)
    beat = 60 / bpm
    out = array.array("h", bytes(2 * n))
    notes = [55.0, 55.0, 65.41, 49.0]                 # A1 A1 C2 G1 – one per bar
    seed = 12345
    for i in range(n):
        t = i / rate
        tb = t % beat
        kick = math.sin(math.tau * (50 + 120 * math.exp(-tb * 30)) * tb) * math.exp(-tb * 9)
        th = (t + beat / 2) % beat
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        hat = ((seed / 0x7FFFFFFF) * 2 - 1) * math.exp(-th * 60) * 0.25
        f = notes[int(t / (beat * 4)) % len(notes)]
        bass = 0.25 * math.sin(math.tau * f * t) * (0.6 + 0.4 * math.exp(-tb * 4))
        chord = 0.05 * (math.sin(math.tau * f * 4 * t) + math.sin(math.tau * f * 5.04 * t))
        v = 0.7 * kick + hat + bass + chord
        out[i] = int(max(-1, min(1, v * 0.8)) * 32767)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(out.tobytes())
    return buf.getvalue()


def audio_file(name: str) -> Path:
    """Path of an audio file for playback/muxing (samples are written to a temp file once)."""
    if name.startswith(SAMPLE_PREFIX):
        key = name[len(SAMPLE_PREFIX):]
        p = Path(tempfile.gettempdir()) / f"plotart_beispiel_{key}"
        if not p.exists():
            p.write_bytes(sample_wav(key))
        return p
    return resolve(name)


# ------------------------------------------------------------------------ analysis
def _fft_mag(frame: list) -> list:
    """Magnitudes of the positive-frequency FFT bins (len = N/2)."""
    try:
        import numpy as np
        return list(np.abs(np.fft.rfft(np.asarray(frame, dtype=float)))[: len(frame) // 2])
    except ImportError:
        pass
    n = len(frame)
    a = [complex(v) for v in frame]
    j = 0                                          # iterative radix-2
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    size = 2
    while size <= n:
        w = cmath.exp(-2j * math.pi / size)
        half = size // 2
        for start in range(0, n, size):
            wk = 1
            for k in range(half):
                u, v = a[start + k], a[start + k + half] * wk
                a[start + k], a[start + k + half] = u + v, u - v
                wk *= w
        size *= 2
    return [abs(c) for c in a[: n // 2]]


_HANN = [0.5 - 0.5 * math.cos(math.tau * i / (WINDOW - 1)) for i in range(WINDOW)]


class Audio:
    """A loaded sound. Values are 0–1 and refer to the current frame unless `time` is given."""

    def __init__(self, samples: array.array, rate: int, name: str, sketch=None):
        self.samples, self.rate, self.name, self._sk = samples, rate, name, sketch
        self.duration = len(samples) / rate
        self._spec_cache: dict = {}
        # loudness reference: 98th percentile of block RMS (robust against single peaks)
        blocks = []
        step = max(1, rate // 20)
        for i in range(0, max(1, len(samples) - step), step):
            seg = samples[i:i + step]
            blocks.append(math.sqrt(sum(v * v for v in seg) / max(1, len(seg))))
        blocks.sort()
        self._ref = (blocks[int(len(blocks) * 0.98)] if blocks else 0) or 1e-9
        self._spec_ref: dict = {}
        self._low_env = None
        self._onset_cache: dict = {}

    def __repr__(self):
        return f"<Audio {self.name} {self.duration:.1f} s>"

    # ------------------------------------------------------------- time
    def _t(self, time):
        if time is not None:
            return float(time)
        ns = self._sk.ns if self._sk is not None else None
        return float(ns.get("time", 0.0)) if ns else 0.0

    def frames(self, fps: float = 30) -> int:
        """Number of frames the sound lasts at `fps`."""
        return max(1, math.ceil(self.duration * fps))

    def _window(self, t, size):
        c = int(t * self.rate)
        a = max(0, c - size // 2)
        seg = list(self.samples[a:a + size])
        return seg + [0.0] * (size - len(seg))

    # ------------------------------------------------------------- values
    def level(self, time=None, smooth: float = 1.0) -> float:
        """Loudness 0–1 (RMS over ~1 frame; smooth > 1 averages over more frames)."""
        fps = self._fps()
        size = max(64, int(self.rate / fps * smooth))
        seg = self._window(self._t(time), size)
        rms = math.sqrt(sum(v * v for v in seg) / size)
        return min(1.0, rms / self._ref)

    def _fps(self):
        ns = self._sk.ns if self._sk is not None else None
        return float(ns.get("fps", 30.0)) if ns else 30.0

    def _mags(self, t):
        key = round(t * self.rate / 256)                 # cache per ~12 ms
        m = self._spec_cache.get(key)
        if m is None:
            seg = self._window(t, WINDOW)
            m = _fft_mag([v * w for v, w in zip(seg, _HANN)])
            if len(self._spec_cache) > 4096:
                self._spec_cache.clear()
            self._spec_cache[key] = m
        return m

    def _band(self, mags, lo, hi):
        hz = self.rate / WINDOW
        a = max(1, int(lo / hz))
        b = max(a + 1, int(hi / hz))
        seg = mags[a:b]
        return math.sqrt(sum(v * v for v in seg) / len(seg)) if seg else 0.0

    def _ref_for(self, key, lo, hi):
        ref = self._spec_ref.get(key)
        if ref is None:                                 # loudest 2 % of the piece in this band
            vals = sorted(self._band(self._mags(t), lo, hi)
                          for t in (i * 0.25 for i in range(max(1, int(self.duration * 4)))))
            ref = self._spec_ref[key] = (vals[int(len(vals) * 0.98)] if vals else 0) or 1e-9
        return ref

    def spectrum(self, bands: int = 16, time=None, lo: float = 40.0, hi: float = 10000.0) -> list:
        """Energy in `bands` logarithmic frequency bands (bass first), each 0–1."""
        mags = self._mags(self._t(time))
        edges = [lo * (hi / lo) ** (i / bands) for i in range(bands + 1)]
        out = []
        for i in range(bands):
            ref = self._ref_for(("s", bands, i, lo, hi), edges[i], edges[i + 1])
            out.append(min(1.0, self._band(mags, edges[i], edges[i + 1]) / ref))
        return out

    def energy(self, lo: float, hi: float, time=None) -> float:
        """Energy between lo and hi Hz, 0–1."""
        return min(1.0, self._band(self._mags(self._t(time)), lo, hi) / self._ref_for(("e", lo, hi), lo, hi))

    def bass(self, time=None) -> float:
        """Tiefen (40–250 Hz), 0–1."""
        return self.energy(40, 250, time)

    def mid(self, time=None) -> float:
        """Mitten (250–2000 Hz), 0–1."""
        return self.energy(250, 2000, time)

    def treble(self, time=None) -> float:
        """Höhen (2–10 kHz), 0–1."""
        return self.energy(2000, 10000, time)

    def _onsets(self, sensitivity):
        """Peak-picked onsets of the low band (one-pole low-pass ~150 Hz, flux per 256 samples)."""
        key = round(sensitivity, 3)
        cached = self._onset_cache.get(key)
        if cached is not None:
            return cached
        if self._low_env is None:
            a = math.exp(-math.tau * 150 / self.rate)
            y, hop, env, acc, k = 0.0, 256, [], 0.0, 0
            for v in self.samples:
                y = (1 - a) * v + a * y
                acc += y * y
                k += 1
                if k == hop:
                    env.append(math.sqrt(acc / hop))
                    acc, k = 0.0, 0
            self._low_env = env
        env = self._low_env
        flux = [0.0] + [max(0.0, env[i] - env[i - 1]) for i in range(1, len(env))]
        top = max(flux) if flux else 0.0
        win = int(self.rate / 256)                       # ±1 s
        peaks = []
        for i in range(len(flux)):
            f = flux[i]
            if f <= 0.1 * top or f < max(flux[max(0, i - 3):i + 4]):
                continue
            seg = flux[max(0, i - win):i + win]
            t = i * 256 / self.rate
            if f > sensitivity * 2 * (sum(seg) / len(seg)) and (not peaks or t - peaks[-1] > 0.2):
                peaks.append(t)                          # at most one beat per 0.2 s (≤ 300 BPM)
        self._onset_cache[key] = peaks
        return peaks

    def beats(self, sensitivity: float = 1.4) -> list:
        """Times (s) of all detected beats in the whole sound."""
        return list(self._onsets(sensitivity))

    def beat(self, time=None, sensitivity: float = 1.4) -> bool:
        """True in the frame in which a beat (bass onset) happens; higher sensitivity = fewer beats."""
        t = self._t(time)
        dt = 1 / self._fps()
        return any(t - dt < b <= t + 1e-9 for b in self._onsets(sensitivity))

    def since_beat(self, time=None, sensitivity: float = 1.4) -> float:
        """Seconds since the last beat (large number before the first one) – good for decaying flashes."""
        t = self._t(time)
        past = [b for b in self._onsets(sensitivity) if b <= t + 1e-9]
        return t - past[-1] if past else 1e9

    def waveform(self, n: int = 256, time=None) -> list:
        """n samples (−1…1) around the current moment – for oscilloscope drawings."""
        size = max(n, int(self.rate / self._fps()))
        seg = self._window(self._t(time), size)
        return [seg[int(i * size / n)] for i in range(n)]


def load_audio(name: str, sketch=None) -> Audio:
    """WAV directly, MP3/OGG/FLAC/M4A via ffmpeg; 'beispiel:beat.wav' is built in."""
    if name.startswith(SAMPLE_PREFIX):
        key = ("sample", name)
        if key not in _CACHE:
            _CACHE[key] = _decode_wav(sample_wav(name[len(SAMPLE_PREFIX):]))
        samples, rate = _CACHE[key]
        return Audio(samples, rate, name, sketch)
    path = resolve(name)
    key = (str(path), os.path.getmtime(path))
    if key not in _CACHE:
        if path.suffix.lower() == ".wav":
            try:
                _CACHE[key] = _decode_wav(path.read_bytes())
            except (wave.Error, EOFError):
                _CACHE[key] = _decode_ffmpeg(path)     # e.g. float or compressed WAV
        else:
            _CACHE[key] = _decode_ffmpeg(path)
        while len(_CACHE) > 8:
            _CACHE.pop(next(iter(_CACHE)))
    samples, rate = _CACHE[key]
    return Audio(samples, rate, name, sketch)
