from pathlib import Path

import pytest
from pydantic import ValidationError

import fframes
from fframes import compose as c


def test_sampled_path_control_points_follow_local_time_and_hold_the_final_shape() -> None:
    changing = c.Samples(values=(2, 8, 14), fps=2)
    path = c.VectorPath(
        size=(24, 24),
        fill="#ff8000",
        segments=(
            c.MoveTo(x=2, y=changing),
            c.CubicTo(control1=(8, changing), control2=(14, 2), end=(20, changing)),
            c.LineTo(x=changing, y=20),
            c.Close(),
        ),
    )
    scene = c.Video(
        resolution=(24, 24),
        fps=2,
        load_system_fonts=False,
        composition=c.Composition(duration=3, children=(path.at(0.5),)),
    ).compile()
    assert not any(scene.rgba(0))
    reference = fframes.Video(
        config=fframes.VideoConfig(width=24, height=24, fps=2),
        frames=tuple(
            f'<svg width="24" height="24"><path fill="#ff8000" '
            f'd="M2 {y} C8 {y} 14 2 20 {y} L{y} 20 Z"/></svg>'
            for y in (2, 8, 14, 14, 14)
        ),
    )
    for index in (5, 1, 3, 2):
        assert scene.rgba(index) == reference.rgba(index - 1)


def test_imported_path_data_preserves_relative_curves_arcs_and_validation() -> None:
    data = "M2 4h8v4q4 0 4 4t4 4a3 3 0 0 1-6 2L2 18z"
    shape = c.VectorPath(size=(24, 24), segments=data, fill="#90a020")
    scene = c.Video(
        resolution=(24, 24),
        load_system_fonts=False,
        composition=c.Composition(duration=1, children=(shape,)),
    )
    raw = fframes.Video(
        config=fframes.VideoConfig(width=24, height=24),
        frames=(f'<svg width="24" height="24"><path d="{data}" fill="#90a020"/></svg>',),
    )
    assert scene.rgba(0) == raw.rgba(0)
    for invalid in ("", "M0 0", "M0 0 L1e999 2", "M0 0 NOT_A_PATH", "L0 0 4 4"):
        with pytest.raises(ValidationError):
            c.VectorPath(size=(24, 24), segments=invalid)


def test_outlined_text_and_color_matrix_offset_match_native_filter_graph() -> None:
    font = Path(__file__).parent / "assets/Tuffy.ttf"
    effect = c.Filter(
        region=(-1, -1, 3, 3),
        color_space="srgb",
        steps=(
            c.ColorMatrix(
                result="tint",
                values=(
                    (0, 0, 0, 0, 0),
                    (0, 0, 0, 0, 1),
                    (0, 0, 0, 0, 0),
                    (0, 0, 0, 0.5, 0),
                ),
            ),
            c.Offset(result="moved", source="tint", dx=3, dy=2),
        ),
    )
    scene = c.Video(
        resolution=(48, 48),
        fonts=(font,),
        load_system_fonts=False,
        composition=c.Composition(
            duration=1,
            children=(
                c.Text(
                    content="Hi",
                    font_family="Tuffy",
                    font_size=24,
                    fill=None,
                    stroke=c.Stroke(color="#ff0000", width=2),
                    anchor="baseline",
                    position=c.Position(x=8, y=28),
                    filter=effect,
                ),
            ),
        ),
    )
    raw = fframes.Video(
        config=fframes.VideoConfig(width=48, height=48, fonts=(font,)),
        frames=(
            '<svg width="48" height="48"><defs><filter id="f" x="-100%" y="-100%" '
            'width="300%" height="300%" color-interpolation-filters="sRGB">'
            '<feColorMatrix values="0 0 0 0 0  0 0 0 0 1  0 0 0 0 0  0 0 0 .5 0"/>'
            '<feOffset dx="3" dy="2"/></filter></defs><g transform="translate(8 28)" '
            'filter="url(#f)"><text font-family="Tuffy" font-size="24" fill="none" '
            'stroke="red" stroke-width="2">Hi</text></g></svg>',
        ),
    )
    pixels = scene.rgba(0)
    assert pixels == raw.rgba(0)
    assert max(pixels[3::4]) in (127, 128)
    assert max(pixels[1::4]) == 255
