"""Animate dimensions and precomputed text: python -m examples.compose.reveals."""

from pathlib import Path

from fframes.compose import Circle, Composition, Position, Rectangle, Text, TextFrames, Tween, Video


def build_video(*, fonts: tuple[Path, ...] = ()) -> Video:
    """Reveal shapes, then hold the last text frame until the clip ends."""
    fps = 30
    return Video(
        resolution=(320, 180),
        fps=fps,
        fonts=fonts,
        load_system_fonts=not fonts,
        composition=Composition(
            duration=2.5,
            children=(
                Composition(
                    size=(240, 120),
                    position=Position(x=24, y=24),
                    children=(
                        Rectangle(
                            size=(Tween(from_value=1, to_value=240, duration=1), 16),
                            opacity=Tween(from_value=0, to_value=1, duration=1),
                            fill="#0088FF",
                        ),
                        Circle(
                            radius=Tween(from_value=0, to_value=16, duration=1),
                            position=Position(y=40),
                            fill="#0088FF",
                        ),
                        Text(
                            content=TextFrames(
                                frames=("", *(f"Frame {index}" for index in range(1, fps + 1)))
                            ),
                            font_size=24,
                            font_weight=700,
                            anchor="baseline",
                            position=Position(y=104),
                            fill="#0088FF",
                        ),
                    ),
                ).at(0.5, duration=1.5),
            ),
        ),
    )


def main() -> None:
    """Write a preview and video to the ignored output directory."""
    output = Path("output/compose/reveals")
    output.mkdir(parents=True, exist_ok=True)
    video = build_video().compile()
    video.save_png(output / "preview.png", index=30)
    video.render(output / "video.mp4")


if __name__ == "__main__":
    main()
