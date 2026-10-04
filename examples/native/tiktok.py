"""The goose clip authored as SVG frames with shared FFT, subtitles and media bindings."""

from html import escape
from pathlib import Path

import fframes
from examples.tiktok import FPS, GLOWS, HEIGHT, WIDTH, prepare


def build() -> fframes.SvgVideo:
    """Reuse static markup and precomputed captions while building the frame sequence."""
    data = prepare()
    definitions, glows = [], []
    for index, glow in enumerate(GLOWS):
        x, y, w, h = glow.region
        definitions.append(
            f'<filter id="blur{index}" x="{x}" y="{y}" width="{w}" height="{h}" '
            f'filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">'
            f'<feGaussianBlur stdDeviation="{glow.sigma}"/></filter>'
        )
        matrix = " ".join(map(str, glow.matrix))
        glows.append(
            f'<g opacity="{glow.opacity}" filter="url(#blur{index})">'
            f'<ellipse rx="{glow.radius[0]}" ry="{glow.radius[1]}" '
            f'transform="matrix({matrix})" fill="{glow.color}"/></g>'
        )
    background = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}">'
        + "<defs>"
        + "".join(definitions)
        + '</defs><rect width="1080" height="1920"/>'
        + "".join(glows)
    )
    captions = [""] * data.frames
    for caption in data.captions:
        content = "".join(
            f'<text x="{40 + dx}" y="{652.8 + j * 120}" font-family="JetBrains Mono" '
            f'font-size="100" fill="white">{escape(line)}</text>'
            for j, (line, dx) in enumerate(caption.lines)
        )
        captions[caption.start : caption.end] = [content] * (caption.end - caption.start)
    frames = tuple(
        background
        + "".join(
            f'<rect x="{150 + i * 50}" y="{300 - float(h) / 2}" width="30" height="{float(h)}" '
            'rx="15" fill="white"/>'
            for i, h in enumerate(row)
        )
        + captions[frame]
        + '<image href="image:goose" x="140" y="970" width="950" height="950" '
        'preserveAspectRatio="xMidYMid meet"/></svg>'
        for frame, row in enumerate(data.heights)
    )
    return fframes.compile_video(
        fframes.VideoConfig(
            width=WIDTH, height=HEIGHT, fps=FPS, fonts=(data.assets["jetbrains_mono"],)
        ),
        frames,
        images=(fframes.ImageBinding(name="goose", source=data.assets["goose"]),),
        audio=(fframes.AudioTrack(source=data.assets["thought"]),),
    )


def main() -> None:
    """Render the original portrait clip into output/native."""
    path = Path("output/native/tiktok.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    fframes.render(build(), path)


if __name__ == "__main__":
    main()
