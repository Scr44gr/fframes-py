"""Port upstream SkSL and Shadertoy layers using reusable Python components."""

from pathlib import Path

from examples.assets import files
from examples.shared.shaders import (
    CARD_OPACITY,
    CARD_Y,
    DURATION,
    FPS,
    GPU_BACKEND,
    HEIGHT,
    TITLE_OPACITY,
    WIDTH,
    backend_argument,
    programs,
)
from fframes import Shader
from fframes.compose import (
    Component,
    Composition,
    Mask,
    Position,
    Rectangle,
    ShaderLayer,
    Stroke,
    Text,
    Video,
)
from fframes.models import Backend


class ShaderCard(Component):
    """Reuse a rounded shader card with the original slide and fade."""

    shader: Shader

    def compose(self) -> Composition:
        """Clip the program while preserving the border outside its bounds."""
        return Composition(
            size=(760, 760),
            position=Position(x=1040, y=CARD_Y),
            opacity=CARD_OPACITY,
            children=(
                ShaderLayer(
                    shader=self.shader, size=(760, 760), mask=Mask(size=(760, 760), radius=40)
                ),
                Rectangle(
                    size=(760, 760), radius=40, fill=None, stroke=Stroke(color="#ffffff33", width=2)
                ),
            ),
        )


def build(backend: Backend = GPU_BACKEND) -> Video:
    """Build the same scene without SVG strings or per-frame Python callbacks."""
    assets = files("shaders")
    aurora, torus = programs(assets)
    return Video(
        composition=Composition(
            duration=DURATION,
            children=(
                ShaderLayer(shader=aurora, size=(WIDTH, HEIGHT)),
                ShaderCard(shader=torus),
                Composition(
                    opacity=TITLE_OPACITY,
                    children=(
                        Text(
                            content="GPU shaders",
                            position=Position(x=120, y=500),
                            font_family="DM Sans",
                            font_weight=500,
                            font_size=128,
                            fill="#ffffff",
                            anchor="baseline",
                        ),
                        Text(
                            content="SkSL and Shadertoy, drawn by Skia",
                            position=Position(x=126, y=580),
                            font_family="DM Sans",
                            font_weight=500,
                            font_size=40,
                            fill="#f5f3ffcc",
                            anchor="baseline",
                        ),
                    ),
                ),
            ),
        ),
        resolution=(WIDTH, HEIGHT),
        fps=FPS,
        backend=backend,
        fonts=(assets["dm_sans"],),
        load_system_fonts=False,
    )


def main() -> None:
    """Render the component scene to output/compose/shaders.mp4."""
    path = Path("output/compose/shaders.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    build(backend_argument()).render(path)


if __name__ == "__main__":
    main()
