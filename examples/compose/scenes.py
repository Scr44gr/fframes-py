"""Port upstream hello-world's two-scene variant using nested compositions."""

from pathlib import Path

from examples.assets import files
from examples.compose.hello_world import backgrounds, counter
from examples.shared.hello_world import FPS, HEIGHT, WIDTH
from fframes.compose import Composition, Position, Rectangle, Text, Tween, Video


def build() -> Video:
    """Give each scene its own clock and retain the global background and readout."""
    assets = files("hello_world")
    first = Composition(
        duration=15,
        children=(
            Text(
                content="hello scene 1",
                position=Position(x=100, y=300),
                font_family="DM Sans",
                font_size=150,
                anchor="baseline",
            ),
            Rectangle(size=(120, 120), fill="#008000"),
            Rectangle(size=(120, 120), fill="#008000", rotation=45, origin=(0, 0)),
        ),
    )
    second = Composition(
        duration=15,
        children=(
            Text(
                content="Hello Scene 2",
                position=Position(x=100, y=Tween(from_value=300, to_value=320, duration=0.2)),
                font_family="DM Sans",
                font_size=150,
                anchor="baseline",
            ),
        ),
    )
    return Video(
        resolution=(WIDTH, HEIGHT),
        fps=FPS,
        load_system_fonts=False,
        fonts=(assets["dm_sans"], assets["jetbrains_mono"]),
        composition=Composition(
            duration=30,
            children=(*backgrounds(), first, second.at(15), counter("#4B5563")),
        ),
    )


def main() -> None:
    """Render the two original scenes to output/compose/scenes.mp4."""
    path = Path("output/compose/scenes.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    build().render(path)


if __name__ == "__main__":
    main()
