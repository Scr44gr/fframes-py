"""Nest typed components and 3D: python -m examples.compose.three_d."""

from examples.shared import three_d as shared
from fframes import compose
from fframes import three_d as d


def build(
    size: tuple[int, int] = (640, 360),
    settings: d.RenderSettings = shared.SETTINGS,
) -> compose.Video:
    """Use a component video as the monitor texture, without constructing SVG."""
    width, height = size
    screen = compose.Video(
        resolution=size,
        fps=shared.FPS,
        composition=compose.Composition(
            duration=shared.DURATION,
            children=(
                compose.Rectangle(size=size, fill="#080b12"),
                compose.Scene3D(renderer=shared.cube(size, settings)),
                compose.Rectangle(
                    size=(width, 3),
                    position=compose.Position(y=height - 3),
                    fill="#3288ff",
                ),
            ),
        ),
    ).texture()
    return compose.Video(
        resolution=size,
        fps=shared.FPS,
        composition=compose.Composition(
            duration=shared.DURATION,
            children=(compose.Scene3D(renderer=shared.monitor(screen, size, settings)),),
        ),
    )


def main() -> None:
    """Export the compose example."""
    shared.export(build().compile(), "compose")


if __name__ == "__main__":
    main()
