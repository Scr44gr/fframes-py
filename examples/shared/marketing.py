"""Original marketing artwork, native spring samples and audio-driven bar heights."""

import argparse
import re
from dataclasses import dataclass
from math import floor
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from examples.assets import files
from examples.shared.shaders import keyframe
from fframes import (
    AudioData,
    Font,
    Keyframe,
    Samples,
    Spring,
    Subtitles,
    TextLayout,
    Tween,
    compile_animation,
)

WIDTH, HEIGHT, FPS = 1920, 1080, 60
SPRING = Spring(mass=1.85, stiffness=130, damping=16)
PALETTE = (
    (6, 6, "#ec4899", "#f43f5e"),
    (0, 3, "#d946ef", "#9333ea"),
    (5, 5, "#facc15", "#f97316"),
    (1, 7, "#38bdf8", "#6366f1"),
    (4, 4, "#4ade80", "#06b6d4"),
    (2, 2, "#22d3ee", "#0ea5e9"),
    (3, 1, "#ffffff", "#ffffff"),
)
ARROW = (
    "M-2.19 -1.63 C8.29 53.64,-34.21 264.71,62.09 331.05 "
    "C158.39 397.38,490.59 385.91,575.58 396.36",
    "M544.61 406.42 C552.39 404.4,562.6 396.92,572.02 395.84",
    "M545.58 385.92 C553.02 389.43,562.97 387.49,572.02 395.84",
)
BOUNCES = (
    "M505,55c0-27.6-22.4-50-50-50s-50,22.4-50,50"
    "c0-27.6-22.4-50-50-50s-50,22.4-50,50c0-27.6-22.4-50-50-50s-50,22.4-50,50"
    "c0-27.6-22.4-50-50-50s-50,22.4-50,50c0-27.6-22.4-50-50-50S5,27.4,5,55"
)
SPARKS = (
    "M549.7,46.6l-21.8,12.6 M531.9,25.8l-12.6,21.8 M504.2,18.3v25.1 "
    "M476.4,25.8L489,47.6 M458.7,46.6l21.8,12.6"
)
MOTION = {
    "wipe": Tween(from_value=0, to_value=1200, start_at=16.2, duration=0.3),
    "bounce": Tween(from_value=-700, to_value=41, start_at=16.3, duration=2.5),
    "spark_opacity": Tween(from_value=1, to_value=0.55, start_at=18.6, duration=0.3),
    "spark_offset": Tween(from_value=-40, to_value=0, start_at=18.7, duration=0.3),
    "spark_length": Tween(from_value=30, to_value=12, start_at=18.7, duration=0.3),
}


@dataclass(frozen=True)
class PathData:
    """One Ferris contour with its source transform and paint reference."""

    path: str
    fill: str
    matrix: tuple[float, float, float, float, float, float]


@dataclass(frozen=True)
class Prepared:
    """Shared scene data, with exactly one writable spectrum-height allocation."""

    assets: dict[str, Path]
    fonts: tuple[Path, ...]
    frames: int
    heights: NDArray[np.float32]
    paths: tuple[PathData, ...]
    gradients: str
    captions: tuple[str, ...]
    motion: dict[str, Samples]


