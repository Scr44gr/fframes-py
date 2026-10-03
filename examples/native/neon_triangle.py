"""Port the original neon triangle, SVG bloom, flicker and live readout."""

from pathlib import Path

import fframes
from examples.assets import files
from examples.neon_triangle import (
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
from examples.shaders import GPU_BACKEND, backend_argument, keyframe
from fframes.models import Backend


def build(backend: Backend = GPU_BACKEND) -> fframes.SvgVideo:
    """Compile all six seconds at the original 60 fps."""
    assets = files("neon_triangle")
    indices = range(DURATION * FPS)
    title = fframes.compile_animation(TITLE).sample_many(indices, FPS)
    opacity = fframes.compile_animation((keyframe(SUBTITLE_OPACITY),)).sample_many(indices, FPS)
    x = fframes.compile_animation((keyframe(SUBTITLE_X),)).sample_many(indices, FPS)
    readout = readouts()
    frames = tuple(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}">'
        '<defs><filter id="neon" x="-20%" y="-50%" width="140%" height="200%">'
        '<feGaussianBlur in="SourceAlpha" stdDeviation="5" result="tight"/>'
        '<feGaussianBlur in="SourceAlpha" stdDeviation="18" result="wide"/>'
        '<feMerge result="blur"><feMergeNode in="tight"/><feMergeNode in="wide"/></feMerge>'
        '<feFlood flood-color="#ff2bd6" result="tint"/>'
        '<feComposite in="tint" in2="blur" operator="in" result="glow"/>'
        '<feMerge><feMergeNode in="glow"/><feMergeNode in="glow"/>'
        '<feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#000000"/>'
        '<image href="shader:triangle" x="820" y="0" width="1100" height="1080"/>'
        f'<g opacity="{title[i]}" filter="url(#neon)" font-family="DM Sans" '
        'font-weight="500" fill="#ffffff"><text x="140" y="480" font-size="190" '
        'letter-spacing="6">NEON</text><text x="146" y="620" font-size="104" '
        'letter-spacing="14">TRIANGLE</text></g>'
        f'<g opacity="{opacity[i]}" transform="translate({x[i]} 0)">'
        '<text x="148" y="720" font-family="JetBrains Mono" font-size="30" fill="#f5d0fe">'
        "one SkSL shader, drawn by Skia on the GPU</text></g>"
        '<text x="148" y="1000" font-family="JetBrains Mono" font-size="24" '
        f'fill="#a78bfa" opacity="{opacity[i]}">{readout[i]}</text></svg>'
        for i in indices
    )
    return fframes.compile_video(
        fframes.VideoConfig(
            width=WIDTH,
            height=HEIGHT,
            fps=FPS,
            backend=backend,
            fonts=(assets["dm_sans"], assets["jetbrains_mono"]),
        ),
        frames,
        shaders=(fframes.ShaderBinding(name="triangle", shader=program(assets)),),
    )


def main() -> None:
    """Render output/native/neon_triangle.mp4 using the selected backend."""
    path = Path("output/native/neon_triangle.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    fframes.render(build(backend_argument()), path)


if __name__ == "__main__":
    main()
