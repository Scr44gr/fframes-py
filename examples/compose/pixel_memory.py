"""Photo galleries, developing prints, heart-shaped bokeh and synchronized clips."""

from math import floor
from pathlib import Path
from typing import TYPE_CHECKING

from examples.shared.pixel_memory import (
    FPS,
    GOLD,
    HEIGHT,
    INTRO,
    WIDTH,
    Kind,
    Photo,
    Shot,
    arguments,
    curve,
    prepare,
    samples,
)
from fframes.compose import (
    Audio,
    Blur,
    Circle,
    ColorMatrix,
    Composition,
    Filter,
    Image,
    LinearGradient,
    Mask,
    Merge,
    Offset,
    Position,
    RadialGradient,
    Rectangle,
    RenderOptions,
    Stop,
    Stroke,
    Text,
    Tween,
    VectorPath,
    Video,
    VideoClip,
)

if TYPE_CHECKING:
    from fframes.compose.components import Item


def shadow(polaroid: bool = False) -> Filter:
    """Keep source alpha, offset, opacity transfer and source-over merge in order."""
    blur, offset = (10, 5) if polaroid else (8, 3)
    return Filter(
        region=(-0.2, -0.2, 1.4, 1.4),
        steps=(
            Blur(result="blur", source="SourceAlpha", sigma=(blur, blur)),
            Offset(result="offset", source="blur", dx=offset, dy=offset),
            ColorMatrix(
                result="alpha",
                source="offset",
                values=((1, 0, 0, 0, 0), (0, 1, 0, 0, 0), (0, 0, 1, 0, 0), (0, 0, 0, 0.3, 0)),
            ),
            Merge(result="merged", sources=("alpha", "SourceGraphic")),
        ),
    )


def photo_frame(photo: Photo, family: str) -> Composition:
    """Reuse one photo component for framed, background and developing treatments."""
    width, height = photo.size
    position = Position(x=photo.position[0], y=photo.position[1])
    children: list[Item] = []
    if photo.development is not None:
        children.extend(
            (
                Rectangle(
                    size=(width + 28, height + 74),
                    fill="#ffffff",
                    radius=2,
                    stroke=Stroke(color="#e9e9e9"),
                ),
                Rectangle(size=photo.size, position=position, fill="#f0f0f0"),
            )
        )
    elif photo.stroke:
        children.append(
            Rectangle(
                size=photo.size,
                position=position,
                fill=None,
                stroke=Stroke(color="#ffffff", width=photo.stroke),
            )
        )
    children.append(
        Image(
            source=photo.source,
            size=photo.size,
            position=position,
            fit="cover" if photo.development is not None else "contain",
        )
    )
    if photo.development is not None:
        children.append(
            Rectangle(
                size=photo.size,
                position=position,
                fill="#ffffff",
                opacity=samples(1 - photo.development),
            )
        )
        if photo.year:
            children.append(
                Text(
                    content=photo.year,
                    position=Position(x=(width + 28) / 2, y=height + 49),
                    anchor="baseline",
                    text_anchor="middle",
                    baseline="middle",
                    font_family=family,
                    font_size=44,
                    fill="#333333",
                    opacity=samples(photo.development),
                )
            )
    return Composition(
        position=Position(x=samples(photo.x), y=samples(photo.y)),
        scale=samples(photo.scale),
        rotation=samples(photo.rotation),
        origin=photo.origin,
        opacity=samples(photo.opacity),
        filter=shadow(photo.development is not None) if photo.shadow else None,
        children=tuple(children),
    )


def scene(shot: Shot, family: str) -> Composition:
    """Build one original scene; video frames and their soundtrack share a local clock."""
    if shot.video is None:
        return Composition(children=tuple(photo_frame(photo, family) for photo in shot.photos))
    duration = shot.duration
    opacity = curve(
        duration, (0, 0.5, 0, 1, "ease_in"), (duration - 0.5, duration, 1, 0, "ease_out")
    )
    width, height = shot.video_size
    scaled = width / height * HEIGHT
    return Composition(
        children=(
            *(
                (
                    VideoClip(
                        source=shot.video,
                        size=(WIDTH, HEIGHT),
                        fit="cover",
                        opacity=samples(opacity * 0.7),
                        filter=Filter(steps=(Blur(result="blur", sigma=(30, 30)),)),
                    ),
                )
                if height > width
                else ()
            ),
            VideoClip(
                source=shot.video,
                size=(scaled, HEIGHT),
                position=Position(x=(WIDTH - scaled) / 2),
                fit="contain",
                opacity=samples(opacity),
            ),
            Audio(source=shot.video),
        )
    )


