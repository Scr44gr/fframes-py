"""The full beta announcement, including reusable nested SVG videos."""

from html import escape
from pathlib import Path

import fframes
from examples.beta import BRACKETS, FPS, GITHUB, HEIGHT, MESSAGES, SCENES, TITLES, WIDTH, prepare
from examples.marketing import arguments
from examples.native import hello_world, marketing, podcast, tiktok


def build(family: str = "Chalkboard SE", fonts: tuple[Path, ...] = ()) -> fframes.SvgVideo:
    """Compile all seven scenes, their overlap and the original audio tail."""
    data = prepare(family, fonts)
    assets = data.assets
    nested = (
        hello_world.video("Hello, Beta!", fps=FPS),
        marketing.video(family, fonts),
        podcast.video(*(assets["beta_audio"],) * 3),
        tiktok.video(),
    )
    images = [
        fframes.ImageBinding(name=k, source=p)
        for k, p in assets.items()
        if k.startswith("beta_") and p.suffix == ".png"
    ]
    for index, video in enumerate(nested):
        images.extend(
            fframes.ImageBinding(name=f"nested{index}_{binding.name}", source=binding.source)
            for binding in video.images
        )
    nested_frames = tuple(
        tuple(frame.replace('href="image:', f'href="image:nested{i}_') for frame in video.frames)
        for i, video in enumerate(nested)
    )
    defs = (
        '<defs><linearGradient id="text"><stop stop-color="#4338ca"/>'
        '<stop offset="1" stop-color="#a21caf"/></linearGradient>'
        '<linearGradient id="progress"><stop stop-color="#aa83de"/>'
        '<stop offset="1" stop-color="#00d4ff"/></linearGradient>'
        '<clipPath id="iphoneUi"><rect x="780" y="150" width="380" height="820" '
        'rx="60"/></clipPath>'
        '<clipPath id="text-clip"><rect width="1920" height="135" y="115"/></clipPath>'
        '<clipPath id="preview-clip"><rect x="364.8" y="320" width="1190.4" height="669.6" '
        'rx="50"/></clipPath>'
        '<filter id="preview-shadow" width="200%" height="200%" color-interpolation-filters="sRGB">'
        '<feDropShadow stdDeviation="40" flood-opacity="0.3"/></filter></defs>'
    )

    def text(
        content: str,
        x: float,
        y: float,
        size: float,
        *,
        font: str = "DM Sans",
        weight: int = 700,
        fill: str = "#000000",
        attrs: str = "",
    ) -> str:
        return (
            f'<text x="{x}" y="{y}" font-family="{escape(font, quote=True)}" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}" {attrs}>{content}</text>'
        )

    def picture(
        name: str, x: float, y: float, w: float, h: float | None = None, attrs: str = ""
    ) -> str:
        height = f'height="{h}"' if h is not None else ""
        return f'<image href="image:beta_{name}" x="{x}" y="{y}" width="{w}" {height} {attrs}/>'

    def message(index: int) -> str:
        y, name, username, content = MESSAGES[index]
        return (
            picture(name, 800, y, 80, 80)
            + text(username, 880, y + 34, 18, font="Inter 24pt", weight=500, fill="#ffffff")
            + text(content, 880, y + 60, 15, font="Inter 24pt", weight=500, fill="#cbd5e1")
        )

    frames = []
    for index in range(data.frames):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" '
            'font-family="Inter 24pt" xml:space="preserve">'
            + defs
            + picture("background", 0, 0, WIDTH, HEIGHT)
        )
        for scene, (start, end) in enumerate(SCENES):
            if not start <= index < end:
                continue
            local = index - start
            t = local / FPS
            m = {name: values.values[local] for name, values in data.motion.items()}
            if scene == 0:
                logo = (
                    "fframes"
                    if local < 100
                    else '<tspan dy="10" font-size="190" font-weight="400" '
                    'font-family="Bubble Bobble"><tspan fill="#7450d9">ff</tspan>rames</tspan>'
                )
                svg += text("Welcome to the beta", m["welcome"], 432, 150) + text(
                    "of " + logo, m["of"], 648, 150
                )
            elif scene == 1:
                svg += picture(
                    "code",
                    0,
                    50,
                    1023,
                    attrs=(
                        f'transform="translate({m["code_x"]} 0) skewX({m["tilt"]}) '
                        f'skewY({-m["tilt"] + 0.4})" opacity="{m["code_alpha"]}"'
                    ),
                )
                svg += (
                    f'<svg x="{m["ferris_x"]}" y="250" width="500" height="500" '
                    f'viewBox="0 0 1200 800">' + data.ferris.gradients
                )
                for i, path in enumerate(data.ferris.paths):
                    a, b, c, d, e, f = path.matrix
                    if i in (8, 10):
                        e += m["eye_right" if i == 8 else "eye_left"]
                    svg += (
                        f'<path d="{path.path}" fill="{path.fill}" '
                        f'transform="matrix({a} {b} {c} {d} {e} {f})"/>'
                    )
                svg += "</svg>"
            elif scene == 2:
                gpu = local > 66
                label = (
                    '<tspan fill="#7450d9" '
                    + (
                        'font-family="Bubble Bobble" font-size="170" font-weight="400">  GPU    '
                        if gpu
                        else 'font-weight="900">native '
                    )
                    + "</tspan>     rendering"
                )
                svg += text("With the power of", m["power_x"], 324, 150) + text(
                    label, m["render_x"], 540, 150
                )
                svg += text(
                    data.counters[local],
                    211.2,
                    756,
                    45,
                    font="JetBrains Mono",
                    weight=600,
                    fill="#4b5563",
                )
                svg += (
                    f'<rect x="192" y="777.6" width="{m["progress"]}" height="30" rx="12" '
                    f'fill="url(#progress)"/>'
                )
            elif scene == 3:
                svg += (
                    '<g clip-path="url(#iphoneUi)">'
                    + picture("camera_ui", 790, 154, 370, 819)
                    + picture("qr", 830, 390, 300, 300)
                )
                svg += f'<g opacity="{m["scan_alpha"]}">' + "".join(
                    f'<path d="{path}" fill="none" stroke="#EBBD1D" stroke-width="2"/>'
                    for path in BRACKETS
                )
                svg += (
                    f'<g transform="translate(960 540) scale({m["button_scale"]}) '
                    'translate(-960 -540)"><rect x="884" y="715" width="200" height="34" '
                    'rx="16" fill="#EBBD1D"/>'
                    + text("fframes discord invite", 905, 737, 16, font="Inter 24pt", weight=500)
                    + "</g></g></g>"
                )
                svg += (
                    '<g clip-path="url(#iphoneUi)">'
                    f'<g transform="translate(0 {m["discord_y"]})">'
                    '<rect x="790" y="154" width="370" height="819" fill="#292841"/>'
                    + picture("discord_ui", 791, 152, 370, 819)
                )
                svg += text(
                    "12:04", 830, 196, 16, font="Inter 24pt", weight=500, fill="#9ca3af"
                ) + "".join(message(i) for i in range(3))
                svg += (
                    f'<g transform="translate(960 {1080 + m["message_y"]}) '
                    f'scale({m["message_scale"]}) translate(-960 -1080)" '
                    f'opacity="{m["message_alpha"]}">' + message(3) + "</g></g></g>"
                )
                svg += picture("iphone_frame", 576, 108, 800)
                svg += (
                    f'<rect x="{976 - m["island_w"] / 2}" y="170" width="{m["island_w"]}" '
                    f'height="{m["island_h"]}" ry="{m["island_h"] / 2}"/>'
                )
                if 8 < local < 372:
                    svg += text(
                        "ff", 895, 197, 23, font="Bubble Bobble", weight=400, fill="#6366f1"
                    )
                    svg += "".join(
                        f'<rect x="{1025 + (i + 1) * 4.5}" y="{190 - float(h) / 2}" width="3" '
                        f'height="{float(h)}" ry="1" fill="#6366f1"/>'
                        for i, h in enumerate(data.heights[local])
                    )
                elif local > 384:
                    svg += (
                        f'<svg x="816" y="182" width="56" height="56" '
                        f'viewBox="0 0 24 24"><path fill="white" d="{GITHUB}"/></svg>'
                    )
                    svg += text(
                        "New collaboration invite",
                        880,
                        208,
                        18,
                        font="Inter 24pt",
                        weight=500,
                        fill="#ffffff",
                    ) + text(
                        "dmtrKovalenko invites you to fframes",
                        880,
                        230,
                        14,
                        font="Inter 24pt",
                        weight=500,
                        fill="#cbd5e1",
                    )
            elif scene == 4:
                svg += picture("github_screenshot", m["github_x"], m["github_y"], WIDTH)
            elif scene == 5:
                svg += text(
                    "to help you get started",
                    m["examples_x"],
                    86.4,
                    60,
                    fill="url(#text)",
                    attrs='text-anchor="middle"',
                )
                svg += (
                    f'<g clip-path="url(#text-clip)"><g transform="translate(0 {m["title_y"]})">'
                    + "".join(
                        text(
                            escape(label),
                            m["hello_x"] if i == 0 else 960,
                            y,
                            120,
                            attrs='text-anchor="middle"',
                        )
                        for i, (label, y) in enumerate(
                            zip(TITLES, (220, 394, 594, 794), strict=True)
                        )
                    )
                    + "</g></g>"
                )
                svg += (
                    '<rect x="364.8" y="320" width="1190.4" height="669.6" rx="50" '
                    'stroke="#4338ca" stroke-width="8" filter="url(#preview-shadow)"/>'
                )
                child = 0 if t < 2.6 else 1 if t < 4.8 else 2 if t < 6.8 else 3
                frame = local if child < 2 else index
                svg += (
                    '<g clip-path="url(#preview-clip)"><g transform="'
                    + (
                        "translate(1552.8 320) rotate(90) "
                        if child == 3
                        else "translate(364.8 320) "
                    )
                    + 'scale(0.62)">'
                    + nested_frames[child][frame]
                    + "</g></g>"
                )
            else:
                svg += text(
                    '<tspan fill="#7450d9">ff</tspan>rames',
                    960,
                    540,
                    190,
                    font="Bubble Bobble",
                    weight=400,
                    attrs=f'text-anchor="middle" opacity="{m["logo_alpha"]}"',
                )
                svg += text(
                    "beta",
                    1220,
                    605,
                    80,
                    font=family,
                    weight=400,
                    fill="url(#text)",
                    attrs=(
                        f'opacity="{m["beta_alpha"]}" '
                        f'transform="rotate({m["beta_angle"]} 1300 590)"'
                    ),
                )
        frames.append(svg + "</svg>")
    return fframes.compile_video(
        fframes.VideoConfig(
            width=WIDTH, height=HEIGHT, fps=FPS, fonts=data.fonts, load_system_fonts=True
        ),
        tuple(frames),
        images=tuple(images),
        audio=(
            fframes.AudioTrack(source=assets["beta_audio"]),
            *(fframes.AudioTrack(source=assets["beta_pop"], start_at=i / FPS) for i in (95, 440)),
        ),
    )


def main() -> None:
    """Render the original announcement with an explicit font replacement if needed."""
    args = arguments()
    path = Path("output/native/beta.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    fframes.render(
        build(args.family, tuple(args.font)), path, options=fframes.RenderOptions(concurrency=2)
    )


if __name__ == "__main__":
    main()
