"""Audio-reactive cubic waves, glowing captions and a looping alpha clip in SVG."""

from html import escape
from pathlib import Path

import fframes
from examples.shared.audio_announce import FPS, HEIGHT, WIDTH, Wave, prepare

GLOW = (
    '<filter id="glow" filterUnits="userSpaceOnUse" x="-192" y="-108" '
    'width="2304" height="1296" color-interpolation-filters="sRGB">'
    '<feColorMatrix in="SourceAlpha" result="hard" '
    'values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"/>'
    '<feGaussianBlur in="hard" stdDeviation="18.3" result="blur"/>'
    '<feComposite in="blur" in2="hard" operator="out" result="outside"/>'
    '<feColorMatrix in="outside" result="tint" '
    'values="0 0 0 0 .654173 0 0 0 0 .116095 0 0 0 0 .56808 0 0 0 1 0"/>'
    '<feMerge><feMergeNode in="tint"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
)


def path(wave: Wave, frame: int) -> str:
    """Serialize precomputed spline points for the low-level SVG boundary."""
    segments = " ".join(
        f"C{float(x1):.7g} {float(y1):.7g} {float(x2):.7g} {float(y2):.7g} {i * 100} {float(y):.7g}"
        for i, (x1, y1, x2, y2, y) in enumerate(
            zip(wave.x1, wave.y1[frame], wave.x2, wave.y2[frame], wave.y[frame, 1:], strict=True), 1
        )
    )
    return (
        f'<path fill="{wave.color}" transform="translate({wave.offset} 0)" '
        f'd="M0 1080 {segments}Z"/>'
    )


def build() -> fframes.SvgVideo:
    """Prepare all analysis before handing the frame sequence to Rust."""
    data = prepare()
    captions = [""] * data.frames
    for caption in data.captions:
        markup = (
            '<g filter="url(#glow)" stroke="#ff208b" stroke-width="1">'
            + "".join(
                f'<text x="450" y="{170 + j * 144}" font-family="JetBrains Mono" '
                f'font-size="120" dominant-baseline="middle" fill="white">{escape(line)}</text>'
                for j, (line, _) in enumerate(caption.lines)
            )
            + "</g>"
        )
        captions[caption.start : caption.end] = [markup] * (caption.end - caption.start)
    background = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}">'
        + "<defs>"
        + GLOW
        + '</defs><image href="image:background" width="1920" height="1080"/>'
    )
    return fframes.compile_video(
        fframes.VideoConfig(
            width=WIDTH, height=HEIGHT, fps=FPS, fonts=(data.assets["jetbrains_mono"],)
        ),
        tuple(
            background
            + captions[i]
            + '<g filter="url(#glow)"><image href="video:avatar" x="80" y="100" width="300" '
            'height="300" preserveAspectRatio="none"/></g>'
            '<g opacity=".5" stroke="white" stroke-width="6">'
            + "".join(path(wave, i) for wave in data.waves)
            + "</g></svg>"
            for i in range(data.frames)
        ),
        images=(
            fframes.ImageBinding(name="background", source=data.assets["announce_background"]),
        ),
        clips=(
            fframes.VideoBinding(name="avatar", source=data.assets["announce_avatar"], loop=True),
        ),
        audio=(fframes.AudioTrack(source=data.assets["announce_video"]),),
    )


def main() -> None:
    """Export the complete announcement into output/native."""
    destination = Path("output/native/audio_announce.mp4")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fframes.render(build(), destination, options=fframes.RenderOptions(concurrency=2))


if __name__ == "__main__":
    main()
