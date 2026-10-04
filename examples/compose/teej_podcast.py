"""The chaptered interview as reusable clipped panels and timed text components."""

from pathlib import Path

from examples.teej_podcast import CHAPTERS, FPS, HEIGHT, WIDTH, Chapter, arguments, prepare
from fframes.compose import (
    Audio,
    Clip,
    Composition,
    Image,
    Mask,
    Position,
    Rectangle,
    RenderOptions,
    Samples,
    Stroke,
    Text,
    Video,
    VideoClip,
)


def build(
    family: str = "Berkeley Mono",
    fonts: tuple[Path, ...] = (),
    chapters: tuple[Chapter, ...] = CHAPTERS,
) -> Video:
    """Share panel geometry while retaining independent video and audio timelines."""
    data = prepare(family, fonts, chapters)
    duration = data.frames / FPS
    panels: list[Rectangle | Composition | Audio] = []
    for side, x, source_x, height in zip(
        ("left", "right"),
        (40, 720),
        (-600, 8),
        data.heights,
        strict=True,
    ):
        panels.extend(
            (
                Rectangle(
                    size=(640, 1000),
                    position=Position(x=x, y=40),
                    fill=None,
                    stroke=Stroke(color="#000000", width=10),
                ),
                Composition(
                    position=Position(x=x, y=40),
                    mask=Mask(size=(640, 1000)),
                    children=(
                        Image(
                            source=data.assets[f"teej_{side}_still"],
                            size=(1920, height),
                            fit="contain",
                            position=Position(x=source_x - x, y=-40),
                        ),
                        VideoClip(
                            source=data.assets[f"teej_{side}"],
                            size=(1920, height),
                            fit="contain",
                            position=Position(x=source_x - x, y=-40),
                        ),
                    ),
                ),
                Audio(source=data.assets[f"teej_{side}"]),
            )
        )
    labels: list[Clip] = []
    for i, (chapter, label) in enumerate(zip(chapters, data.labels, strict=True)):
        end = chapters[i + 1].start if i + 1 < len(chapters) else duration
        for start, stop, color in (
            (0, chapter.start, "#ffffff"),
            (chapter.start, end, "#000000"),
            (end, duration, "#ffffff"),
        ):
            stop = min(stop, duration)
            if stop > start:
                labels.append(
                    Text(
                        content=label,
                        font_family="Sofia Sans Semi Condensed",
                        font_size=26,
                        anchor="baseline",
                        baseline="middle",
                        position=Position(x=1410, y=180 + i * 75),
                        fill=color,
                    ).at(start, duration=stop - start)
                )
    return Video(
        resolution=(WIDTH, HEIGHT),
        fps=FPS,
        fonts=data.fonts,
        composition=Composition(
            duration=duration,
            children=(
                Rectangle(size=(WIDTH, HEIGHT), fill="#1a191b"),
                *panels,
                Text(
                    content="2D: Rust",
                    font_family=family,
                    font_size=75,
                    anchor="baseline",
                    baseline="text-before-edge",
                    fill="#ffffff",
                    position=Position(x=1400, y=40),
                ),
                *(
                    Rectangle(
                        size=(490, 60),
                        radius=5,
                        fill="#404040",
                        position=Position(x=1400, y=145 + i * 75),
                    )
                    for i in range(len(chapters))
                ),
                Rectangle(
                    size=(490, 60),
                    radius=5,
                    fill="#ff6900",
                    position=Position(
                        x=1400, y=Samples(values=tuple(145 + y for y in data.highlight), fps=FPS)
                    ),
                ),
                *labels,
            ),
        ),
    )


def main() -> None:
    """Render the chaptered recording with two workers."""
    args = arguments()
    path = Path("output/compose/teej_podcast.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    build(args.family, tuple(args.font)).render(path, options=RenderOptions(concurrency=2))


if __name__ == "__main__":
    main()