def prepare(family: str, fonts: tuple[Path, ...]) -> Prepared:
    """Load verified assets and resolve finite animation curves once."""
    assets = files("marketing")
    fonts = (assets["bubble"], *fonts)
    TextLayout(fonts=fonts, load_system_fonts=True).width("Marketing", Font(family=family))
    audio = AudioData(source=assets["marketing_audio"])
    frames = floor(
        max(
            audio.duration,
            6 + AudioData(source=assets["marketing_woosh"]).duration,
            16 + AudioData(source=assets["marketing_end"]).duration,
        )
        * FPS
    )
    spectrum = audio.spectrum(
        frames=frames, fps=FPS, sample_size=16, smooth=3, window="hamming_legacy"
    )
    values = np.frombuffer(spectrum.data, dtype="<f4").reshape(frames, 8)
    heights = np.empty_like(values)
    np.multiply(values, 60, out=heights)
    np.clip(heights, 96, 720, out=heights)
    source = assets["marketing_art"].read_text(encoding="utf-8").split("const PRETTY_SPECTRUM")[0]
    matches = re.findall(
        r'<g\s+transform=(.*?)>\s*<path\s+d="([^"]+)"\s+(.*?)/>\s*</g>', source, re.S
    )
    paths = []
    for index, (transform, path, attributes) in enumerate(matches):
        if transform.startswith('"matrix('):
            numbers = tuple(map(float, transform.split("(", 1)[1].split(")", 1)[0].split(",")))
            a, b, c, d, e, f = numbers
        elif index == 8:
            a, b, c, d, e, f = 1.0, 0.0, 0.0, 1.0, 727.0, 435.209
        elif index == 10:
            a, b, c, d, e, f = 1.0, 0.0, 0.0, 1.0, 520.0, 436.428
        else:
            raise ValueError("unexpected Ferris transform")
        paint = re.search(r'(?:fill="|fill:)([^";]+)', attributes)
        fill = paint[1] if paint else "#000000"
        if fill.startswith("rgb("):
            fill = "#" + "".join(f"{int(v):02x}" for v in fill[4:-1].split(","))
        if fill == "white":
            fill = "#ffffff"
        paths.append(PathData(path, fill, (a, b, c, d, e, f)))
    if len(paths) != 12:
        raise ValueError("pinned Ferris artwork must have twelve paths")
    gradients = "<defs>" + source.split("<defs>", 1)[1].split("</defs>", 1)[0] + "</defs>"
    track = Subtitles.parse(assets["marketing_captions"].read_text(encoding="utf-8"))
    captions = tuple(
        next(
            (
                cue.text
                for cue in reversed(track.cues)
                if round(cue.start * 1000) <= i * 1000 // FPS <= round(cue.end * 1000)
            ),
            "",
        )
        for i in range(frames)
    )

    def sample(keys: tuple[Keyframe, ...]) -> Samples:
        return Samples(
            values=tuple(compile_animation(keys).sample_many(range(frames), FPS)), fps=FPS
        )

    motion = {name: sample((keyframe(value),)) for name, value in MOTION.items()}
    motion["ferris"] = sample(
        (
            Keyframe(start=2.3, end=4.8, from_value=1400, to_value=770, easing=SPRING),
            Keyframe(start=4.8, end=14.8, from_value=770, to_value=1400, easing=SPRING),
        )
    )
    motion["eye"] = sample(
        (
            Keyframe(start=3.4, end=3.65, from_value=0, to_value=50),
            Keyframe(start=4.1, end=4.35, from_value=50, to_value=0),
        )
    )
    arrow = sample(
        (
            Keyframe(start=5.8, end=9, from_value=0, to_value=1, easing=SPRING),
            Keyframe(start=9, end=19, from_value=1, to_value=0, easing=SPRING),
        )
    )
    motion["arrow"] = Samples(values=tuple(max(0.0, min(1.0, a)) for a in arrow.values), fps=FPS)
    code_spring = Spring(mass=0.85, stiffness=80, damping=16)
    motion["code"] = sample(
        (
            Keyframe(start=5.8, end=9, from_value=-1000, to_value=40, easing=code_spring),
            Keyframe(start=9, end=19, from_value=40, to_value=-1200, easing=code_spring),
        )
    )
    for position, _index, _first, _last in PALETTE:
        motion[f"bar_{position}"] = sample(
            (
                Keyframe(
                    start=16, end=26, from_value=544 + position * 116, to_value=944, easing=SPRING
                ),
            )
        )
    return Prepared(assets, fonts, frames, heights, tuple(paths), gradients, captions, motion)


class Arguments(argparse.Namespace):
    """Choose an explicit replacement for the system-only Chalkboard SE font."""

    family: str
    font: list[Path]


def arguments() -> Arguments:
    """Share font configuration between the two ports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", default="Chalkboard SE")
    parser.add_argument("--font", type=Path, action="append", default=[])
    return parser.parse_args(namespace=Arguments())
