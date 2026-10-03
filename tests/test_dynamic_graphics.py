from pathlib import Path

import pytest
from pydantic import ValidationError

import fframes
from fframes import compose

FONT = Path(__file__).parent / "assets/Tuffy.ttf"


def test_direct_video_owns_explicit_font_data(tmp_path: Path) -> None:
    source = tmp_path / "font.ttf"
    source.write_bytes(FONT.read_bytes())
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="64">'
        '<text x="4" y="40" font-family="Tuffy" font-size="30">Font</text></svg>'
    )
    config = fframes.VideoConfig(width=128, height=64, fonts=(source,))
    video = fframes.compile_video(config, (svg,))
    expected = video.rgba(0)
    source.unlink()
    assert any(expected[3::4])
    assert video.rgba(0) == expected
    with pytest.raises(FileNotFoundError):
        fframes.compile_video(config, (svg,))
    source.write_bytes(b"not a font")
    with pytest.raises(ValueError, match="invalid font"):
        fframes.compile_video(config, (svg,))


def test_animated_fill_and_stroke_follow_native_color_interpolation() -> None:
    color = compose.ColorTween(from_value="#FF0000", to_value="#0000FF", duration=1)
    video = compose.Video(
        resolution=(16, 16),
        fps=10,
        load_system_fonts=False,
        composition=compose.Composition(
            duration=2,
            children=(
                compose.Rectangle(size=(16, 16), fill=color),
                compose.Circle(
                    radius=4,
                    position=compose.Position(x=4, y=4),
                    fill=None,
                    stroke=compose.Stroke(color=color, width=2),
                ),
            ),
        ),
    ).compile()
    for frame, expected in (
        (15, b"\x00\x00\xff\xff"),
        (5, b"\x7f\x00\x7f\xff"),
        (0, b"\xff\x00\x00\xff"),
    ):
        pixels = video.rgba(frame)
        assert pixels[:4] == expected
        assert pixels[(8 * 16 + 4) * 4 : (8 * 16 + 5) * 4] == expected


def test_text_templates_use_local_time_and_baseline_coordinates() -> None:
    template = "{{{frame}}} {seconds:.2f}"
    video = compose.Video(
        resolution=(128, 64),
        fps=10,
        load_system_fonts=False,
        fonts=(FONT,),
        composition=compose.Composition(
            duration=2,
            children=(
                compose.Text(
                    content=compose.TextTemplate(template=template),
                    position=compose.Position(x=4, y=40),
                    anchor="baseline",
                    font_family="Tuffy",
                    font_size=24,
                ).at(0.5, duration=1),
            ),
        ),
    ).compile()
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="64">'
        '<text x="4" y="40" font-family="Tuffy" font-size="24">{5} 0.50</text></svg>'
    )
    reference = fframes.compile_video(
        fframes.VideoConfig(width=128, height=64, fonts=(FONT,)), (svg,)
    )
    assert video.rgba(10) == reference.rgba(0)
    assert not any(video.rgba(4))
    assert not any(video.rgba(15))


@pytest.mark.parametrize(
    "template", ["{typo}", "{seconds}", "{frame!r}", "{frame:}", "{seconds:.12f}", "{"]
)
def test_text_templates_reject_unsupported_formatting(template: str) -> None:
    with pytest.raises(ValidationError):
        compose.TextTemplate(template=template)


def test_text_templates_require_explicit_baseline_position() -> None:
    content = compose.TextTemplate(template="{frame}")
    with pytest.raises(ValidationError, match="baseline"):
        compose.Text(content=content)
    with pytest.raises(ValidationError, match="numeric positions"):
        compose.Text(content=content, anchor="baseline", position=compose.Position(x="center"))


def test_group_origin_matches_svg_rotation_about_local_zero() -> None:
    video = compose.Video(
        resolution=(16, 16),
        load_system_fonts=False,
        composition=compose.Composition(
            duration=1,
            children=(
                compose.Composition(
                    size=(8, 8),
                    position=compose.Position(x=10),
                    rotation=90,
                    origin=(0, 0),
                    children=(compose.Rectangle(size=(6, 2), position=compose.Position(x=2, y=1)),),
                ),
            ),
        ),
    ).compile()
    reference = fframes.compile_video(
        fframes.VideoConfig(width=16, height=16),
        (
            '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">'
            '<g transform="translate(10 0) rotate(90)">'
            '<rect x="2" y="1" width="6" height="2"/></g></svg>',
        ),
    )
    assert video.rgba(0) == reference.rgba(0)
    assert sum(video.rgba(0)[3::4]) == 12 * 255
    with pytest.raises(ValidationError, match="origin coordinates"):
        compose.Rectangle(size=(6, 2), origin=(1e8, 0))
