import pytest

from fframes import compose as c
from fframes.models import Backend


@pytest.mark.parametrize("backend", ["cpu", "skia"])
def test_depth_animation_keeps_original_ties_and_local_clock(backend: Backend) -> None:
    red = c.Rectangle(size=(8, 8), fill="#ff0000", z_index=c.Samples(values=(2, 0, -2), fps=1))
    blue = c.Rectangle(size=(8, 8), fill="#0000ff")
    scene = c.Video(
        resolution=(8, 8),
        fps=1,
        backend=backend,
        load_system_fonts=False,
        composition=c.Composition(
            duration=4, children=(c.Composition(children=(red, blue)).at(1, duration=3),)
        ),
    ).compile()
    for frame, color in (
        (3, b"\x00\x00\xff\xff"),
        (1, b"\xff\x00\x00\xff"),
        (2, b"\x00\x00\xff\xff"),
        (0, b"\x00" * 4),
    ):
        assert scene.rgba(frame) == color * 64


def test_static_root_depth_overrides_insertion_order() -> None:
    scene = c.Video(
        resolution=(4, 4),
        load_system_fonts=False,
        composition=c.Composition(
            duration=1,
            children=(
                c.Rectangle(size=(4, 4), fill="#ff0000", z_index=2),
                c.Rectangle(size=(4, 4), fill="#0000ff", z_index=1),
            ),
        ),
    ).compile()
    assert scene.rgba(0) == b"\xff\x00\x00\xff" * 16
