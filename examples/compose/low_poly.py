"""Reusable polygon paths and an animated image-pattern title."""

from pathlib import Path
from typing import TYPE_CHECKING

from examples.shared.low_poly import FPS, HEIGHT, WIDTH, Bird, arguments, prepare
from fframes.compose import (
    Audio,
    Composition,
    Pattern,
    Position,
    Rectangle,
    RenderOptions,
    Samples,
    Text,
    VectorPath,
    Video,
)

if TYPE_CHECKING:
    from fframes.compose.components import Item


def build(bird: Bird = "owl") -> Video:
    """Compile the original artwork once, with samples evaluated entirely in Rust."""
    data = prepare(bird)
    children: list[Item] = [Rectangle(size=(WIDTH, HEIGHT))]
    if bird == "pelican":
        children.append(Rectangle(size=(8000, 3000), position=Position(x=-2000), fill="#0d0d00"))
    if data.heights is not None:
        children.extend(
            (
                Text(
                    content="EAGLE OWL",
                    anchor="baseline",
                    position=Position(x=1440, y=378),
                    text_anchor="middle",
                    font_family="Fredoka One",
                    font_size=100,
                    fill=Pattern(
                        source=data.assets["noise"],
                        size=(230, 177),
                        matrix=(
                            1,
                            0,
                            0,
                            1,
                            Samples(values=tuple(dx - 1440 for dx in data.noise_x), fps=FPS),
                            Samples(values=tuple(dy - 378 for dy in data.noise_y), fps=FPS),
                        ),
                    ),
                ),
                Text(
                    content="BUBO BUBO",
                    anchor="baseline",
                    position=Position(x=1440, y=280.8),
                    text_anchor="middle",
                    font_family="Fredoka One",
                    font_size=45,
                    fill="#9f8866",
                ),
                *(
                    Rectangle(
                        size=(8, Samples(values=tuple(map(float, heights)), fps=FPS)),
                        radius=3,
                        position=Position(
                            x=1220 + i * 15,
                            y=Samples(values=tuple(550 - float(h) / 2 for h in heights), fps=FPS),
                        ),
                        fill="#ffffff",
                    )
                    for i, heights in enumerate(data.heights.T)
                ),
                Audio(source=data.assets["owl_audio"]).at(0, duration=10),
            )
        )
    children.append(
        Composition(
            matrix=(0.28125, 0, 0, 0.28125, 300, 0) if bird == "owl" else None,
            children=tuple(
                VectorPath(
                    size=(WIDTH, HEIGHT),
                    segments="M" + p.points + "Z",
                    fill=p.fill,
                    rendering="crispEdges" if bird == "owl" else "auto",
                )
                for p in data.polygons
            ),
        )
    )
    return Video(
        resolution=(WIDTH, HEIGHT),
        fps=FPS,
        fonts=(data.assets["fredoka"],),
        load_system_fonts=False,
        composition=Composition(duration=data.duration, children=tuple(children)),
    )


def main() -> None:
    """Render the selected bird to output/compose."""
    args = arguments()
    path = Path(f"output/compose/low_poly_{args.bird}.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    build(args.bird).render(path, options=RenderOptions(concurrency=2))


if __name__ == "__main__":
    main()
