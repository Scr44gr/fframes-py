"""Shared spectrum and cubic spline geometry for the original audio announcement."""

from dataclasses import dataclass
from math import floor
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from examples.assets import files
from examples.subtitles import Caption, captions
from fframes import AudioData, Font, Subtitles, TextLayout

WIDTH, HEIGHT, FPS = 1920, 1080, 30
CAPTION_FONT = Font(family="JetBrains Mono", size=120)


def controls(points: NDArray[np.float32]) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    """Solve the upstream Bezier spline in batches, reusing both result buffers.

    Thomas algorithm from particleincell.com/2012/bezier-splines, as used upstream.
    Rows are independent frames; columns are equally ordered sample positions.
    """
    n = points.shape[1] - 1
    if n < 2:
        raise ValueError("a spline needs at least three points")
    first = np.empty((points.shape[0], n), dtype=np.float32)
    second = np.empty_like(first)
    diagonal = np.full(n, 4, dtype=np.float32)
    diagonal[0], diagonal[-1] = 2, 7
    np.multiply(points[:, 1:], 2, out=first)
    np.multiply(points[:, :-1], 4, out=second)
    np.add(first, second, out=first)
    first[:, 0] = points[:, 0] + 2 * points[:, 1]
    first[:, -1] = 8 * points[:, -2] + points[:, -1]
    for i in range(1, n):
        multiplier = np.float32(2 if i == n - 1 else 1) / diagonal[i - 1]
        diagonal[i] -= multiplier
        np.multiply(first[:, i - 1], multiplier, out=second[:, i])
        np.subtract(first[:, i], second[:, i], out=first[:, i])
    first[:, -1] /= diagonal[-1]
    for i in range(n - 2, -1, -1):
        np.subtract(first[:, i], first[:, i + 1], out=first[:, i])
        first[:, i] /= diagonal[i]
    np.multiply(points[:, 1:-1], 2, out=second[:, :-1])
    np.subtract(second[:, :-1], first[:, 1:], out=second[:, :-1])
    np.add(points[:, -1], first[:, -1], out=second[:, -1])
    second[:, -1] *= 0.5
    return first, second


@dataclass(frozen=True)
class Wave:
    """Precomputed coordinates; array slices used by both authors remain views."""

    x1: NDArray[np.float32]
    x2: NDArray[np.float32]
    y: NDArray[np.float32]
    y1: NDArray[np.float32]
    y2: NDArray[np.float32]
    color: str
    offset: int = 0


def waves(values: NDArray[np.float32]) -> tuple[Wave, ...]:
    """Match all four original wave profiles without copying the FFT source."""
    result = []
    for stride, scale, color, offset in (
        (2, 1200, "#4c20a8", 0),
        (4, 400, "#9370db", 0),
        (6, 1200, "#db2777", 0),
        (7, 1200, "#ea580c", -1600),
    ):
        frequencies = values[:, ::stride] if offset == 0 else values[:, ::-stride]
        points = np.zeros((values.shape[0], frequencies.shape[1] + 2), dtype=np.float32)
        np.multiply(frequencies, scale, out=points[:, 1:-1])
        np.minimum(points, 600, out=points)
        y1, y2 = controls(points)
        x1, x2 = controls(np.arange(points.shape[1], dtype=np.float32)[None, :] * 100)
        for coordinates in (points, y1, y2):
            np.subtract(1080, coordinates, out=coordinates)
        result.append(Wave(x1[0], x2[0], points, y1, y2, color, offset))
    return tuple(result)


@dataclass(frozen=True)
class Prepared:
    """Local assets plus the finite numerical and caption timelines."""

    assets: dict[str, Path]
    frames: int
    waves: tuple[Wave, ...]
    captions: tuple[Caption, ...]


def prepare() -> Prepared:
    """Analyze the soundtrack once and retain the original looping alpha video."""
    assets = files("audio_announce")
    audio = AudioData(source=assets["announce_video"])
    frames = max(1, floor(audio.duration * FPS))
    spectrum = audio.spectrum(frames=frames, fps=FPS, sample_size=512, smooth=4, window="hann")
    values = np.frombuffer(spectrum.data, dtype="<f4").reshape(frames, 256)
    track = Subtitles.parse(assets["announce_captions"].read_text(encoding="utf-8"))
    lines = captions(
        track,
        TextLayout(fonts=(assets["jetbrains_mono"],)),
        CAPTION_FONT,
        1400,
        frames,
        FPS,
        align="left",
    )
    return Prepared(assets, frames, waves(values), lines)
