from pathlib import Path

import pytest

from fframes import Video as RawVideo
from fframes import VideoConfig
from fframes.compose import Composition, Position, Text, Video
from fframes.models import Backend


@pytest.mark.parametrize("backend", ["cpu", "skia"])
def test_clipped_text_does_not_poison_another_copy(backend: Backend) -> None:
    fonts = (Path(__file__).parent / "assets/Tuffy.ttf",)
    positions = ((80, 124), (80, 64))
    composed = Video(
        resolution=(160, 128),
        backend=backend,
        fonts=fonts,
        load_system_fonts=False,
        composition=Composition(
            duration=1,
            children=tuple(
                Text(
                    content="2023",
                    font_family="Tuffy",
                    font_size=44,
                    anchor="baseline",
                    text_anchor="middle",
                    baseline="middle",
                    position=Position(x=x, y=y),
                )
                for x, y in positions
            ),
        ),
    ).compile()
    raw = RawVideo(
        config=VideoConfig(
            width=160, height=128, backend=backend, fonts=fonts, load_system_fonts=False
        ),
        frames=(
            '<svg width="160" height="128">'
            + "".join(
                f'<text x="{x}" y="{y}" font-family="Tuffy" font-size="44" '
                'text-anchor="middle" dominant-baseline="middle">2023</text>'
                for x, y in positions
            )
            + "</svg>",
        ),
    )
    assert composed.rgba(0) == raw.rgba(0)
