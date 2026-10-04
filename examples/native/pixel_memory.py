"""Original Pixel Memory choreography as finite SVG frames and native media bindings."""

from html import escape
from math import floor
from pathlib import Path

import fframes
from examples.pixel_memory import (
    FPS,
    GOLD,
    HEIGHT,
    INTRO,
    WIDTH,
    Kind,
    Photo,
    arguments,
    curve,
    prepare,
)


def photo_frame(photo: Photo, index: int, name: str, family: str) -> str:
    """Draw one original frame treatment using the shared sampled choreography."""
    width, height = photo.size
    x, y = photo.position
    ox, oy = photo.origin
    transform = (
        f"translate({photo.x[index]} {photo.y[index]}) translate({ox} {oy}) "
        f"rotate({photo.rotation[index]}) scale({photo.scale[index]}) translate({-ox} {-oy})"
    )
    shadow = (
        ' filter="url(#polaroid-shadow)"'
        if photo.development is not None
        else ' filter="url(#photo-shadow)"'
        if photo.shadow
        else ""
    )
    svg = f'<g transform="{transform}" opacity="{photo.opacity[index]}"{shadow}>'
    if photo.development is not None:
        svg += (
            f'<rect width="{width + 28}" height="{height + 74}" rx="2" fill="white" '
            'stroke="#e9e9e9" stroke-width="1"/>'
            f'<rect x="14" y="14" width="{width}" height="{height}" fill="#f0f0f0"/>'
        )
    elif photo.stroke:
        svg += (
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="none" '
            f'stroke="white" stroke-width="{photo.stroke}"/>'
        )
    fit = "slice" if photo.development is not None else "meet"
    svg += (
        f'<image href="image:{name}" x="{x}" y="{y}" width="{width}" height="{height}" '
        f'preserveAspectRatio="xMidYMid {fit}"/>'
    )
    if photo.development is not None:
        progress = photo.development[index]
        svg += (
            f'<rect x="14" y="14" width="{width}" height="{height}" fill="white" '
            f'opacity="{1 - progress}"/><text x="{(width + 28) / 2}" y="{height + 49}" '
            f'font-family="{escape(family, quote=True)}" font-size="44" fill="#333333" '
            f'text-anchor="middle" dominant-baseline="middle" opacity="{progress}">'
            f"{escape(photo.year)}</text>"
        )
    return svg + "</g>"


