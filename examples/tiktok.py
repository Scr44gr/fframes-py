"""Original portrait scene geometry and one-time audio/subtitle preparation."""

from dataclasses import dataclass
from math import cos, floor, radians, sin
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from examples.assets import files
from examples.subtitles import Caption, captions
from fframes import AudioData, Font, Subtitles, TextLayout

WIDTH, HEIGHT, FPS = 1080, 1920, 60
CAPTION_FONT = Font(family="JetBrains Mono", size=100)


@dataclass(frozen=True)
class Glow:
    """One transformed ellipse and the original absolute filter region."""

    radius: tuple[float, float]
    matrix: tuple[float, float, float, float, float, float]
    region: tuple[float, float, float, float]
    sigma: int
    color: str
    opacity: float = 1


C, S = cos(radians(70)), sin(radians(70))
GLOWS = (
    Glow(
        (311.126, 316.462),
        (C, S, -S, C, 449.658, 652.599),
        (-66.271, 140.76, 1031.86, 1023.68),
        100,
        "#b011e8",
    ),
    Glow(
        (208.812, 211.997),
        (0.00844, 0.99996, -0.99984, 0.01802, 686.793, 1443.34),
        (194.823, 954.499, 983.941, 977.681),
        140,
        "#b310ff",
    ),
    Glow(
        (176.773, 179.55),
        (0.00844, 0.99996, -0.99984, 0.01802, 406.049, 927.243),
        (26.522, 550.447, 759.054, 753),
        100,
        "#ff9900",
        0.5,
    ),
    Glow(
        (379.483, 380.775),
        (C, S, -S, C, 565.155, 1157.97),
        (-15.573, 578.228, 1161.46, 1159.48),
        100,
        "#454acf",
    ),
)


@dataclass(frozen=True)
class Prepared:
    """Shared assets and numeric buffers; no audio work in the rendering loop."""

    assets: dict[str, Path]
    heights: NDArray[np.float32]
    captions: tuple[Caption, ...]
    frames: int


def prepare() -> Prepared:
    """View the native FFT buffer and allocate only the writable bar-height result."""
    assets = files("tiktok")
    audio = AudioData(source=assets["thought"])
    frames = max(1, floor(audio.duration * FPS))
    spectrum = audio.spectrum(frames=frames, fps=FPS, sample_size=32, smooth=4, center=True)
    values = np.frombuffer(spectrum.data, dtype=np.dtype(np.float32).newbyteorder("<")).reshape(
        frames, 16
    )
    heights = np.empty_like(values)
    np.multiply(values, 2000, out=heights)
    np.clip(heights, 30, 400, out=heights)
    layout = TextLayout(fonts=(assets["jetbrains_mono"],))
    lines = captions(
        Subtitles.parse(assets["thought_captions"].read_text(encoding="utf-8")),
        layout,
        CAPTION_FONT,
        1000,
        frames,
        FPS,
    )
    return Prepared(assets, heights, lines, frames)
