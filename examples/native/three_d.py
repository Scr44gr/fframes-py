"""Nest SVG and 3D through native image bindings: python -m examples.native.three_d."""

import fframes
from examples.shared import three_d as shared
from fframes import three_d as d


def build(
    size: tuple[int, int] = (640, 360),
    settings: d.RenderSettings = shared.SETTINGS,
) -> fframes.Video:
    """Compile an SVG display into a texture, then a 3D monitor into the final SVG."""
    width, height = size
    scene = shared.cube(size, settings)
    screen = d.Texture(
        source=d.SvgTexture(
            size=size,
            frames=(
                f'<svg width="{width}" height="{height}">'
                f'<rect width="{width}" height="{height}" fill="#080b12"/>'
                f'<image href="scene:cube" width="{width}" height="{height}"/>'
                f'<rect y="{height - 3}" width="{width}" height="3" fill="#3288ff"/></svg>',
            ),
            scenes=(d.SceneBinding(name="cube", renderer=scene),),
        )
    )
    display = shared.monitor(screen, size, settings)
    svg = (
        f'<svg width="{width}" height="{height}">'
        f'<image href="scene:monitor" width="{width}" height="{height}"/></svg>'
    )
    return fframes.Video(
        config=fframes.VideoConfig(width=width, height=height, fps=shared.FPS),
        frames=(svg,) * (shared.DURATION * shared.FPS),
        scenes=(d.SceneBinding(name="monitor", renderer=display),),
    )


def main() -> None:
    """Export the native example."""
    shared.export(build().native, "native")


if __name__ == "__main__":
    main()
