"""Port upstream hello-world's two-scene variant with explicit local keyframes."""

from pathlib import Path

import fframes
from examples.assets import files
from examples.native.hello_world import document
from examples.shared.hello_world import DURATION, FPS, HEIGHT, WIDTH, background


def build() -> fframes.SvgVideo:
    """Sequence two fifteen-second scenes while keeping the global background clock."""
    assets = files("hello_world")
    indices = range(DURATION * FPS)
    colors = fframes.compile_color_animation(background()).sample_many(indices, FPS)
    y = fframes.compile_animation(
        (fframes.Keyframe(start=0, end=0.2, from_value=300, to_value=320),)
    ).sample_many(range(15 * FPS), FPS)
    first = (
        '<text font-family="DM Sans" x="100" y="300" font-size="150">hello scene 1</text>'
        '<rect width="120" height="120" fill="green"/>'
        '<rect width="120" height="120" fill="green" transform="rotate(45)"/>'
    )
    frames = tuple(
        document(
            first
            if i < 15 * FPS
            else (
                f'<text x="100" y="{y[i - 15 * FPS]}" font-size="150" '
                'font-family="DM Sans">Hello Scene 2</text>'
            ),
            i,
            colors[i],
            "#4B5563",
        )
        for i in indices
    )
    return fframes.compile_video(
        fframes.VideoConfig(
            width=WIDTH, height=HEIGHT, fps=FPS, fonts=(assets["dm_sans"], assets["jetbrains_mono"])
        ),
        frames,
    )


def main() -> None:
    """Render the two original scenes to output/native/scenes.mp4."""
    path = Path("output/native/scenes.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    fframes.render(build(), path)


if __name__ == "__main__":
    main()