def build(
    seed: int = 48,
    song: str = "revenge",
    study: Kind | None = None,
    text: str = INTRO,
    family: str = "Indie Flower",
    fonts: tuple[Path, ...] = (),
) -> fframes.SvgVideo:
    """Compile all source gallery algorithms, audio and synchronized video scenes."""
    data = prepare(seed, song, study, text, family, fonts)
    frames = floor(data.duration * FPS)
    defs = (
        '<defs><linearGradient id="background" x2="1" y2="1"><stop stop-color="black"/>'
        '<stop offset="1" stop-color="#050505"/></linearGradient>'
    )
    for index, colors in enumerate(GOLD):
        defs += (
            f'<radialGradient id="bokeh-{index}" fx="0.4" fy="0.4">'
            + "".join(
                f'<stop offset="{offset}" stop-color="{color}"/>'
                for offset, color in zip((0, 0.7, 1), colors, strict=True)
            )
            + "</radialGradient>"
        )
    for sigma in (2, 5, 8):
        defs += (
            f'<filter id="blur-{sigma}" x="-50%" y="-50%" width="200%" height="200%">'
            f'<feGaussianBlur stdDeviation="{sigma}"/></filter>'
        )
    for name, sigma, offset in (("photo", 8, 3), ("polaroid", 10, 5)):
        defs += (
            f'<filter id="{name}-shadow" x="-20%" y="-20%" width="140%" height="140%">'
            f'<feGaussianBlur in="SourceAlpha" stdDeviation="{sigma}"/>'
            f'<feOffset dx="{offset}" dy="{offset}"/><feComponentTransfer>'
            '<feFuncA type="linear" slope="0.3"/></feComponentTransfer><feMerge>'
            '<feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        )
    defs += '<filter id="video-blur"><feGaussianBlur stdDeviation="30"/></filter></defs>'
    images: dict[Path, str] = {}
    clips, audio = [], []
    contents = [""] * frames
    if data.intro_duration:
        opacity = curve(
            data.intro_duration, (data.intro_duration - 3, data.intro_duration, 1, 0, "ease_out")
        )
        text_svg = "".join(
            f'<text x="960" y="{324 + i * 124 * 1.1}" font-size="124" '
            'font-family="Space Grotesk" fill="white" text-anchor="middle" '
            f'dominant-baseline="middle">{escape(line)}</text>'
            for i, line in enumerate(data.lines)
        )
        for i in range(floor(data.intro_duration * FPS)):
            contents[i] += f'<g opacity="{opacity[i]}">{text_svg}</g>'
    for scene_index, (start, shot) in enumerate(data.scenes):
        for photo in shot.photos:
            if photo.source not in images:
                images[photo.source] = f"photo{len(images)}"
        end = min(frames, start + floor(shot.duration * FPS))
        if shot.video is None:
            for i in range(start, end):
                contents[i] += "".join(
                    photo_frame(photo, i - start, images[photo.source], family)
                    for photo in shot.photos
                )
            continue
        name = f"clip{scene_index}"
        clips.append(
            fframes.VideoBinding(
                name=name, source=shot.video, start_at=start / FPS, duration=shot.duration
            )
        )
        audio.append(
            fframes.AudioTrack(source=shot.video, start_at=start / FPS, duration=shot.duration)
        )
        width, height = shot.video_size
        scaled = width / height * HEIGHT
        opacity = curve(
            shot.duration,
            (0, 0.5, 0, 1, "ease_in"),
            (shot.duration - 0.5, shot.duration, 1, 0, "ease_out"),
        )
        for i in range(start, end):
            alpha = opacity[i - start]
            if height > width:
                contents[i] += (
                    f'<image href="video:{name}" width="1920" height="1080" '
                    f'preserveAspectRatio="xMidYMid slice" opacity="{alpha * 0.7}" '
                    'filter="url(#video-blur)"/>'
                )
            contents[i] += (
                f'<image href="video:{name}" width="{scaled}" height="1080" '
                f'x="{(WIDTH - scaled) / 2}" opacity="{alpha}"/>'
            )
    if data.final_start < frames:
        dash_offset = curve(
            data.duration - data.final_start / FPS, (0, data.final_duration, 3000, 0, "linear")
        )
        for i in range(data.final_start, frames):
            contents[i] += (
                '<svg x="517" y="0" width="886" viewBox="-20 0 483 115">'
                f'<path d="{data.final_path}" fill="none" stroke="white" stroke-width="9" '
                'stroke-linecap="round" stroke-dasharray="900 900" '
                f'stroke-dashoffset="{dash_offset[i - data.final_start]}"/></svg>'
            )
    if study is None:
        audio.append(
            fframes.AudioTrack(source=data.assets[f"pixel_{song.lower()}_mp3"], start_at=6)
        )
    documents = tuple(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
        + defs
        + '<rect width="1920" height="1080" fill="url(#background)"/>'
        + "".join(
            f'<circle cx="{c.x[i]}" cy="{c.y[i]}" r="{c.radius}" '
            f'opacity="{c.opacity}" fill="url(#bokeh-{c.palette})" '
            f'filter="url(#blur-{int(c.blur)})"/>'
            for c in data.bokeh
        )
        + contents[i]
        + "</svg>"
        for i in range(frames)
    )
    return fframes.compile_video(
        fframes.VideoConfig(
            width=WIDTH, height=HEIGHT, fps=FPS, fonts=data.fonts, load_system_fonts=True
        ),
        documents,
        images=tuple(fframes.ImageBinding(name=name, source=path) for path, name in images.items()),
        clips=tuple(clips),
        audio=tuple(audio),
    )


def main() -> None:
    """Render the selected gallery into output/native."""
    args = arguments()
    path = Path(f"output/native/pixel_memory{('_' + args.scene) if args.scene else ''}.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    fframes.render(
        build(args.seed, args.song, args.scene, args.text, args.family, tuple(args.font)),
        path,
        options=fframes.RenderOptions(concurrency=2),
    )


if __name__ == "__main__":
    main()
