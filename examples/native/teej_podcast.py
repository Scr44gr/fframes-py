"""Two synchronized interviews, clipped panels and a measured chapter list in SVG."""

from bisect import bisect_right
from html import escape
from pathlib import Path

import fframes
from examples.teej_podcast import CHAPTERS, FPS, HEIGHT, WIDTH, Chapter, arguments, prepare


def build(
    family: str = "Berkeley Mono",
    fonts: tuple[Path, ...] = (),
    chapters: tuple[Chapter, ...] = CHAPTERS,
) -> fframes.SvgVideo:
    """Retain the source's five-minute recording and all chapter entries."""
    data = prepare(family, fonts, chapters)
    panels = []
    for side, x, source_x, height in zip(
        ("left", "right"),
        (40, 720),
        (-600, 8),
        data.heights,
        strict=True,
    ):
        panels.append(
            f'<defs><clipPath id="{side}"><rect x="{x}" y="40" width="640" height="1000"/>'
            "</clipPath></defs>"
            f'<rect x="{x}" y="40" width="640" height="1000" fill="none" '
            'stroke="black" stroke-width="10"/>'
            f'<g clip-path="url(#{side})"><image href="image:{side}" x="{source_x}" width="1920" '
            f'height="{height}"/><image href="video:{side}" x="{source_x}" '
            f'width="1920" height="{height}"/></g>'
        )
    background = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}">'
        '<rect width="1920" height="1080" fill="#1a191b"/>'
        + "".join(panels)
        + '<text x="1400" y="40" dominant-baseline="text-before-edge" '
        f'font-family="{escape(family, quote=True)}" font-size="75" fill="white">2D: Rust</text>'
        + "".join(
            f'<rect x="1400" y="{145 + i * 75}" width="490" height="60" rx="5" fill="#404040"/>'
            for i in range(len(chapters))
        )
    )
    starts = tuple(c.start for c in chapters)
    frames = tuple(
        background
        + f'<rect x="1400" y="{145 + y}" width="490" height="60" rx="5" fill="#ff6900"/>'
        + "".join(
            f'<text x="1410" y="{180 + i * 75}" dominant-baseline="middle" xml:space="preserve" '
            f'font-family="Sofia Sans Semi Condensed" font-size="26" fill="{color}">'
            f"{escape(label)}</text>"
            for i, label in enumerate(data.labels)
            for color in ("black" if i == bisect_right(starts, frame / FPS) - 1 else "white",)
        )
        + "</svg>"
        for frame, y in enumerate(data.highlight)
    )
    return fframes.compile_video(
        fframes.VideoConfig(
            width=WIDTH, height=HEIGHT, fps=FPS, fonts=data.fonts, load_system_fonts=True
        ),
        frames,
        images=tuple(
            fframes.ImageBinding(name=s, source=data.assets[f"teej_{s}_still"])
            for s in ("left", "right")
        ),
        clips=tuple(
            fframes.VideoBinding(name=s, source=data.assets[f"teej_{s}"]) for s in ("left", "right")
        ),
        audio=tuple(fframes.AudioTrack(source=data.assets[f"teej_{s}"]) for s in ("left", "right")),
    )


def main() -> None:
    """Render the chaptered recording with two workers."""
    args = arguments()
    path = Path("output/native/teej_podcast.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    fframes.render(
        build(args.family, tuple(args.font)), path, options=fframes.RenderOptions(concurrency=2)
    )


if __name__ == "__main__":
    main()
