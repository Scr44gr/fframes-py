"""Bind the six unmodified upstream programs to precomputed scene uniforms."""

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from examples.intro.drawing import BONE, FPS, ORANGE, Box, N, Number, Painter
from fframes import (
    ColorUniform,
    FloatUniform,
    ImageUniform,
    Samples,
    Shader,
    VectorUniform,
    VideoUniform,
)

if TYPE_CHECKING:
    from fframes.shaders import Uniform
from fframes.values import Scalar


def scalar(value: Number, padding: int = 0) -> Scalar:
    """Transfer final values once; constant sequences avoid allocating native timelines."""
    if isinstance(value, float | int):
        return float(value)
    if value.ndim == 0 or np.all(value == value[0]):
        return float(value.flat[0])
    values = tuple(map(float, value))
    if padding:
        values = (values[0],) * padding + values
    return Samples(values=values, fps=FPS)


def effect(
    p: Painter[N],
    name: str,
    floats: dict[str, Number],
    colors: dict[str, str],
    *,
    vectors: dict[str, tuple[Number, Number]] | None = None,
    image: Path | None = None,
    video: Path | None = None,
    box: Box = (0, 0, 1920, 1080),
) -> N:
    """Keep global shader time continuous when a three-frame glitch reuses a scene."""
    padding = p.window.first - p.window.scene_first
    uniforms: list[Uniform] = [
        FloatUniform(name=k, value=scalar(v, padding)) for k, v in floats.items()
    ]
    uniforms.extend(ColorUniform(name=k, value=v) for k, v in colors.items())
    uniforms.extend(
        VectorUniform(name=k, value=(scalar(x, padding), scalar(y, padding)))
        for k, (x, y) in (vectors or {}).items()
    )
    if image is not None:
        uniforms.append(ImageUniform(name="iChannel0", source=image))
    if video is not None:
        uniforms.append(VideoUniform(name="iChannel0", source=video, loop=True))
    return p.shader(
        Shader(
            source=p.assets[f"intro_{name}_sksl"].read_text(encoding="utf-8"),
            uniforms=tuple(uniforms),
            time_offset=padding / FPS,
        ),
        box,
    )


def contour(
    p: Painter[N], well: tuple[Number, Number], depth: float, density: float, bright: Number
) -> N:
    """Render the original topographic backdrop."""
    return effect(
        p,
        "contour",
        {"uDepth": depth, "uDensity": density, "uBright": bright},
        {"uInk": "#8a857c", "uHot": ORANGE},
        vectors={"uWell": well},
    )


def grid(p: Painter[N], speed: float, horizon: float, bright: Number) -> N:
    """Render the perspective grid used by the benchmark, preview and render scenes."""
    return effect(
        p,
        "grid",
        {"uSpeed": speed, "uHorizon": horizon, "uBright": bright},
        {"uInk": "#6f6a63", "uHot": ORANGE},
    )


def tunnel(p: Painter[N]) -> N:
    """Keep the tunnel's explicit global time through scene changes."""
    return effect(
        p, "tunnel", {"uT": p.seconds, "uSpeed": 3, "uGlow": 1}, {"uHot": ORANGE, "uBone": BONE}
    )


def guest(p: Painter[N], box: Box, halftone: Number) -> N:
    """Chroma-key the synchronized guest and optionally turn it into a halftone print."""
    return effect(
        p,
        "key",
        {"uHalftone": halftone, "uCell": 9, "uAlpha": 1},
        {"uInk": ORANGE, "uPaper": BONE},
        vectors={"uImg": (1280, 720)},
        video=p.assets["intro_right_clip_mp4"],
        box=box,
    )
