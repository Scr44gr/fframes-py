"""The beta announcement composed from reusable videos and native scene curves."""

from math import radians, tan
from pathlib import Path
from typing import TYPE_CHECKING

from examples.compose import hello_world, marketing, podcast, tiktok
from examples.shared.beta import (
    BRACKETS,
    FPS,
    GITHUB,
    HEIGHT,
    MESSAGES,
    SCENES,
    TITLES,
    WIDTH,
    prepare,
)
from examples.shared.marketing import arguments
from fframes.compose import (
    Audio,
    Blur,
    Clip,
    ColorMatrix,
    Composition,
    Filter,
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
from fframes.compose.paint import Brush
from fframes.values import Scalar

if TYPE_CHECKING:
    from fframes.compose.components import Item


def gate(start: int, end: int, count: int) -> Samples:
    """Hide a child outside its interval while keeping its original animation clock."""
    return Samples(values=tuple(float(start <= i < end) for i in range(count)), fps=FPS)


def silent(video: Video) -> Composition:
    """Embed these untransformed source roots without their independent soundtracks."""
    return Composition(
        duration=video.composition.duration,
        children=tuple(
            child
            for child in video.composition.children
            if not isinstance(child, Audio)
            and not (isinstance(child, Clip) and isinstance(child.content, Audio))
        ),
    )


def build(family: str = "Chalkboard SE", fonts: tuple[Path, ...] = ()) -> Video:
    """Preserve all seven scenes, the overlapping GitHub reveal and embedded clocks."""
    data = prepare(family, fonts)
    m, assets = data.motion, data.assets

    def text(
        content: str | TextFrames | tuple[TextRun, ...],
        x: Scalar,
        y: float,
        size: float,
        *,
        font: str = "DM Sans",
        weight: int = 700,
        fill: Brush | None = "#000000",
        centered: bool = False,
    ) -> Text:
        return Text(
            content=content,
            position=Position(x=x, y=y),
            anchor="baseline",
            text_anchor="middle" if centered else "start",
            font_family=font,
            font_size=size,
            font_weight=weight,
            fill=fill,
        )

    def picture(name: str, x: Scalar, y: Scalar, w: float, h: float) -> Image:
        return Image(
            source=assets[f"beta_{name}"], position=Position(x=x, y=y), size=(w, h), fit="contain"
        )

    def message(index: int) -> Composition:
        y, name, username, content = MESSAGES[index]
        return Composition(
            children=(
                picture(name, 800, y, 80, 80),
                text(username, 880, y + 34, 18, font="Inter 24pt", weight=500, fill="#ffffff"),
                text(content, 880, y + 60, 15, font="Inter 24pt", weight=500, fill="#cbd5e1"),
            )
        )

    def sliced(name: str, start: int) -> Samples:
        return Samples(values=m[name].values[start:], fps=FPS)

    gradient = LinearGradient(
        stops=(Stop(offset=0, color="#4338ca"), Stop(offset=1, color="#a21caf"))
    )
    heading = Composition(
        children=(
            text("Welcome to the beta", m["welcome"], 432, 150),
            text("of fframes", m["of"], 648, 150).at(0, duration=100 / FPS),
            text(
                (
                    TextRun(content="of "),
                    TextRun(
                        content="ff",
                        font_family="Bubble Bobble",
                        font_size=190,
                        font_weight=400,
                        fill="#7450d9",
                        dy=10,
                    ),
                    TextRun(
                        content="rames", font_family="Bubble Bobble", font_size=190, font_weight=400
                    ),
                ),
                sliced("of", 100),
                648,
                150,
            ).at(100 / FPS),
        )
    )
    skew_x = tuple(tan(radians(v)) for v in m["tilt"].values)
    skew_y = tuple(tan(radians(-v + 0.4)) for v in m["tilt"].values)
    code = Composition(
        children=(
            Composition(
                opacity=m["code_alpha"],
                matrix=(
                    Samples(
                        values=tuple(1 + x * y for x, y in zip(skew_x, skew_y, strict=True)),
                        fps=FPS,
                    ),
                    Samples(values=skew_y, fps=FPS),
                    Samples(values=skew_x, fps=FPS),
                    1,
                    m["code_x"],
                    0,
                ),
                children=(picture("code", 0, 50, 1023, 1023 * 766 / 790),),
            ),
            Composition(
                position=Position(x=m["ferris_x"], y=250),
                mask=Mask(size=(500, 500)),
                children=(
                    Composition(
                        matrix=(5 / 12, 0, 0, 5 / 12, 0, 250 / 3),
                        children=marketing.ferris_paths(
                            data.ferris, (m["eye_right"], m["eye_left"])
                        ),
                    ),
                ),
            ),
        )
    )
    rendering = Composition(
        children=(
            text("With the power of", m["power_x"], 324, 150),
            *(
                text(
                    (
                        TextRun(
                            content="  GPU    " if start else "native ",
                            fill="#7450d9",
                            font_family="Bubble Bobble" if start else "DM Sans",
                            font_size=170 if start else 150,
                            font_weight=400 if start else 900,
                        ),
                        TextRun(content="     rendering"),
                    ),
                    sliced("render_x", start),
                    540,
                    150,
                ).at(start / FPS, duration=(end - start) / FPS)
                for start, end in ((0, 67), (67, 140))
            ),
            text(
                TextFrames(frames=data.counters),
                211.2,
                756,
                45,
                font="JetBrains Mono",
                weight=600,
                fill="#4b5563",
            ),
            Rectangle(
                position=Position(x=192, y=777.6),
                size=(m["progress"], 30),
                radius=12,
                fill=LinearGradient(
                    stops=(Stop(offset=0, color="#aa83de"), Stop(offset=1, color="#00d4ff"))
                ),
            ),
        )
    )
    phone_mask = Mask(size=(380, 820), position=(780, 150), radius=60)
    phone = Composition(
        children=(
            Composition(
                mask=phone_mask,
                children=(
                    picture("camera_ui", 790, 154, 370, 819),
                    picture("qr", 830, 390, 300, 300),
                    Composition(
                        opacity=m["scan_alpha"],
                        children=(
                            *(
                                VectorPath(
                                    size=(WIDTH, HEIGHT),
                                    segments=path,
                                    fill=None,
                                    stroke=Stroke(color="#EBBD1D", width=2),
                                )
                                for path in BRACKETS
                            ),
                            Composition(
                                scale=m["button_scale"],
                                origin=(960, 540),
                                children=(
                                    Rectangle(
                                        position=Position(x=884, y=715),
                                        size=(200, 34),
                                        radius=16,
                                        fill="#EBBD1D",
                                    ),
                                    text(
                                        "fframes discord invite",
                                        905,
                                        737,
                                        16,
                                        font="Inter 24pt",
                                        weight=500,
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            Composition(
                mask=phone_mask,
                children=(
                    Composition(
                        position=Position(y=m["discord_y"]),
                        children=(
                            Rectangle(
                                position=Position(x=790, y=154), size=(370, 819), fill="#292841"
                            ),
                            picture("discord_ui", 791, 152, 370, 819),
                            text(
                                "12:04", 830, 196, 16, font="Inter 24pt", weight=500, fill="#9ca3af"
                            ),
                            *(message(i) for i in range(3)),
                            Composition(
                                position=Position(y=m["message_y"]),
                                scale=m["message_scale"],
                                origin=(960, 1080),
                                opacity=m["message_alpha"],
                                children=(message(3),),
                            ),
                        ),
                    ),
                ),
            ),
            picture("iphone_frame", 576, 108, 800, 800 * 544 / 480),
            Rectangle(
                position=Position(
                    x=Samples(values=tuple(976 - w / 2 for w in m["island_w"].values), fps=FPS),
                    y=170,
                ),
                size=(m["island_w"], m["island_h"]),
                radius=Samples(values=tuple(h / 2 for h in m["island_h"].values), fps=FPS),
            ),
            Composition(
                children=(
                    text("ff", 895, 197, 23, font="Bubble Bobble", weight=400, fill="#6366f1"),
                    *(
                        Rectangle(
                            position=Position(
                                x=1025 + (i + 1) * 4.5,
                                y=Samples(
                                    values=tuple(190 - float(h) / 2 for h in data.heights[9:, i]),
                                    fps=FPS,
                                ),
                            ),
                            size=(
                                3,
                                Samples(values=tuple(map(float, data.heights[9:, i])), fps=FPS),
                            ),
                            radius=1,
                            fill="#6366f1",
                        )
                        for i in range(6)
                    ),
                )
            ).at(9 / FPS, duration=(372 - 9) / FPS),
            Composition(
                children=(
                    VectorPath(
                        size=(24, 24),
                        segments=GITHUB,
                        fill="#ffffff",
                        matrix=(56 / 24, 0, 0, 56 / 24, 816, 182),
                    ),
                    text(
                        "New collaboration invite",
                        880,
                        208,
                        18,
                        font="Inter 24pt",
                        weight=500,
                        fill="#ffffff",
                    ),
                    text(
                        "dmtrKovalenko invites you to fframes",
                        880,
                        230,
                        14,
                        font="Inter 24pt",
                        weight=500,
                        fill="#cbd5e1",
                    ),
                )
            ).at(385 / FPS),
        )
    )
    github = Composition(
        children=(
            picture("github_screenshot", m["github_x"], m["github_y"], WIDTH, WIDTH * 5166 / 2560),
        )
    )
    preview_mask = Mask(size=(1190.4, 669.6), position=(364.8, 320), radius=50)
    preview_shadow = Filter(
        region=(-0.1, -0.1, 2, 2),
        color_space="srgb",
        steps=(
            Blur(result="blur", source="SourceAlpha", sigma=(40, 40)),
            Offset(result="offset", source="blur", dx=2, dy=2),
            ColorMatrix(
                result="shadow",
                source="offset",
                values=((0, 0, 0, 0, 0), (0, 0, 0, 0, 0), (0, 0, 0, 0, 0), (0, 0, 0, 0.3, 0)),
            ),
            Merge(result="merged", sources=("shadow", "SourceGraphic")),
        ),
    )
    examples = Composition(
        children=(
            text(
                "to help you get started", m["examples_x"], 86.4, 60, fill=gradient, centered=True
            ),
            Composition(
                mask=Mask(size=(WIDTH, 135), position=(0, 115)),
                children=(
                    Composition(
                        position=Position(y=m["title_y"]),
                        children=tuple(
                            text(label, m["hello_x"] if i == 0 else 960, y, 120, centered=True)
                            for i, (label, y) in enumerate(
                                zip(TITLES, (220, 394, 594, 794), strict=True)
                            )
                        ),
                    ),
                ),
            ),
            Rectangle(
                position=Position(x=364.8, y=320),
                size=(1190.4, 669.6),
                radius=50,
                stroke=Stroke(color="#4338ca", width=8),
                filter=preview_shadow,
            ),
            *(
                Composition(
                    opacity=gate(start, end, 500),
                    mask=preview_mask,
                    children=(
                        Composition(
                            position=Position(x=364.8, y=320),
                            scale=0.62,
                            origin=(0, 0),
                            children=(silent(child),),
                        ),
                    ),
                )
                for start, end, child in (
                    (0, 156, hello_world.build("Hello, Beta!")),
                    (156, 288, marketing.build(family, fonts)),
                )
            ),
        )
    )
    ending = Composition(
        children=(
            Composition(
                opacity=m["logo_alpha"],
                children=(
                    text(
                        (TextRun(content="ff", fill="#7450d9"), TextRun(content="rames")),
                        960,
                        540,
                        190,
                        font="Bubble Bobble",
                        weight=400,
                        centered=True,
                    ),
                ),
            ),
            Composition(
                rotation=m["beta_angle"],
                origin=(1300, 590),
                opacity=m["beta_alpha"],
                children=(text("beta", 1220, 605, 80, font=family, weight=400, fill=gradient),),
            ),
        )
    )
    children: list[Item] = [picture("background", 0, 0, WIDTH, HEIGHT)]
    children.extend(
        scene.at(start / FPS, duration=(end - start) / FPS)
        for scene, (start, end) in zip(
            (heading, code, rendering, phone, github, examples, ending), SCENES, strict=True
        )
    )
    for start, end, child, portrait in (
        (1570, 1690, podcast.build(*(assets["beta_audio"],) * 3), False),
        (1690, 1782, tiktok.build(), True),
    ):
        children.append(
            Composition(
                opacity=gate(start, end, data.frames),
                mask=preview_mask,
                children=(
                    Composition(
                        size=(1080, 1920) if portrait else (WIDTH, HEIGHT),
                        position=Position(x=1552.8 if portrait else 364.8, y=320),
                        rotation=90 if portrait else 0,
                        scale=0.62,
                        origin=(0, 0),
                        children=(silent(child),),
                    ),
                ),
            )
        )
    children.extend(
        (
            Audio(source=assets["beta_audio"]),
            *(Audio(source=assets["beta_pop"]).at(i / FPS) for i in (95, 440)),
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
    """Render the composed announcement to output/compose."""
    args = arguments()
    path = Path("output/compose/beta.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    build(args.family, tuple(args.font)).render(path, options=RenderOptions(concurrency=2))


if __name__ == "__main__":
    main()
