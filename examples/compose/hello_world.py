"""Port upstream hello-world using components and native animation."""

from pathlib import Path

from examples.assets import files
from examples.hello_world import DURATION, FPS, HEIGHT, MOVEMENT, WIDTH, background
from fframes.compose import (
    Clip,
    ColorTween,
    Component,
    Composition,
    Position,
    Rectangle,
    Text,
    TextTemplate,
    Tween,
    Video,
)


def backgrounds() -> tuple[Clip, ...]:
    """Build the global background once, independently of each local scene."""
    return tuple(
        Rectangle(
            size=(WIDTH, HEIGHT),
            fill=ColorTween(from_value=k.from_value, to_value=k.to_value, duration=k.end - k.start),
        ).at(k.start, duration=k.end - k.start)
        for k in background()
    )


def counter(fill: str = "#3B5563") -> Text:
    """Format the global frame readout in Rust while the video renders."""
    return Text(
        content=TextTemplate(template="This frame index: {frame}, second: {seconds:.2f}"),
        position=Position(x=100, y=440),
        font_family="JetBrains Mono",
        font_size=74,
        font_weight=500,
        fill=fill,
        anchor="baseline",
    )


class Greeting(Component):
    """Reuse the original scene without constructing SVG or Python frame callbacks."""

    slug: str = "Renderer!"

    def compose(self) -> Composition:
        """Keep original dimensions, typography, timing and painter order."""
        squares = tuple(
            Rectangle(
                size=(200, 200),
                fill="#0000FF",
                position=Position(
                    x=Tween(from_value=a[0], to_value=b[0], duration=end - start),
                    y=Tween(from_value=a[1], to_value=b[1], duration=end - start),
                ),
            ).at(start, duration=end - start if end < 10 else DURATION - start)
            for start, end, a, b in MOVEMENT
        )
        return Composition(
            duration=DURATION,
            children=(
                *backgrounds(),
                *squares,
                Text(
                    content=f"Hello {self.slug}",
                    position=Position(x=99, y=300),
                    font_family="DM Sans",
                    font_size=150,
                    anchor="baseline",
                ),
                counter(),
            ),
        )


def build(slug: str = "Renderer!") -> Video:
    """Describe the complete scene with the exact upstream font assets."""
    assets = files("hello_world")
    return Video(
        resolution=(WIDTH, HEIGHT),
        fps=FPS,
        load_system_fonts=False,
        fonts=(assets["dm_sans"], assets["jetbrains_mono"]),
        composition=Composition(duration=DURATION, children=(Greeting(slug=slug),)),
    )


def main() -> None:
    """Render the upstream scene to output/compose/hello_world.mp4."""
    path = Path("output/compose/hello_world.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    build().render(path)


if __name__ == "__main__":
    main()
