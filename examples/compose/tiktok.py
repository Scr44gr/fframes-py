"""The original goose clip composed from ellipses, sampled bars and caption intervals."""

from pathlib import Path

from examples.shared.tiktok import FPS, GLOWS, HEIGHT, WIDTH, prepare
from fframes.compose import (
    Audio,
    Blur,
    Composition,
    Ellipse,
    Filter,
    Image,
    Position,
    Rectangle,
    Samples,
    Text,
    Video,
)


def build() -> Video:
    """Compile the portrait scene with batch FFT and reusable text layers."""
    data = prepare()
    return Video(
        resolution=(WIDTH, HEIGHT),
        fps=FPS,
        fonts=(data.assets["jetbrains_mono"],),
        load_system_fonts=False,
        composition=Composition(
            duration=data.frames / FPS,
            children=(
                Rectangle(size=(WIDTH, HEIGHT)),
                *(
                    Composition(
                        opacity=glow.opacity,
                        filter=Filter(
                            units="user",
                            color_space="srgb",
                            region=glow.region,
                            steps=(Blur(result="blur", sigma=(glow.sigma, glow.sigma)),),
                        ),
                        children=(
                            Ellipse(
                                size=(glow.radius[0] * 2, glow.radius[1] * 2),
                                position=Position(x=-glow.radius[0], y=-glow.radius[1]),
                                matrix=glow.matrix,
                                fill=glow.color,
                            ),
                        ),
                    )
                    for glow in GLOWS
                ),
                *(
                    Rectangle(
                        size=(30, Samples(values=tuple(map(float, data.heights[:, i])), fps=FPS)),
                        position=Position(
                            x=150 + i * 50,
                            y=Samples(
                                values=tuple(300 - float(h) / 2 for h in data.heights[:, i]),
                                fps=FPS,
                            ),
                        ),
                        radius=15,
                        fill="#ffffff",
                    )
                    for i in range(16)
                ),
                *(
                    Composition(
                        children=tuple(
                            Text(
                                content=line,
                                position=Position(x=40 + dx, y=652.8 + j * 120),
                                font_family="JetBrains Mono",
                                font_size=100,
                                fill="#ffffff",
                                anchor="baseline",
                            )
                            for j, (line, dx) in enumerate(caption.lines)
                        )
                    ).at(caption.start / FPS, duration=(caption.end - caption.start) / FPS)
                    for caption in data.captions
                ),
                Image(
                    source=data.assets["goose"],
                    size=(950, 950),
                    fit="contain",
                    position=Position(x=140, y=970),
                ),
                Audio(source=data.assets["thought"]),
            ),
        ),
    )


def main() -> None:
    """Render the original portrait clip into output/compose."""
    path = Path("output/compose/tiktok.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    build().render(path)


if __name__ == "__main__":
    main()
