"""Conference sponsor intro and speaker card with the original SVG typography."""

from html import escape
from pathlib import Path

import fframes
from examples.shared.conference import CORNERS, CUT, FPS, HEIGHT, WIDTH, arguments, prepare, samples


def build(talk: str = "0") -> fframes.SvgVideo:
    """Render one selected session with its pinned photo and conference soundtrack."""
    data = prepare(talk)
    motion = samples(data.frames)
    frames = []
    for frame in range(data.frames):
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
            'xml:space="preserve">'
        )
        if frame < CUT:
            values = {name: series[frame] for name, series in motion.items()}
            svg += (
                '<image href="image:conference_gradient" width="1920" height="1080"/>'
                f'<text x="1344" y="{values["location_y"]}" font-size="70" fill="white" '
                f'opacity="{values["location_opacity"]}"><tspan font-weight="600" '
                'font-family="Montserrat">Warsaw </tspan>'
                '<tspan font-family="JetBrains Mono">2025</tspan></text>'
                f'<text x="{values["title_x"]}" y="{values["title_y"]}" text-anchor="middle" '
                'dominant-baseline="middle" font-family="Montserrat" font-size="200" fill="white">'
                'FUN <tspan fill="#c24f1e">OCaml</tspan></text>'
                f'<svg y="250" width="1140" height="828"><path d="{data.camel}" '
                f'fill="#562f1f" opacity="{values["camel_opacity"]}"/></svg>'
                '<text x="960" y="620" font-size="60" font-family="Inter 18pt" '
                'font-weight="600" fill="#d43f00" dominant-baseline="middle" '
                f'opacity="{values["sponsors_opacity"]}">'
                "Sponsors and Partners</text>"
                f'<image x="720" y="{values["sponsors_y"]}" width="1150" href="image:sponsors"/>'
            )
        else:
            local = frame - CUT
            svg += '<image href="image:conference_background" width="1920"/>'
            for lines, size, y, family, weight in (
                (data.title, data.title_size, 350, "Inter 18pt", 800),
                (data.abstract, data.abstract_size, data.abstract_y, "Inter 24pt", 400),
            ):
                svg += "".join(
                    f'<text x="90" y="{y + int(i * size * 1.2)}" font-size="{size}" '
                    f'font-family="{family}" font-weight="{weight}" fill="white">'
                    f"{escape(line)}</text>"
                    for i, line in enumerate(lines)
                )
            svg += "".join(
                f'<path transform="translate({x} {y})" d="{path}" fill="none" '
                f'stroke="#fffbfb" stroke-width="3" stroke-dasharray="300" '
                f'stroke-dashoffset="{motion["dash"][local]}"/>'
                for path, x, y in zip(CORNERS, (1000, 40), (250, data.corner_y), strict=True)
            )
            svg += (
                '<defs><clipPath id="photo"><circle cx="1540" cy="470" r="220"/></clipPath>'
                '<filter id="shadow"><feDropShadow dx="3" dy="3" stdDeviation="8" '
                'flood-color="black" flood-opacity="0.5"/></filter></defs>'
                f'<g transform="matrix(1 {data.skew_y.values[local]} '
                f'{data.skew_x.values[local]} 1 0 0)">'
                '<rect x="1200" y="162" width="661" height="770" rx="60" '
                'fill="#525764" filter="url(#shadow)"/>'
                '<image x="1320" y="250" width="440" height="440" '
                'href="image:portrait" clip-path="url(#photo)"/>'
                f'<rect x="{1534 - data.speaker_width // 2}" y="773" width="{data.speaker_width}" '
                'height="90" rx="20" fill="white"/>'
                '<text x="1534" y="820" font-family="Inter 24pt" font-weight="700" font-size="54" '
                'text-anchor="middle" dominant-baseline="middle" fill="#d54000">'
                f"{escape(data.talk.speaker_name)}</text></g>"
            )
        frames.append(svg + "</svg>")
    return fframes.compile_video(
        fframes.VideoConfig(width=WIDTH, height=HEIGHT, fps=FPS, fonts=data.fonts),
        tuple(frames),
        images=(
            *(
                fframes.ImageBinding(name=name, source=data.assets[name])
                for name in ("conference_gradient", "conference_background", "sponsors")
            ),
            fframes.ImageBinding(
                name="portrait", source=data.assets[data.talk.avatar or "speaker_placeholder"]
            ),
        ),
        audio=(fframes.AudioTrack(source=data.assets["conference_audio"]),),
    )


def main() -> None:
    """Render one conference splash screen into output/native."""
    args = arguments()
    path = Path("output/native/conference.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    fframes.render(build(args.talk), path, options=fframes.RenderOptions(concurrency=2))


if __name__ == "__main__":
    main()
