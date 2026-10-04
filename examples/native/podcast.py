"""The original bird podcast layout authored with SVG and local media bindings."""

from pathlib import Path

import fframes
from examples.shared.podcast import (
    DURATION,
    FPS,
    HEIGHT,
    SPEAKERS,
    WIDTH,
    YELLOW,
    arguments,
    prepare,
)


def build(
    goose: Path | None = None, guest: Path | None = None, duck: Path | None = None
) -> fframes.SvgVideo:
    """Use the original mixed track; optional voice stems only animate their bars."""
    return video(goose, guest, duck).native


def video(
    goose: Path | None = None, guest: Path | None = None, duck: Path | None = None
) -> fframes.Video:
    """Keep frames and bindings reusable in the beta demonstration."""
    data = prepare((goose, guest, duck))
    defs = (
        '<clipPath id="right-section-mask"><rect x="970.797" y="-143.12" '
        'width="723" height="1446.02"/></clipPath>'
        '<clipPath id="character-detail-clip"><rect x="906.547" y="161.456" '
        'width="350.203" height="350.203"/></clipPath>'
        + "".join(
            f'<clipPath id="{name}"><circle r="180" cx="{400 + i * 560}" cy="680"/></clipPath>'
            for i, name in enumerate(SPEAKERS)
        )
    )
    artwork = data.markup.replace(
        'mask="url(#right-section-mask)"', 'clip-path="url(#right-section-mask)"'
    )
    background = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}">'
        f"<defs>{defs}</defs>"
        + artwork
        + "".join(
            f'<image href="image:{name}" x="{220 + i * 560}" y="500" width="360" height="360" '
            f'clip-path="url(#{name})"/><circle cx="{400 + i * 560}" cy="680" r="180" '
            'fill="none" stroke="black" stroke-width="16"/>'
            for i, name in enumerate(SPEAKERS)
        )
    )
    guest_width = 48 + (320 if "guest" in data.heights else 0)
    background += (
        f'<rect x="{960 - guest_width / 2}" y="900" width="{guest_width}" height="100" rx="32"/>'
    )
    frames = (
        tuple(
            background
            + "".join(
                f'<rect x="{240 + SPEAKERS.index(name) * 560 + i * 20}" y="{950 - float(h) / 2}" '
                f'width="16" height="{float(h)}" rx="4" '
                f'fill="{YELLOW if name == "guest" else "#000000"}"/>'
                for name, heights in data.heights.items()
                for i, h in enumerate(heights[frame])
            )
            + "</svg>"
            for frame in range(DURATION * FPS)
        )
        if data.heights
        else (background + "</svg>",) * (DURATION * FPS)
    )
    return fframes.Video(
        config=fframes.VideoConfig(width=WIDTH, height=HEIGHT, fps=FPS),
        frames=frames,
        images=tuple(
            fframes.ImageBinding(name=s, source=data.assets[f"podcast_{s}"]) for s in SPEAKERS
        ),
        audio=(fframes.AudioTrack(source=data.assets["podcast_audio"], duration=DURATION),),
    )


def main() -> None:
    """Render the complete minute into output/native."""
    args = arguments()
    path = Path("output/native/podcast.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    fframes.render(
        build(args.goose_audio, args.guest_audio, args.duck_audio),
        path,
        options=fframes.RenderOptions(concurrency=2),
    )


if __name__ == "__main__":
    main()
