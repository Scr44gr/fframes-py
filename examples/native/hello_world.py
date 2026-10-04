"""Port upstream hello-world using SVG, native animation and explicit font files."""

from html import escape
from pathlib import Path

import fframes
from examples.assets import files
from examples.hello_world import DURATION, FPS, HEIGHT, WIDTH, background, coordinate


def document(
    content: str, index: int, color: str, counter_color: str = "#3B5563", *, fps: int = FPS
) -> str:
    """Wrap scene content with the shared global background and frame readout."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}">'
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{color}"/>'
        f'{content}<text x="100" y="440" font-family="JetBrains Mono" font-size="74" '
        f'font-weight="500" fill="{counter_color}">This frame index: {index}, '
        f"second: {index / fps:.2f}</text></svg>"
    )


def build(slug: str = "Renderer!") -> fframes.SvgVideo:
    """Compile the complete thirty-second original scene."""
    return video(slug).native


def video(slug: str = "Renderer!", *, fps: int = FPS) -> fframes.Video:
    """Keep frames and bindings reusable in the beta demonstration."""
    assets = files("hello_world")
    count = DURATION * fps
    indices = range(count)
    x = fframes.compile_animation(coordinate(0)).sample_many(indices, fps)
    y = fframes.compile_animation(coordinate(1)).sample_many(indices, fps)
    colors = fframes.compile_color_animation(background()).sample_many(indices, fps)
    title = escape(slug)
    frames = tuple(
        document(
            f'<rect x="{x[i]}" y="{y[i]}" width="200" height="200" fill="blue"/>'
            f'<text x="99" y="300" font-family="DM Sans" font-size="150" fill="#000">'
            f"Hello {title}</text>",
            i,
            colors[i],
            fps=fps,
        )
        for i in indices
    )
    return fframes.Video(
        config=fframes.VideoConfig(
            width=WIDTH, height=HEIGHT, fps=fps, fonts=(assets["dm_sans"], assets["jetbrains_mono"])
        ),
        frames=frames,
    )


def main() -> None:
    """Render the upstream scene to output/native/hello_world.mp4."""
    path = Path("output/native/hello_world.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    fframes.render(build(), path)


if __name__ == "__main__":
    main()
