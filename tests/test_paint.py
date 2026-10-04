from pathlib import Path

import pytest
from pydantic import ValidationError

import fframes
from fframes.compose import (
    Circle,
    Composition,
    LinearGradient,
    Pattern,
    Position,
    RadialGradient,
    Rectangle,
    Samples,
    Stop,
    Stroke,
    Text,
    TextRun,
    VectorPath,
    Video,
)


def pixel(data: bytes, x: int, y: int, width: int = 32) -> bytes:
    index = (y * width + x) * 4
    return data[index : index + 4]


def test_gradients_have_independent_ids_and_preserve_stop_alpha() -> None:
    scene = Video(
        resolution=(32, 16),
        fps=1,
        load_system_fonts=False,
        composition=Composition(
            duration=1,
            children=(
                Rectangle(
                    size=(16, 16),
                    fill=LinearGradient(
                        stops=(
                            Stop(offset=0, color="#ff000080"),
                            Stop(offset=1, color="#0000ff80"),
                        )
                    ),
                ),
                Rectangle(
                    size=(16, 16),
                    position=Position(x=16),
                    fill=RadialGradient(
                        stops=(
                            Stop(offset=0, color="#ffffff"),
                            Stop(offset=1, color="#000000"),
                        )
                    ),
                ),
            ),
        ),
    ).compile()
    data = scene.rgba(0)
    assert pixel(data, 0, 8)[3] == 128
    assert pixel(data, 0, 8)[0] > 240
    assert pixel(data, 15, 8)[2] > 240
    assert pixel(data, 24, 8)[0] > 220
    assert pixel(data, 16, 0) == bytes.fromhex("000000ff")


def test_pattern_transform_is_evaluated_on_the_local_clock(tmp_path: Path) -> None:
    image = tmp_path / "tile.png"
    fframes.Video(
        config=fframes.VideoConfig(width=4, height=2, fps=1),
        frames=(
            '<svg width="4" height="2"><path d="M0 0h2v2H0z" fill="red"/>'
            '<path d="M2 0h2v2H2z" fill="blue"/></svg>',
        ),
    ).native.save_png(0, image)
    shape = Rectangle(
        size=(32, 8),
        fill=Pattern(
            source=image,
            size=(4, 2),
            matrix=(
                1,
                0,
                0,
                1,
                Samples(values=(0, 2), fps=1),
                0,
            ),
        ),
    )
    scene = Video(
        resolution=(32, 8),
        fps=1,
        load_system_fonts=False,
        composition=Composition(duration=3, children=(shape.at(1),)),
    ).compile()
    assert not any(scene.rgba(0))
    assert pixel(scene.rgba(1), 0, 0) == bytes.fromhex("ff0000ff")
    assert pixel(scene.rgba(2), 0, 0) == bytes.fromhex("0000ffff")


def test_animated_matrix_and_dash_offset_match_svg() -> None:
    scene = Video(
        resolution=(32, 8),
        fps=1,
        load_system_fonts=False,
        composition=Composition(
            duration=2,
            children=(
                VectorPath(
                    size=(32, 8),
                    segments="M0 2H28",
                    fill=None,
                    rendering="crispEdges",
                    matrix=(1, 0, 0, 1, 0, Samples(values=(0, 4), fps=1)),
                    stroke=Stroke(
                        color="#ffffff",
                        width=2,
                        dash=(4, 4),
                        dash_offset=Samples(values=(0, 4), fps=1),
                    ),
                ),
            ),
        ),
    ).compile()
    reference = fframes.Video(
        config=fframes.VideoConfig(width=32, height=8, fps=1),
        frames=tuple(
            f'<svg width="32" height="8"><path d="M0 {y}H28" stroke="white" '
            f'stroke-width="2" stroke-dasharray="4 4" stroke-dashoffset="{offset}" '
            'shape-rendering="crispEdges"/></svg>'
            for y, offset in ((2, 0), (6, 4))
        ),
    )
    for index in (1, 0, 1):
        assert scene.rgba(index) == reference.native.rgba(index)
    with pytest.raises(ValidationError, match="ascending"):
        LinearGradient(stops=(Stop(offset=1, color="#ffffff"), Stop(offset=0, color="#000000")))
    with pytest.raises(ValidationError):
        Stroke(color="#ffffff", dash=(-1, 2))


