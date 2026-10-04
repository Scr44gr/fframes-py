"""Marketing animation using gradients, reusable paths and sampled native effects."""

from pathlib import Path
from typing import TYPE_CHECKING

from examples.marketing import (
    ARROW,
    BOUNCES,
    FPS,
    HEIGHT,
    PALETTE,
    SPARKS,
    WIDTH,
    Prepared,
    arguments,
    prepare,
)
from fframes.compose import (
    Audio,
    Blur,
    Circle,
    ColorMatrix,
    Composite,
    Composition,
    Filter,
    Flood,
    Image,
    LinearGradient,
    Mask,
    Merge,
    Offset,
    Position,
    Rectangle,
    RenderOptions,
    Samples,
    Stop,
    Stroke,
    Text,
    TextFrames,
    TextRun,
    VectorPath,
    Video,
)

if TYPE_CHECKING:
    from fframes.compose.components import Item


def shadow(color: str) -> Filter:
    """Preserve the original half-opacity colored glow in linear filter space."""
    return Filter(
        region=(-1, -1, 3, 3),
        steps=(
            Blur(result="blur", source="SourceAlpha", sigma=(10.4, 10.4)),
            Offset(result="offset", source="blur", dy=3),
            Flood(result="color", color=color),
            Composite(result="tint", source="color", destination="offset", operator="in"),
            ColorMatrix(
                result="half",
                source="tint",
                values=((1, 0, 0, 0, 0), (0, 1, 0, 0, 0), (0, 0, 1, 0, 0), (0, 0, 0, 0.5, 0)),
            ),
            Merge(result="glow", sources=("half", "SourceGraphic")),
        ),
    )


def ferris_paths(data: Prepared, eyes: tuple[Samples, Samples]) -> tuple[VectorPath, ...]:
    """Reuse the source contours and paints with independently animated pupils."""
    gradients = {
        "url(#_Linear1)": LinearGradient(
            units="user",
            matrix=(1, 0, 1.38778e-17, -1, 0, -0.000650515),
            stops=(
                Stop(offset=0, color="#f74c00"),
                Stop(offset=0.33, color="#f74c00"),
                Stop(offset=1, color="#f49600"),
            ),
        ),
        **{
            name: LinearGradient(
                units="user",
                matrix=matrix,
                stops=(
                    Stop(offset=0, color="#cc3a00"),
                    Stop(offset=0.15, color="#cc3a00"),
                    Stop(offset=0.74, color="#f74c00"),
                    Stop(offset=1, color="#f74c00"),
                ),
            )
            for name, matrix in (
                ("url(#_Linear2)", (1.0, 0.0, 0.0, -1.0, 0.0, 1.23438e-6)),
                ("url(#_Linear3)", (1.0, 1.32349e-23, 1.32349e-23, -1.0, 0.0, -9.1568e-7)),
            )
        },
    }
    ferris = []
    for index, path in enumerate(data.paths):
        a, b, c, d, e, f = path.matrix
        ferris.append(
            VectorPath(
                size=(1200, 800),
                segments=path.path,
                fill=gradients.get(path.fill, path.fill),
                matrix=(
                    a,
                    b,
                    c,
                    d,
                    Samples(values=tuple(e + v for v in eyes[index == 10].values), fps=FPS)
                    if index in (8, 10)
                    else e,
                    f,
                ),
            )
        )
    return tuple(ferris)


