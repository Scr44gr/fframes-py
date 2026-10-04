"""Bird illustrations and circular speaker cards built from reusable graphics."""

from pathlib import Path

from examples.shared.podcast import (
    DURATION,
    FPS,
    HEIGHT,
    SPEAKERS,
    WIDTH,
    YELLOW,
    arguments,
    prepare,
)
from fframes.compose import (
    Audio,
    Circle,
    Composition,
    Image,
    Mask,
    Position,
    Rectangle,
    RenderOptions,
    Samples,
    Stroke,
    VectorPath,
    Video,
)


def build(goose: Path | None = None, guest: Path | None = None, duck: Path | None = None) -> Video:
    """Keep independent speaker analyses optional and retain the source artwork."""
    data = prepare((goose, guest, duck))

    def art(index: int, fill: str) -> VectorPath:
        return VectorPath(size=(WIDTH, HEIGHT), segments=data.paths[index], fill=fill)

    guest_width = 48 + (320 if "guest" in data.heights else 0)
    return Video(
        resolution=(WIDTH, HEIGHT),
        fps=FPS,
        load_system_fonts=False,
        composition=Composition(
            duration=DURATION,
            children=(
                Rectangle(size=(1946, 2512), position=Position(x=-648, y=-373), fill=YELLOW),
                Rectangle(size=(723, 722.346), position=Position(x=598, y=-20), fill=YELLOW),
                *(
                    art(i, fill)
                    for i, fill in enumerate(("#ffffff", YELLOW, YELLOW, "#000000", "#000000"))
                ),
                Rectangle(
                    size=(21.8877, 18.8438), position=Position(x=934.082, y=352.85), fill="#ffffff"
                ),
                Rectangle(
                    size=(21.8877, 18.8438), position=Position(x=953.146, y=332.611), fill="#ffffff"
                ),
                Rectangle(
                    size=(1117.68, 1446), position=Position(x=970.797, y=-142.854), fill="#ffffff"
                ),
                Composition(
                    mask=Mask(size=(723, 1446.02), position=(970.797, -143.12)),
                    children=(
                        art(5, YELLOW),
                        art(6, "#ffffff"),
                        art(7, "#ffffff"),
                        Composition(
                            mask=Mask(size=(350.203, 350.203), position=(906.547, 161.456)),
                            children=(
                                art(8, "#000000"),
                                art(9, "#000000"),
                                Rectangle(
                                    size=(24.7119, 53.6602),
                                    position=Position(x=1233.45, y=426.227),
                                    fill="#ffffff",
                                ),
                            ),
                        ),
                        Rectangle(
                            size=(62.8389, 11.1667),
                            position=Position(x=1000.45, y=321.444),
                            rotation=-180,
                            origin=(0, 0),
                        ),
                        Rectangle(
                            size=(62.8389, 18.8438),
                            position=Position(x=973.62, y=360.527),
                            rotation=-180,
                            origin=(0, 0),
                            fill=YELLOW,
                        ),
                        Rectangle(
                            size=(74.1364, 44.0885),
                            position=Position(x=927.727, y=270.334),
                            fill="#ffffff",
                        ),
                    ),
                ),
                Rectangle(size=(269.007, 11.2969), position=Position(x=684.139, y=440.348)),
                Rectangle(size=(21, 1080), position=Position(x=950)),
                *(
                    Composition(
                        position=Position(x=220 + i * 560, y=500),
                        children=(
                            Image(
                                source=data.assets[f"podcast_{name}"],
                                size=(360, 360),
                                fit="contain",
                                mask=Mask(size=(360, 360), radius=180),
                            ),
                            Circle(radius=180, fill=None, stroke=Stroke(color="#000000", width=16)),
                        ),
                    )
                    for i, name in enumerate(SPEAKERS)
                ),
                Rectangle(
                    size=(guest_width, 100),
                    radius=32,
                    position=Position(x=960 - guest_width / 2, y=900),
                ),
                *(
                    Rectangle(
                        size=(16, Samples(values=tuple(map(float, heights[:, i])), fps=FPS)),
                        radius=4,
                        fill=YELLOW if name == "guest" else "#000000",
                        position=Position(
                            x=240 + SPEAKERS.index(name) * 560 + i * 20,
                            y=Samples(
                                values=tuple(950 - float(h) / 2 for h in heights[:, i]), fps=FPS
                            ),
                        ),
                    )
                    for name, heights in data.heights.items()
                    for i in range(16)
                ),
                Audio(source=data.assets["podcast_audio"]).at(0, duration=DURATION),
            ),
        ),
    )


def main() -> None:
    """Render the complete minute into output/compose."""
    args = arguments()
    path = Path("output/compose/podcast.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    build(args.goose_audio, args.guest_audio, args.duck_audio).render(
        path, options=RenderOptions(concurrency=2)
    )


if __name__ == "__main__":
    main()
