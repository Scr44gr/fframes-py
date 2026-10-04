"""Original marketing clip authored as SVG with shared native audio analysis."""

from html import escape
from pathlib import Path

import fframes
from examples.shared.marketing import (
    ARROW,
    BOUNCES,
    FPS,
    HEIGHT,
    PALETTE,
    SPARKS,
    WIDTH,
    arguments,
    prepare,
)


def build(family: str = "Chalkboard SE", fonts: tuple[Path, ...] = ()) -> fframes.SvgVideo:
    """Retain the complete spectrum, Ferris animation, captions and logo outro."""
    return video(family, fonts).native


def video(family: str = "Chalkboard SE", fonts: tuple[Path, ...] = ()) -> fframes.Video:
    """Keep frames and bindings reusable in the beta demonstration."""
    data = prepare(family, fonts)
    definitions = (
        "<defs>"
        + "".join(
            f'<linearGradient id="bar-{position}" y2="1"><stop stop-color="{first}"/>'
            f'<stop offset="1" stop-color="{last}"/></linearGradient>'
            f'<filter id="shadow-{position}" x="-100%" y="-100%" width="300%" height="300%">'
            '<feGaussianBlur in="SourceAlpha" stdDeviation="10.4"/>'
            '<feOffset dx="0" dy="3" result="offsetblur"/>'
            f'<feFlood flood-color="{last}" flood-opacity="0.5"/>'
            '<feComposite in2="offsetblur" operator="in"/><feMerge><feMergeNode/>'
            '<feMergeNode in="SourceGraphic"/></feMerge></filter>'
            for position, _index, first, last in PALETTE
        )
        + (
            '<linearGradient id="anim"><stop stop-color="#ec77ab"/>'
            '<stop offset="1" stop-color="#4f46e5"/></linearGradient></defs>'
        )
    )
    frames = []
    for frame in range(data.frames):
        t = frame / FPS
        motion = {name: value.values[frame] for name, value in data.motion.items()}
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" '
            'xml:space="preserve">'
            + definitions
            + '<rect width="1920" height="1080" fill="#111827"/>'
        )
        for position, index, _first, _last in PALETTE:
            h = float(data.heights[frame, index])
            x = motion[f"bar_{position}"]
            svg += (
                f'<rect x="{x}" y="{500 - h / 2}" width="104" height="{h + 8}" '
                'rx="48" fill="none" stroke="white" stroke-width="4"/>'
                f'<rect x="{x}" y="{500 - h / 2}" width="96" height="{h}" rx="48" '
                f'fill="url(#bar-{position})" filter="url(#shadow-{position})"/>'
            )
        svg += (
            f'<svg x="200" y="290" width="298" viewBox="0 0 598.3520004127504 417.989493060112" '
            f'opacity="{motion["arrow"]}">'
            '<g transform="translate(12.76795062351539 11.630295608565234)">'
            f'<path d="{ARROW[0]}" stroke="white" stroke-width="4.5" fill="none" '
            f'stroke-linecap="round" stroke-dasharray="8 12"/><path d="{ARROW[1]}" '
            f'stroke="white" stroke-width="4.5" fill="none"/><path d="{ARROW[2]}" '
            'stroke="white" stroke-width="4.5" fill="none"/></g></svg>'
            '<text x="960" y="939.6" font-size="64" text-anchor="middle" fill="white" '
            f'font-family="{escape(family, quote=True)}">{escape(data.captions[frame])}</text>'
            f'<image href="image:code" width="900" height="900" x="{motion["code"]}" y="10"/>'
        )
        if 2.3 <= t < 5:
            svg += (
                f'<svg x="1456" y="{motion["ferris"]}" width="400" height="400" '
                'viewBox="0 0 1200 800">' + data.gradients
            )
            for index, path in enumerate(data.paths):
                a, b, c, d, e, f = path.matrix
                if index in (8, 10):
                    e += motion["eye"]
                svg += (
                    f'<path d="{path.path}" fill="{path.fill}" '
                    f'transform="matrix({a} {b} {c} {d} {e} {f})"/>'
                )
            svg += "</svg>"
        svg += f'<circle cx="960" cy="500" r="{motion["wipe"]}" fill="white"/>'
        if t > 16.25:
            color = "#7351d8" if t > 18.8 else "#000000"
            svg += (
                '<text x="960" y="570" font-family="Bubble Bobble" '
                'font-size="154" text-anchor="middle">'
                f'<tspan fill="{color}">ff</tspan>rames</text><text x="960" y="610" '
                f'font-family="{escape(family, quote=True)}" font-size="30" text-anchor="middle">'
                "Write some code. Get video. Enjoy!</text>"
                '<g transform="scale(2.7) translate(-218,110)">'
                f'<path d="{BOUNCES}" fill="none" stroke="url(#anim)" stroke-width="10" '
                'stroke-linecap="round" stroke-linejoin="round" stroke-miterlimit="10" '
                f'stroke-dasharray="40.4579 796.447" stroke-dashoffset="{motion["bounce"]}"/>'
                f'<path d="{SPARKS}" fill="none" stroke="#4f46e5" stroke-width="6" '
                'stroke-linecap="round" stroke-linejoin="round" '
                f'opacity="{motion["spark_opacity"]}" stroke-dashoffset="{motion["spark_offset"]}" '
                f'stroke-dasharray="{motion["spark_length"]} 137"/></g>'
            )
        frames.append(svg + "</svg>")
    return fframes.Video(
        config=fframes.VideoConfig(
            width=WIDTH, height=HEIGHT, fps=FPS, fonts=data.fonts, load_system_fonts=True
        ),
        frames=tuple(frames),
        images=(fframes.ImageBinding(name="code", source=data.assets["marketing_code"]),),
        audio=tuple(
            fframes.AudioTrack(source=data.assets[name], start_at=start)
            for name, start in (
                ("marketing_audio", 0),
                ("marketing_woosh", 6),
                ("marketing_end", 16),
            )
        ),
    )


def main() -> None:
    """Render the full marketing clip to output/native."""
    args = arguments()
    path = Path("output/native/marketing.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    fframes.render(
        build(args.family, tuple(args.font)), path, options=fframes.RenderOptions(concurrency=2)
    )


if __name__ == "__main__":
    main()
