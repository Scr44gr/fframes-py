"""Port the original neon triangle with typed filter graphs and reusable text."""

from pathlib import Path

from examples.assets import files
from examples.shared.neon_triangle import (
    DURATION,
    FPS,
    HEIGHT,
    SUBTITLE_OPACITY,
    SUBTITLE_X,
    TITLE,
    WIDTH,
    program,
    readouts,
)
from examples.shared.shaders import GPU_BACKEND, backend_argument
from fframes.compose import (
    Blur,
    Component,
    Composite,
    Composition,
    Filter,
    Flood,
    Merge,
    Position,
    Rectangle,
    ShaderLayer,
    Text,
    TextFrames,
    Tween,
    Video,
)
from fframes.models import Backend


class NeonTitle(Component):
    """Two text lines with the original tight and wide magenta bloom."""

    def compose(self) -> Composition:
        """Merge the glow twice before painting the white source text."""
        return Composition(
            filter=Filter(
                region=(-0.2, -0.5, 1.4, 2),
                steps=(
                    Blur(result="tight", source="SourceAlpha", sigma=(5, 5)),
                    Blur(result="wide", source="SourceAlpha", sigma=(18, 18)),
                    Merge(result="blur", sources=("tight", "wide")),
                    Flood(result="tint", color="#ff2bd6"),
                    Composite(result="glow", source="tint", destination="blur", operator="in"),
                    Merge(result="output", sources=("glow", "glow", "SourceGraphic")),
                ),
            ),
            children=tuple(
                Text(
                    content=content,
                    position=Position(x=x, y=y),
                    font_family="DM Sans",
                    font_weight=500,
                    font_size=size,
                    letter_spacing=spacing,
                    anchor="baseline",
                    fill="#ffffff",
                )
                for content, x, y, size, spacing in (
                    ("NEON", 140, 480, 190, 6),
                    ("TRIANGLE", 146, 620, 104, 14),
                )
            ),
        )


def build(backend: Backend = GPU_BACKEND) -> Video:
    """Compile the shader and layer timed copies of one reusable title."""
    assets = files("neon_triangle")
    title = NeonTitle()
    flicker = tuple(
        Composition(
            children=(title,),
            opacity=Tween(from_value=k.from_value, to_value=k.to_value, duration=k.end - k.start),
        ).at(k.start, duration=(TITLE[i + 1].start if i + 1 < len(TITLE) else DURATION) - k.start)
        for i, k in enumerate(TITLE)
    )
    return Video(
        resolution=(WIDTH, HEIGHT),
        fps=FPS,
        backend=backend,
        load_system_fonts=False,
        fonts=(assets["dm_sans"], assets["jetbrains_mono"]),
        composition=Composition(
            duration=DURATION,
            children=(
                Rectangle(size=(WIDTH, HEIGHT)),
                ShaderLayer(shader=program(assets), size=(1100, HEIGHT), position=Position(x=820)),
                *flicker,
                Composition(
                    opacity=SUBTITLE_OPACITY,
                    position=Position(x=SUBTITLE_X),
                    children=(
                        Text(
                            content="one SkSL shader, drawn by Skia on the GPU",
                            position=Position(x=148, y=720),
                            font_family="JetBrains Mono",
                            font_size=30,
                            fill="#f5d0fe",
                            anchor="baseline",
                        ),
                    ),
                ),
                Text(
                    content=TextFrames(frames=readouts()),
                    opacity=SUBTITLE_OPACITY,
                    position=Position(x=148, y=1000),
                    font_family="JetBrains Mono",
                    font_size=24,
                    fill="#a78bfa",
                    anchor="baseline",
                ),
            ),
        ),
    )


def main() -> None:
    """Render output/compose/neon_triangle.mp4 using the selected backend."""
    path = Path("output/compose/neon_triangle.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    build(backend_argument()).render(path)


if __name__ == "__main__":
    main()
