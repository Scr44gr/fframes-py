from pathlib import Path

import fframes
from examples.compose.reveals import build_video


def test_reveals_example_matches_svg_and_holds_until_the_local_clip_ends() -> None:
    font = Path(__file__).parent / "assets/Tuffy.ttf"
    video = build_video(fonts=(font,)).compile()
    assert len(video) == 75
    assert not any(video.rgba(14))
    assert not any(video.rgba(15))
    for frame, width, radius, opacity, label in (
        (30, 120.5, 8, 0.5, "Frame 15"),
        (45, 240, 16, 1, "Frame 30"),
    ):
        reference = fframes.Video(
            config=fframes.VideoConfig(width=320, height=180, fonts=(font,)),
            frames=(
                '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180">'
                '<g transform="translate(24 24)" fill="#0088FF">'
                f'<rect width="{width}" height="16" opacity="{opacity}"/>'
                f'<circle cx="{radius}" cy="{40 + radius}" r="{radius}"/>'
                '<text x="0" y="104" font-family="sans-serif" font-size="24" '
                f'font-weight="700">{label}</text></g></svg>',
            ),
        )
        assert video.rgba(frame) == reference.rgba()
    assert video.rgba(59) == video.rgba(45)
    assert not any(video.rgba(60))