@pytest.mark.parametrize(("dx", "dy"), [(0, 0), (3, -2)])
def test_text_runs_preserve_spacing_inherited_style_and_shared_anchor(dx: int, dy: int) -> None:
    font = Path(__file__).parent / "assets/Tuffy.ttf"
    text = Text(
        content=(
            TextRun(content="Hello "),
            TextRun(content="world", fill="#ff0000", font_size=20, dx=dx, dy=dy),
        ),
        font_family="Tuffy",
        font_size=16,
        fill="#ffffff",
        anchor="baseline",
        text_anchor="middle",
        position=Position(x=80, y=28),
    )
    scene = Video(
        resolution=(160, 40),
        fps=1,
        fonts=(font,),
        load_system_fonts=False,
        composition=Composition(duration=1, children=(text,)),
    )
    reference = fframes.Video(
        config=fframes.VideoConfig(width=160, height=40, fps=1, fonts=(font,)),
        frames=(
            '<svg width="160" height="40" xml:space="preserve"><text x="80" y="28" '
            'font-family="Tuffy" font-size="16" fill="white" text-anchor="middle">'
            f'<tspan>Hello </tspan><tspan font-size="20" fill="red" dx="{dx}" dy="{dy}">'
            "world</tspan></text></svg>",
        ),
    )
    assert scene.rgba(0) == reference.rgba(0)


def test_zero_radius_reveal_and_animated_dash_lengths_use_the_clip_clock() -> None:
    scene = Video(
        resolution=(32, 16),
        fps=2,
        load_system_fonts=False,
        composition=Composition(
            duration=2,
            children=(
                Composition(
                    children=(
                        Circle(radius=Samples(values=(0, 4, 8), fps=2), fill="#ff0000"),
                        VectorPath(
                            size=(32, 16),
                            segments="M0 12H32",
                            fill=None,
                            stroke=Stroke(
                                color="#ffffff", width=2, dash=(Samples(values=(0, 4, 8), fps=2), 4)
                            ),
                        ),
                    )
                ).at(0.5),
            ),
        ),
    )
    reference = fframes.Video(
        config=fframes.VideoConfig(width=32, height=16, fps=2),
        frames=tuple(
            f'<svg width="32" height="16"><circle cx="{r}" cy="{r}" r="{r}" fill="red"/>'
            f'<path d="M0 12H32" stroke="white" stroke-width="2" stroke-dasharray="{r} 4"/></svg>'
            for r in (0, 4, 8)
        ),
    )
    assert not any(scene.rgba(0))
    for index in (3, 1, 2):
        assert scene.rgba(index) == reference.rgba(index - 1)
    with pytest.raises(ValidationError, match="radius"):
        Circle(radius=Samples(values=(1, -1), fps=2))


def test_rounded_rectangle_keeps_circular_corners_while_expanding() -> None:
    scene = Video(
        resolution=(40, 20),
        fps=1,
        load_system_fonts=False,
        composition=Composition(
            duration=2,
            children=(
                Rectangle(
                    size=(36, Samples(values=(10, 18), fps=1)),
                    radius=Samples(values=(5, 9), fps=1),
                    fill="#ffffff",
                ),
            ),
        ),
    )
    reference = fframes.Video(
        config=fframes.VideoConfig(width=40, height=20, fps=1),
        frames=tuple(
            f'<svg width="40" height="20"><rect width="36" height="{h}" '
            f'rx="{h / 2}" fill="white"/></svg>'
            for h in (10, 18)
        ),
    )
    for index in (1, 0):
        assert scene.rgba(index) == reference.rgba(index)
    with pytest.raises(ValidationError, match="radius"):
        Rectangle(size=(10, 10), radius=Samples(values=(-1, 1), fps=1))
