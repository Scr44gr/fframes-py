"""Port upstream SkSL and Shadertoy layers with SVG composition."""

from pathlib import Path

import fframes
from examples.assets import files
from examples.shaders import (
    CARD_OPACITY,
    CARD_Y,
    DURATION,
    FPS,
    GPU_BACKEND,
    HEIGHT,
    TITLE_OPACITY,
    WIDTH,
    backend_argument,
    keyframe,
    programs,
)
from fframes.models import Backend


def build(backend: Backend = GPU_BACKEND) -> fframes.SvgVideo:
    """Compile the original eight-second scene with two native shader bindings."""
    assets = files("shaders")
    aurora, torus = programs(assets)
    indices = range(DURATION * FPS)
    y, card, title = (
        fframes.compile_animation((keyframe(tween),)).sample_many(indices, FPS)
        for tween in (CARD_Y, CARD_OPACITY, TITLE_OPACITY)
    )
    frames = tuple(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}">'
        '<defs><clipPath id="card"><rect x="1040" y="160" width="760" '
        'height="760" rx="40"/></clipPath></defs>'
        f'<image href="shader:aurora" width="{WIDTH}" height="{HEIGHT}"/>'
        f'<g transform="translate(0 {y[i] - 160})" opacity="{card[i]}">'
        '<g clip-path="url(#card)"><image href="shader:torus" x="1040" y="160" '
        'width="760" height="760"/></g><rect x="1040" y="160" width="760" '
        'height="760" rx="40" fill="none" stroke="#ffffff" stroke-opacity="0.2" '
        'stroke-width="2"/></g>'
        f'<g opacity="{title[i]}" font-family="DM Sans" font-weight="500">'
        '<text x="120" y="500" font-size="128" fill="#ffffff">GPU shaders</text>'
        '<text x="126" y="580" font-size="40" fill="#f5f3ff" fill-opacity="0.8">'
        "SkSL and Shadertoy, drawn by Skia</text></g></svg>"
        for i in indices
    )
    return fframes.compile_video(
        fframes.VideoConfig(
            width=WIDTH, height=HEIGHT, fps=FPS, backend=backend, fonts=(assets["dm_sans"],)
        ),
        frames,
        shaders=(
            fframes.ShaderBinding(name="aurora", shader=aurora),
            fframes.ShaderBinding(name="torus", shader=torus),
        ),
    )


def main() -> None:
    """Render the original programs to output/native/shaders.mp4."""
    path = Path("output/native/shaders.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    fframes.render(build(backend_argument()), path)


if __name__ == "__main__":
    main()
