"""Conference splash screens built from text runs, clipped portraits and local scenes."""

from pathlib import Path

from examples.conference import CORNERS, CUT, FPS, HEIGHT, MOTION, WIDTH, arguments, prepare
from fframes.compose import (
    Audio,
    Blur,
    ColorMatrix,
    Composition,
    Filter,
    Image,
    Mask,
    Merge,
    Offset,
    Position,
    Rectangle,
    RenderOptions,
    Stroke,
    Text,
    TextRun,
    VectorPath,
    Video,
)


def build(talk: str = "0") -> Video:
    """Use the same verified sessions and layout as the native example."""
    data = prepare(talk)
    shadow = Filter(
        steps=(
            Blur(result="blur", source="SourceAlpha", sigma=(8, 8)),
            Offset(result="shifted", source="blur", dx=3, dy=3),
            ColorMatrix(
                result="tint",
                source="shifted",
                values=((0, 0, 0, 0, 0), (0, 0, 0, 0, 0), (0, 0, 0, 0, 0), (0, 0, 0, 0.5, 0)),
            ),
            Merge(result="shadow", sources=("tint", "SourceGraphic")),
        )
    )
    intro = Composition(
        duration=CUT / FPS,
        children=(
            Image(source=data.assets["conference_gradient"], size=(WIDTH, HEIGHT)),
            Text(
                content=(
                    TextRun(content="Warsaw ", font_family="Montserrat", font_weight=600),
                    TextRun(content="2025", font_family="JetBrains Mono"),
                ),
                font_size=70,
                anchor="baseline",
                fill="#ffffff",
                position=Position(x=1344, y=MOTION["location_y"]),
                opacity=MOTION["location_opacity"],
            ),
            Text(
                content=(TextRun(content="FUN "), TextRun(content="OCaml", fill="#c24f1e")),
                font_family="Montserrat",
                font_size=200,
                fill="#ffffff",
                anchor="baseline",
                baseline="middle",
                text_anchor="middle",
                position=Position(x=MOTION["title_x"], y=MOTION["title_y"]),
            ),
            VectorPath(
                size=(1140, 828),
                segments=data.camel,
                fill="#562f1f",
                mask=Mask(size=(1140, 828)),
                position=Position(y=250),
                opacity=MOTION["camel_opacity"],
            ),
            Text(
                content="Sponsors and Partners",
                font_family="Inter 18pt",
                font_weight=600,
                font_size=60,
                fill="#d43f00",
                anchor="baseline",
                baseline="middle",
                position=Position(x=960, y=620),
                opacity=MOTION["sponsors_opacity"],
            ),
            Image(
                source=data.assets["sponsors"],
                size=(1150, 1150 * 338 / 1008),
                position=Position(x=720, y=MOTION["sponsors_y"]),
            ),
        ),
    )
    speaker = Composition(
        children=(
            Image(source=data.assets["conference_background"], size=(1920, 1920 * 1164 / 1901)),
            *(
                Text(
                    content=line,
                    font_family=family,
                    font_size=size,
                    font_weight=weight,
                    fill="#ffffff",
                    anchor="baseline",
                    position=Position(x=90, y=y + int(i * size * 1.2)),
                )
                for lines, size, y, family, weight in (
                    (data.title, data.title_size, 350, "Inter 18pt", 800),
                    (data.abstract, data.abstract_size, data.abstract_y, "Inter 24pt", 400),
                )
                for i, line in enumerate(lines)
            ),
            *(
                VectorPath(
                    size=(140, 134),
                    segments=path,
                    position=Position(x=x, y=y),
                    fill=None,
                    stroke=Stroke(
                        color="#fffbfb", width=3, dash=(300,), dash_offset=MOTION["dash"]
                    ),
                )
                for path, x, y in zip(CORNERS, (1000, 40), (250, data.corner_y), strict=True)
            ),
            Composition(
                matrix=(1, data.skew_y, data.skew_x, 1, 0, 0),
                children=(
                    Rectangle(
                        size=(661, 770),
                        radius=60,
                        fill="#525764",
                        position=Position(x=1200, y=162),
                        filter=shadow,
                    ),
                    Image(
                        source=data.assets[data.talk.avatar or "speaker_placeholder"],
                        size=(440, 440),
                        fit="contain",
                        mask=Mask(size=(440, 440), radius=220),
                        position=Position(x=1320, y=250),
                    ),
                    Rectangle(
                        size=(data.speaker_width, 90),
                        radius=20,
                        fill="#ffffff",
                        position=Position(x=1534 - data.speaker_width // 2, y=773),
                    ),
                    Text(
                        content=data.talk.speaker_name,
                        font_family="Inter 24pt",
                        font_size=54,
                        font_weight=700,
                        fill="#d54000",
                        anchor="baseline",
                        baseline="middle",
                        text_anchor="middle",
                        position=Position(x=1534, y=820),
                    ),
                ),
            ),
        )
    )
    return Video(
        resolution=(WIDTH, HEIGHT),
        fps=FPS,
        fonts=data.fonts,
        load_system_fonts=False,
        composition=Composition(
            duration=data.frames / FPS,
            children=(
                intro,
                speaker.at(CUT / FPS),
                Audio(source=data.assets["conference_audio"]),
            ),
        ),
    )


def main() -> None:
    """Render one conference splash screen into output/compose."""
    args = arguments()
    path = Path("output/compose/conference.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    build(args.talk).render(path, options=RenderOptions(concurrency=2))


if __name__ == "__main__":
    main()
