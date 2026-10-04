"""Original polygon scenes with SVG patterns and deterministic noise animation."""

from pathlib import Path

import fframes
from examples.low_poly import FPS, HEIGHT, WIDTH, Bird, arguments, prepare


def build(bird: Bird = "owl") -> fframes.SvgVideo:
    """Retain every source polygon and the owl's original soundtrack."""
    data = prepare(bird)
    art = "".join(f'<polygon points="{p.points}" fill="{p.fill}"/>' for p in data.polygons)
    opening = f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}">'
    opening += '<rect width="1920" height="1080" fill="black"/>'
    if bird == "pelican":
        opening += '<rect x="-2000" width="8000" height="3000" fill="#0d0d00"/>'
    images: tuple[fframes.ImageBinding, ...] = ()
    audio: tuple[fframes.AudioTrack, ...] = ()
    if data.heights is None:
        frames = (opening + art + "</svg>",) * (data.duration * FPS)
    else:
        images = (fframes.ImageBinding(name="noise", source=data.assets["noise"]),)
        audio = (fframes.AudioTrack(source=data.assets["owl_audio"], duration=10),)
        opening += (
            '<defs><pattern id="noise" patternUnits="userSpaceOnUse" width="230" height="177">'
            '<image href="image:noise" width="230" height="177"/></pattern>'
            '<clipPath id="title"><text x="1440" y="378" text-anchor="middle" '
            'font-size="100" font-family="Fredoka One">EAGLE OWL</text></clipPath></defs>'
        )
        art = (
            '<svg height="1080" x="-300" viewBox="0 0 2560 3840" shape-rendering="crispEdges">'
            + art
            + "</svg>"
        )
        frames = tuple(
            opening + f'<g clip-path="url(#title)"><rect x="-1920" y="-1080" '
            f'width="5760" height="3240" transform="translate({dx} {dy})" fill="url(#noise)"/></g>'
            '<text x="1440" y="280.8" text-anchor="middle" fill="#9f8866" '
            'font-size="45" font-family="Fredoka One">BUBO BUBO</text>'
            + "".join(
                f'<rect x="{1220 + i * 15}" y="{550 - float(h) / 2}" '
                f'width="8" height="{float(h)}" rx="3" fill="white"/>'
                for i, h in enumerate(heights)
            )
            + art
            + "</svg>"
            for dx, dy, heights in zip(data.noise_x, data.noise_y, data.heights, strict=True)
        )
    return fframes.compile_video(
        fframes.VideoConfig(
            width=WIDTH,
            height=HEIGHT,
            fps=FPS,
            fonts=(data.assets["fredoka"],),
            load_system_fonts=False,
        ),
        frames,
        images=images,
        audio=audio,
    )


def main() -> None:
    """Render the selected bird to output/native."""
    args = arguments()
    path = Path(f"output/native/low_poly_{args.bird}.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    fframes.render(build(args.bird), path, options=fframes.RenderOptions(concurrency=2))


if __name__ == "__main__":
    main()