def build(family: str = "Chalkboard SE", fonts: tuple[Path, ...] = ()) -> Video:
    """Compile complete upstream motion, preserving its original layer order."""
    data = prepare(family, fonts)
    motion = data.motion

    def sample(values: tuple[float, ...], start: int = 0) -> Samples:
        return Samples(values=values[start:], fps=FPS)

    children: list[Item] = [Rectangle(size=(WIDTH, HEIGHT), fill="#111827")]
    for position, index, first, last in PALETTE:
        values = tuple(map(float, data.heights[:, index]))
        placement = Position(
            x=motion[f"bar_{position}"], y=sample(tuple(500 - h / 2 for h in values))
        )
        children.extend(
            (
                Rectangle(
                    size=(104, sample(tuple(h + 8 for h in values))),
                    position=placement,
                    radius=48,
                    fill=None,
                    stroke=Stroke(color="#ffffff", width=4),
                ),
                Rectangle(
                    size=(96, sample(values)),
                    position=placement,
                    radius=48,
                    fill=LinearGradient(
                        end=(1, 1), stops=(Stop(offset=0, color=first), Stop(offset=1, color=last))
                    ),
                    filter=shadow(last),
                ),
            )
        )
    arrow_scale = 298 / 598.3520004127504
    children.extend(
        (
            Composition(
                position=Position(x=200, y=290),
                mask=Mask(size=(298, 1080)),
                opacity=motion["arrow"],
                children=(
                    Composition(
                        matrix=(
                            arrow_scale,
                            0,
                            0,
                            arrow_scale,
                            arrow_scale * 12.76795062351539,
                            (1080 - 417.989493060112 * arrow_scale) / 2
                            + arrow_scale * 11.630295608565234,
                        ),
                        children=tuple(
                            VectorPath(
                                size=(599, 418),
                                segments=path,
                                fill=None,
                                stroke=Stroke(
                                    color="#ffffff",
                                    width=4.5,
                                    cap="round" if i == 0 else "butt",
                                    dash=(8, 12) if i == 0 else (),
                                ),
                            )
                            for i, path in enumerate(ARROW)
                        ),
                    ),
                ),
            ),
            Text(
                content=TextFrames(frames=data.captions),
                anchor="baseline",
                position=Position(x=960, y=939.6),
                text_anchor="middle",
                font_family=family,
                font_size=64,
                fill="#ffffff",
            ),
            Image(
                source=data.assets["marketing_code"],
                size=(900, 900),
                fit="contain",
                position=Position(x=motion["code"], y=10),
            ),
        )
    )
    eye = sample(motion["eye"].values, 138)
    ferris = ferris_paths(data, (eye, eye))
    children.extend(
        (
            Composition(
                position=Position(x=1456, y=sample(motion["ferris"].values, 138)),
                size=(400, 400),
                mask=Mask(size=(400, 400)),
                children=(
                    Composition(matrix=(1 / 3, 0, 0, 1 / 3, 0, 200 / 3), children=tuple(ferris)),
                ),
            ).at(2.3, duration=2.7),
            Circle(
                radius=motion["wipe"],
                fill="#ffffff",
                position=Position(
                    x=sample(tuple(960 - r for r in motion["wipe"].values)),
                    y=sample(tuple(500 - r for r in motion["wipe"].values)),
                ),
            ),
        )
    )
    outro_start = 976
    for start, end, color in ((976, 1129, "#000000"), (1129, data.frames, "#7351d8")):
        children.append(
            Text(
                content=(TextRun(content="ff", fill=color), TextRun(content="rames")),
                font_family="Bubble Bobble",
                font_size=154,
                anchor="baseline",
                text_anchor="middle",
                position=Position(x=960, y=570),
            ).at(start / FPS, duration=(end - start) / FPS)
        )
    children.extend(
        (
            Text(
                content="Write some code. Get video. Enjoy!",
                font_family=family,
                font_size=30,
                anchor="baseline",
                text_anchor="middle",
                position=Position(x=960, y=610),
            ).at(outro_start / FPS),
            Composition(
                matrix=(2.7, 0, 0, 2.7, -218 * 2.7, 110 * 2.7),
                children=(
                    VectorPath(
                        size=(550, 70),
                        segments=BOUNCES,
                        fill=None,
                        stroke=Stroke(
                            color=LinearGradient(
                                stops=(
                                    Stop(offset=0, color="#ec77ab"),
                                    Stop(offset=1, color="#4f46e5"),
                                )
                            ),
                            width=10,
                            cap="round",
                            join="round",
                            miter_limit=10,
                            dash=(40.4579, 796.447),
                            dash_offset=sample(motion["bounce"].values, outro_start),
                        ),
                    ),
                    VectorPath(
                        size=(550, 70),
                        segments=SPARKS,
                        fill=None,
                        opacity=sample(motion["spark_opacity"].values, outro_start),
                        stroke=Stroke(
                            color="#4f46e5",
                            width=6,
                            cap="round",
                            join="round",
                            dash=(sample(motion["spark_length"].values, outro_start), 137),
                            dash_offset=sample(motion["spark_offset"].values, outro_start),
                        ),
                    ),
                ),
            ).at(outro_start / FPS),
            *(
                Audio(source=data.assets[name]).at(start)
                for name, start in (
                    ("marketing_audio", 0),
                    ("marketing_woosh", 6),
                    ("marketing_end", 16),
                )
            ),
        )
    )
    return Video(
        resolution=(WIDTH, HEIGHT),
        fps=FPS,
        fonts=data.fonts,
        load_system_fonts=True,
        composition=Composition(duration=data.frames / FPS, children=tuple(children)),
    )


def main() -> None:
    """Render the full marketing clip to output/compose."""
    args = arguments()
    path = Path("output/compose/marketing.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    build(args.family, tuple(args.font)).render(path, options=RenderOptions(concurrency=2))


if __name__ == "__main__":
    main()
