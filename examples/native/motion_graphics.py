"""The three upstream motion studies authored directly as SVG frames."""

from html import escape
from pathlib import Path

import fframes
from examples.shared.motion_graphics import (
    FPS,
    HEIGHT,
    INSTALL,
    MOTION,
    QUOTE,
    URL,
    WIDTH,
    Scene,
    arguments,
    fonts,
    quote_lines,
    sample,
    terminal,
)


def label(
    content: str,
    x: float,
    y: float,
    family: str,
    size: int,
    *,
    spacing: int = 0,
    anchor: str = "middle",
    baseline: str = "auto",
    fill: str = "#ffffff",
    weight: int = 400,
    style: str = "normal",
    opacity: float = 1,
) -> str:
    """Escape text at the raw SVG boundary."""
    return (
        f'<text x="{x}" y="{y}" font-family="{escape(family, quote=True)}" '
        f'font-size="{size}" letter-spacing="{spacing}" text-anchor="{anchor}" '
        f'dominant-baseline="{baseline}" fill="{fill}" font-weight="{weight}" '
        f'font-style="{style}" opacity="{opacity}">{escape(content)}</text>'
    )


def motion(family: str) -> tuple[str, ...]:
    """Retain the original scale origin, line positions and accent geometry."""
    values = {name: sample(value, 4) for name, value in MOTION.items()}
    frames = []
    for i in range(4 * FPS):
        scale, y, width = values["scale"][i], values["y"][i], values["accent"][i]
        first = label(
            "I FIXED",
            960,
            y,
            family,
            340,
            spacing=20,
            weight=700,
            baseline="central",
            opacity=values["opacity"][i],
        )
        second = label(
            "CLAUDE CODE",
            960,
            values["second_y"][i],
            "Bebas Neue",
            280,
            spacing=14,
            baseline="central",
            opacity=values["second_opacity"][i],
        )
        third = label(
            "(for real)",
            960,
            values["third_y"][i],
            family,
            60,
            spacing=6,
            weight=300,
            style="italic",
            opacity=values["third_opacity"][i],
        )
        frames.append(
            f'<g opacity="{values["fade"][i]}">'
            f'<g transform="translate({960 * (1 - scale)} {y * (1 - scale)}) scale({scale})">'
            f'{first}</g>{second}<rect x="{960 - width / 2}" y="455" width="{width}" '
            f'height="3" rx="2" fill="white" opacity=".25"/>{third}</g>'
        )
    return tuple(frames)


def quote(layout: fframes.TextLayout, text: str) -> tuple[str, ...]:
    """Fit once, then reuse the same SVG text block for all frames."""
    labels = "".join(
        label(line, 960, y, "Bebas Neue", size, spacing=20)
        for line, size, y in quote_lines(layout, text)
    )
    values = {name: sample(value, 3) for name, value in QUOTE.items()}
    return tuple(
        f'<g opacity="{values["opacity"][i] * values["fade"][i]}" '
        f'transform="translate({960 * (1 - s)} {540 * (1 - s) + values["slide"][i]}) '
        f'scale({s})">{labels}</g>'
        for i, s in enumerate(values["scale"])
    )


def install(layout: fframes.TextLayout) -> tuple[str, ...]:
    """Render the terminal and cursor with shared precomputed native metrics."""
    values = {name: sample(value, 10) for name, value in INSTALL.items()}
    size, x, lines, cursor, blink = terminal(layout)
    prompt = label(
        "$ ", 250, 506, "JetBrains Mono", size, anchor="start", baseline="central", fill="#ff8c00"
    )
    dots = "".join(
        f'<circle cx="{cx}" cy="446" r="9" fill="{color}"/>'
        for cx, color in ((232, "#ff5f57"), (258, "#febc2e"), (284, "#28c840"))
    )
    frames = []
    for i in range(10 * FPS):
        scale, y, width = values["scale"][i], values["y"][i], values["accent"][i]
        title = label(
            "INSTALL FFF",
            960,
            y,
            "Bebas Neue",
            200,
            spacing=16,
            baseline="central",
            opacity=values["opacity"][i],
        )
        command = label(
            lines[i],
            x,
            506,
            "JetBrains Mono",
            size,
            anchor="start",
            baseline="central",
            fill="#e0e0ff",
        )
        url = label(
            URL,
            960,
            680 + values["url_y"][i],
            "JetBrains Mono",
            32,
            spacing=1,
            opacity=values["url_opacity"][i],
        )
        frames.append(
            f'<g opacity="{values["fade"][i]}">'
            f'<g transform="translate({960 * (1 - scale)} {y * (1 - scale)}) scale({scale})">'
            f'{title}</g><rect x="{960 - width / 2}" y="380" width="{width}" '
            'height="2" rx="1" fill="#ff8c00" opacity=".6"/>'
            f'<g opacity="{values["box_opacity"][i]}" '
            f'transform="translate(0 {values["box_y"][i]})">'
            '<rect x="200" y="420" width="1520" height="160" rx="16" '
            'fill="#1a1a2e" stroke="#553300" stroke-width="1.5"/>'
            f'{dots}{prompt}{command}<rect x="{cursor.values[i]}" y="{506 - size * 0.45}" '
            f'width="{size * 0.55}" height="{size * 0.9}" fill="#e0e0ff" '
            f'opacity="{blink.values[i]}"/></g>{url}</g>'
        )
    return tuple(frames)


def build(
    scene: Scene = "motion",
    *,
    text: str = "PERFORMANCE",
    family: str = "Helvetica Neue",
    extra_fonts: tuple[Path, ...] = (),
) -> fframes.SvgVideo:
    """Prepare all frames in Python and transfer them to the low-level engine."""
    sources = fonts(extra_fonts)
    layout = fframes.TextLayout(fonts=sources, load_system_fonts=scene == "motion")
    if scene == "motion":
        layout.width("I FIXED", fframes.Font(family=family))
        content = motion(family)
    elif scene == "quote":
        content = quote(layout, text)
    else:
        content = install(layout)
    return fframes.compile_video(
        fframes.VideoConfig(
            width=WIDTH, height=HEIGHT, fps=FPS, fonts=sources, load_system_fonts=scene == "motion"
        ),
        tuple(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}">'
            f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#000000"/>{frame}</svg>'
            for frame in content
        ),
    )


def main() -> None:
    """Render the selected study into output/native."""
    args = arguments()
    path = Path(f"output/native/motion_{args.scene}.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    fframes.render(
        build(args.scene, text=args.text, family=args.family, extra_fonts=tuple(args.font)), path
    )


if __name__ == "__main__":
    main()
