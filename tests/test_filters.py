import pytest
from pydantic import ValidationError

import fframes
from fframes import compose
from fframes.models import Backend


@pytest.mark.parametrize("backend", ["cpu", "skia"])
def test_filter_graph_matches_svg_and_is_clipped_after_filtering(backend: Backend) -> None:
    effect = compose.Filter(
        region=(-1, -1, 3, 3),
        steps=(
            compose.Blur(result="blur", source="SourceAlpha", sigma=(2, 2)),
            compose.Flood(result="tint", color="#ff0000"),
            compose.Composite(result="glow", source="tint", destination="blur", operator="in"),
            compose.Merge(result="final", sources=("glow", "SourceGraphic")),
        ),
    )
    scene = compose.Video(
        resolution=(32, 32),
        backend=backend,
        load_system_fonts=False,
        composition=compose.Composition(
            duration=1,
            children=(
                compose.Rectangle(
                    size=(8, 8),
                    fill="#ffffff",
                    position=compose.Position(x=12, y=12),
                    filter=effect,
                    mask=compose.Mask(size=(16, 16), position=(-2, -2)),
                ),
            ),
        ),
    ).compile()
    reference = fframes.compile_video(
        fframes.VideoConfig(width=32, height=32, backend=backend),
        (
            '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
            '<defs><filter id="f" x="-100%" y="-100%" width="300%" height="300%">'
            '<feGaussianBlur in="SourceAlpha" stdDeviation="2" result="blur"/>'
            '<feFlood flood-color="#ff0000" result="tint"/>'
            '<feComposite in="tint" in2="blur" operator="in" result="glow"/>'
            '<feMerge><feMergeNode in="glow"/><feMergeNode in="SourceGraphic"/></feMerge>'
            '</filter><clipPath id="c"><rect x="-2" y="-2" width="16" height="16"/>'
            "</clipPath></defs>"
            '<g transform="translate(12 12)" filter="url(#f)" clip-path="url(#c)">'
            '<rect width="8" height="8" fill="white"/></g></svg>',
        ),
    )
    assert scene.rgba(0) == reference.rgba(0)
    halo = (11 * 32 + 11) * 4
    assert scene.rgba(0)[halo + 3] > 0
    assert scene.rgba(0)[:4] == bytes(4)


def test_filter_graph_rejects_forward_and_duplicate_references() -> None:
    with pytest.raises(ValidationError, match="prior results"):
        compose.Filter(steps=(compose.Blur(result="a", source="missing", sigma=(1, 1)),))
    with pytest.raises(ValidationError, match="unique"):
        compose.Filter(steps=(compose.Flood(result="SourceAlpha", color="#ffffff"),))
    with pytest.raises(ValidationError, match="positive"):
        compose.Filter(
            steps=(compose.Merge(result="a", sources=("SourceGraphic",)),), region=(0, 0, 0, 1)
        )
