from pathlib import Path

import pytest
from pydantic import ValidationError

import fframes
from fframes import compose


def test_samples_resize_and_move_on_the_local_clock_with_endpoint_holds() -> None:
    video = compose.Video(
        resolution=(16, 8),
        fps=10,
        load_system_fonts=False,
        composition=compose.Composition(
            duration=1,
            children=(
                compose.Rectangle(
                    size=(compose.Samples(values=(2, 4, 6), fps=5), 2),
                    position=compose.Position(x=compose.Samples(values=(0, 4, 8), fps=5)),
                    fill="#ff0000",
                ).at(0.2),
            ),
        ),
    ).compile()
    for frame, x, width in ((0, 0, 0), (2, 0, 2), (3, 0, 2), (4, 4, 4), (9, 8, 6), (2, 0, 2)):
        expected = bytearray(16 * 8 * 4)
        for y in range(2):
            expected[(y * 16 + x) * 4 : (y * 16 + x + width) * 4] = b"\xff\0\0\xff" * width
        assert video.rgba(frame) == expected


def test_text_anchor_style_and_empty_frames_match_svg() -> None:
    font = Path(__file__).parent / "assets/Tuffy.ttf"
    video = compose.Video(
        resolution=(200, 80),
        fps=2,
        fonts=(font,),
        load_system_fonts=False,
        composition=compose.Composition(
            duration=1,
            children=(
                compose.Text(
                    content=compose.TextFrames(frames=("", "hello")),
                    font_family="Tuffy",
                    font_size=24,
                    font_style="italic",
                    anchor="baseline",
                    text_anchor="middle",
                    baseline="central",
                    position=compose.Position(x=100, y=40),
                ),
            ),
        ),
    )
    reference = fframes.Video(
        config=fframes.VideoConfig(width=200, height=80, fonts=(font,)),
        frames=(
            '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="80">'
            '<text x="100" y="40" font-family="Tuffy" font-size="24" font-style="italic" '
            'text-anchor="middle" dominant-baseline="central">hello</text></svg>',
        ),
    )
    assert not any(video.rgba(0))
    assert video.rgba(1) == reference.rgba(0)


def test_samples_reject_invalid_values_and_animated_extents() -> None:
    with pytest.raises(ValidationError):
        compose.Samples(values=(), fps=30)
    with pytest.raises(ValidationError):
        compose.Samples(values=(float("nan"),), fps=30)
    with pytest.raises(ValidationError):
        compose.Rectangle(size=(compose.Samples(values=(1, 0), fps=30), 4))
    with pytest.raises(ValidationError):
        compose.Rectangle(size=(4, 4), opacity=compose.Samples(values=(0, 1.1), fps=30))