def build(
    seed: int = 48,
    song: str = "revenge",
    study: Kind | None = None,
    text: str = INTRO,
    family: str = "Indie Flower",
    fonts: tuple[Path, ...] = (),
) -> Video:
    """Build a complete soundtrack-length slideshow or one selected source study."""
    data = prepare(seed, song, study, text, family, fonts)
    palettes = tuple(
        RadialGradient(
            focus=(0.4, 0.4),
            stops=tuple(
                Stop(offset=offset, color=color)
                for offset, color in zip((0, 0.7, 1), colors, strict=True)
            ),
        )
        for colors in GOLD
    )
    children: list[Item] = [
        Rectangle(
            size=(WIDTH, HEIGHT),
            fill=LinearGradient(
                end=(1, 1), stops=(Stop(offset=0, color="#000000"), Stop(offset=1, color="#050505"))
            ),
        )
    ]
    children.extend(
        Circle(
            radius=circle.radius,
            position=Position(
                x=samples(circle.x - circle.radius), y=samples(circle.y - circle.radius)
            ),
            opacity=circle.opacity,
            fill=palettes[circle.palette],
            filter=Filter(
                region=(-0.5, -0.5, 2, 2),
                steps=(Blur(result="blur", sigma=(circle.blur, circle.blur)),),
            ),
        )
        for circle in data.bokeh
    )
    if data.intro_duration:
        children.append(
            Composition(
                opacity=Tween(
                    from_value=1,
                    to_value=0,
                    start_at=data.intro_duration - 3,
                    duration=3,
                    easing="ease_out",
                ),
                children=tuple(
                    Text(
                        content=line,
                        font_family="Space Grotesk",
                        font_size=124,
                        anchor="baseline",
                        text_anchor="middle",
                        baseline="middle",
                        position=Position(x=960, y=324 + i * 124 * 1.1),
                        fill="#ffffff",
                    )
                    for i, line in enumerate(data.lines)
                ),
            ).at(0, duration=floor(data.intro_duration * FPS) / FPS)
        )
    children.extend(
        scene(shot, family).at(start / FPS, duration=floor(shot.duration * FPS) / FPS)
        for start, shot in data.scenes
    )
    if data.final_start < floor(data.duration * FPS):
        scale = 886 / 483
        children.append(
            Composition(
                position=Position(x=517),
                mask=Mask(size=(886, HEIGHT)),
                children=(
                    VectorPath(
                        size=(483, 152),
                        segments=data.final_path,
                        fill=None,
                        matrix=(scale, 0, 0, scale, 20 * scale, (HEIGHT - 115 * scale) / 2),
                        stroke=Stroke(
                            color="#ffffff",
                            width=9,
                            cap="round",
                            dash=(900, 900),
                            dash_offset=Tween(
                                from_value=3000, to_value=0, duration=data.final_duration
                            ),
                        ),
                    ),
                ),
            ).at(data.final_start / FPS)
        )
    if study is None:
        children.append(Audio(source=data.assets[f"pixel_{song.lower()}_mp3"]).at(6))
    return Video(
        resolution=(WIDTH, HEIGHT),
        fps=FPS,
        fonts=data.fonts,
        load_system_fonts=True,
        composition=Composition(
            duration=floor(data.duration * FPS) / FPS, children=tuple(children)
        ),
    )


def main() -> None:
    """Render the chosen deterministic gallery into output/compose."""
    args = arguments()
    path = Path(f"output/compose/pixel_memory{('_' + args.scene) if args.scene else ''}.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    build(args.seed, args.song, args.scene, args.text, args.family, tuple(args.font)).render(
        path, options=RenderOptions(concurrency=2)
    )


if __name__ == "__main__":
    main()
