import pytest
from pydantic import ValidationError

import fframes
from fframes import compose
from fframes.models import Backend


@pytest.mark.parametrize("backend", ["cpu", "skia"])
def test_animated_mask_and_difference_blending_match_svg(backend: Backend) -> None:
    values = (4, 12, 20)
    scene = compose.Video(
        resolution=(32, 24),
        fps=1,
        backend=backend,
        load_system_fonts=False,
        composition=compose.Composition(
            duration=3,
            children=(
                compose.Rectangle(size=(32, 24), fill="#804020"),
                compose.Composition(
                    blend_mode="difference",
                    mask=compose.Mask(
                        size=(compose.Samples(values=values, fps=1), 12),
                        position=(compose.Samples(values=(2, 4, 6), fps=1), 4),
                        radius=compose.Samples(values=(0, 2, 4), fps=1),
                    ),
                    children=(compose.Rectangle(size=(32, 24), fill="#ffffff"),),
                ),
            ),
        ),
    ).compile()
    raw = fframes.Video(
        config=fframes.VideoConfig(width=32, height=24, fps=1, backend=backend),
        frames=tuple(
            '<svg width="32" height="24"><rect width="32" height="24" fill="#804020"/>'
            f'<clipPath id="m"><rect x="{2 + 2 * i}" y="4" width="{width}" height="12" '
            f'rx="{2 * i}"/></clipPath><g style="mix-blend-mode:difference" clip-path="url(#m)">'
            '<rect width="32" height="24" fill="white"/></g></svg>'
            for i, width in enumerate(values)
        ),
    )
    for index in (2, 0, 1):
        assert raw.rgba(index) == scene.rgba(index)
        assert scene.rgba(index)[:4] == bytes((128, 64, 32, 255))
        p = (10 * 32 + 3 + index * 2) * 4
        assert scene.rgba(index)[p : p + 4] == bytes((127, 191, 223, 255))


def test_mask_rejects_invalid_animated_geometry() -> None:
    with pytest.raises(ValidationError, match="size"):
        compose.Mask(size=(compose.Samples(values=(1, 0), fps=1), 4))
    with pytest.raises(ValidationError, match="radius"):
        compose.Mask(size=(4, 4), radius=-1)
    with pytest.raises(ValidationError, match="coordinates"):
        compose.Mask(size=(4, 4), position=(1e8, 0))
