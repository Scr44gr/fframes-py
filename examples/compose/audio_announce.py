"""The announcement built with sampled cubic curves, filter graphs and video layers."""

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from examples.shared.audio_announce import FPS, HEIGHT, WIDTH, Wave, prepare
from fframes.compose import (
    Audio,
    Blur,
    Close,
    ColorMatrix,
    Composite,
    Composition,
    CubicTo,
    Filter,
    Image,
    Merge,
    MoveTo,
    Position,
    RenderOptions,
    Samples,
    Stroke,
    Text,
    VectorPath,
    Video,
    VideoClip,
)

GLOW = Filter(
    units="user",
    region=(-192, -108, 2304, 1296),
    color_space="srgb",
    steps=(
        ColorMatrix(
            result="hard",
            source="SourceAlpha",
            values=(
                (0, 0, 0, 0, 0),
                (0, 0, 0, 0, 0),
                (0, 0, 0, 0, 0),
                (0, 0, 0, 127, 0),
            ),
        ),
        Blur(result="blur", source="hard", sigma=(18.3, 18.3)),
        Composite(result="outside", source="blur", destination="hard", operator="out"),
        ColorMatrix(
            result="tint",
            source="outside",
            values=(
                (0, 0, 0, 0, 0.654173),
                (0, 0, 0, 0, 0.116095),
                (0, 0, 0, 0, 0.56808),
                (0, 0, 0, 1, 0),
            ),
        ),
        Merge(result="output", sources=("tint", "SourceGraphic")),
    ),
)


def sample(column: NDArray[np.float32]) -> Samples:
    """Transfer a column once; subsequent geometry evaluation stays in Rust."""
    return Samples(values=tuple(map(float, column)), fps=FPS)


def wave_path(wave: Wave) -> VectorPath:
    """Keep the spline topology static while its vertical control points animate."""
    return VectorPath(
        size=(WIDTH, HEIGHT),
        fill=wave.color,
        stroke=Stroke(color="#ffffff", width=6),
        position=Position(x=wave.offset),
        segments=(
            MoveTo(x=0, y=1080),
            *(
                CubicTo(
                    control1=(float(x1), sample(wave.y1[:, i])),
                    control2=(float(x2), sample(wave.y2[:, i])),
                    end=((i + 1) * 100, sample(wave.y[:, i + 1])),
                )
                for i, (x1, x2) in enumerate(zip(wave.x1, wave.x2, strict=True))
            ),
            Close(),
        ),
    )


def build() -> Video:
    """Compile the full soundtrack, looping avatar and timed caption groups."""
    data = prepare()
    return Video(
        resolution=(WIDTH, HEIGHT),
        fps=FPS,
        fonts=(data.assets["jetbrains_mono"],),
        load_system_fonts=False,
        composition=Composition(
            duration=data.frames / FPS,
            children=(
                Image(
                    source=data.assets["announce_background"], size=(WIDTH, HEIGHT), fit="contain"
                ),
                *(
                    Composition(
                        filter=GLOW,
                        children=tuple(
                            Text(
                                content=line,
                                font_family="JetBrains Mono",
                                font_size=120,
                                anchor="baseline",
                                baseline="middle",
                                fill="#ffffff",
                                stroke=Stroke(color="#ff208b", width=1),
                                position=Position(x=450, y=170 + j * 144),
                            )
                            for j, (line, _) in enumerate(caption.lines)
                        ),
                    ).at(caption.start / FPS, duration=(caption.end - caption.start) / FPS)
                    for caption in data.captions
                ),
                Composition(
                    filter=GLOW,
                    children=(
                        VideoClip(
                            source=data.assets["announce_avatar"],
                            size=(300, 300),
                            loop=True,
                            position=Position(x=80, y=100),
                        ),
                    ),
                ),
                Composition(opacity=0.5, children=tuple(map(wave_path, data.waves))),
                Audio(source=data.assets["announce_video"]),
            ),
        ),
    )


def main() -> None:
    """Export the complete announcement into output/compose."""
    destination = Path("output/compose/audio_announce.mp4")
    destination.parent.mkdir(parents=True, exist_ok=True)
    build().render(destination, options=RenderOptions(concurrency=2))


if __name__ == "__main__":
    main()
