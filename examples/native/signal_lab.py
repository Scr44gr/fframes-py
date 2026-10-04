"""Signal Lab authored as SVG with shared native animation and audio bindings."""

from pathlib import Path

import fframes
from examples.assets import files
from examples.native.motion_graphics import label as svg_text
from examples.shared.signal_lab import (
    CARDS,
    DURATION,
    FPS,
    GRAY,
    GREEN,
    HEIGHT,
    INK,
    LIME,
    MUTED,
    PAPER,
    PROGRESS,
    TITLES,
    TRAVEL,
    WIDTH,
    bars,
    heading,
    ramp,
    rise,
    sample,
)


def text(
    content: str,
    x: float,
    y: float,
    size: int,
    color: str = INK,
    *,
    anchor: str = "start",
    spacing: int = 0,
) -> str:
    """Apply the common typography at the SVG boundary."""
    return svg_text(
        content, x, y, "DM Sans", size, fill=color, weight=500, anchor=anchor, spacing=spacing
    )


def rect(x: float, y: float, width: float, height: float, color: str, radius: int = 0) -> str:
    """Write a rectangle in canvas coordinates."""
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{color}"/>'


def circle(x: float, y: float, radius: int, color: str) -> str:
    """Write a circle using its center rather than its bounds."""
    return f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{color}"/>'


def line(path: str, color: str, width: int) -> str:
    """Write an unfilled stroked path."""
    return f'<path d="{path}" stroke="{color}" stroke-width="{width}" fill="none"/>'


def label(index: int) -> str:
    """Identify one of the four studies."""
    return (
        circle(209, 147, 17, GREEN)
        + text(TITLES[index], 252, 158, 30)
        + text(f"0{index + 1} / 04", 1728, 158, 30, anchor="end")
    )


def group(body: str, index: int, start: float, *, move: bool = True) -> str:
    """Apply sampled entrance opacity and optional spring displacement."""
    y = sample(rise(start))[index] if move else 0
    return f'<g opacity="{sample(ramp(start))[index]}" transform="translate(0 {y})">{body}</g>'


def product(index: int) -> str:
    """Preserve the release checklist's nested transforms."""
    rows = "".join(
        group(
            rect(1088, 424 + i * 105, 540, 82, "#29403d", 14)
            + text(name, 1124, 478 + i * 105, 38, PAPER)
            + text("Ready", 1586, 478 + i * 105, 30, LIME, anchor="end"),
            index,
            0.7 + i * 0.12,
        )
        for i, name in enumerate(("Build", "Review", "Publish"))
    )
    star = (
        f'<g transform="translate(1650 278) rotate({index / FPS * 8})">'
        + circle(0, 0, 73, LIME)
        + line("M-34 0H34M0-34V34M-24-24L24 24M-24 24L24-24", INK, 7)
        + "</g>"
    )
    return (
        label(0)
        + text("Signal.", 183, 445, 208, spacing=-10)
        + text("Your next release,", 192, 543, 52)
        + text("in motion.", 192, 610, 52)
        + group(
            rect(192, 703, 380, 76, INK, 38)
            + text("A FICTIONAL PRODUCT", 382, 753, 32, LIME, anchor="middle"),
            index,
            0.4,
            move=False,
        )
        + f'<g transform="translate(0 {sample(rise(0))[index]})">'
        + rect(1000, 262, 728, 576, INK, 32)
        + circle(1095, 352, 14, LIME)
        + text("Release / 01", 1138, 365, 38, PAPER)
        + rows
        + star
        + "</g>"
    )


def data(index: int, title: str) -> str:
    """Drive bar geometry and readouts with the same sampled measurements."""
    columns = []
    for i in range(4):
        heights, positions, labels = bars(i)
        x, h, y = 982 + i * 188, heights.values[index], positions.values[index]
        columns.append(
            rect(x, y, 126, h, GREEN if i == 3 else GRAY, 8)
            + text(labels[index], x + 63, y - 23, 36, anchor="middle")
            + text(f"0{i + 1}", x + 63, 851, 30, MUTED, anchor="middle")
        )
    return (
        label(1)
        + text(title, 192, 314, 108, spacing=-4)
        + text(f"{76 * sample(ramp(0.55))[index]:.0f}", 180, 646, 248, spacing=-12)
        + text("Weekly activations", 192, 734, 46)
        + text("ILLUSTRATIVE DATA / WEEKS 01\u201304", 192, 802, 30, MUTED)
        + "".join(columns)
    )


def system(index: int, title: str) -> str:
    """Draw the connected cards and moving revision marker."""
    cards = "".join(
        group(
            rect(192 + i * 548, 440, 440, 302, INK, 24)
            + text(number, 228 + i * 548, 505, 30, LIME)
            + text(name, 228 + i * 548, 612, 64, PAPER)
            + text(subtitle, 228 + i * 548, 684, 32, GRAY),
            index,
            0.12 + i * 0.1,
        )
        for i, (number, name, subtitle) in enumerate(CARDS)
    )
    return (
        label(2)
        + text(title, 192, 314, 108, spacing=-4)
        + group(
            line("M632 591H740M1180 591H1288", GREEN, 5)
            + line("M718 577L740 591L718 605M1266 577L1288 591L1266 605", GREEN, 5),
            index,
            0.4,
            move=False,
        )
        + cards
        + group(
            line("M412 780V824H1508V780", GRAY, 3)
            + circle(sample(TRAVEL)[index], 824, 12, GREEN)
            + text("REVISE AND REPEAT", 960, 894, 30, MUTED, anchor="middle"),
            index,
            0.65,
            move=False,
        )
    )


def closing(index: int) -> str:
    """Spring the closing title above its use-case banner."""
    return (
        label(3)
        + f'<g transform="translate(0 {sample(rise(0.2))[index]})">'
        + text("Built from code.", 183, 457, 146, spacing=-6)
        + text("Ready to revise.", 183, 631, 146, spacing=-6)
        + "</g>"
        + group(
            rect(192, 750, 1536, 90, INK, 16)
            + text("PRODUCT DEMOS", 240, 809, 34, PAPER)
            + text("DATA STORIES", 716, 809, 34, PAPER)
            + text("VISUAL EXPLAINERS", 1152, 809, 34, PAPER)
            + circle(664, 797, 7, LIME)
            + circle(1100, 797, 7, LIME),
            index,
            0.2,
            move=False,
        )
    )


def build() -> fframes.SvgVideo:
    """Compile the SVG frames with the continuous shared soundtrack."""
    assets = files("signal_lab")
    fonts = (assets["dm_sans"],)
    layout = fframes.TextLayout(fonts=fonts)
    data_title = heading(layout, "Give numbers a rhythm.")
    system_title = heading(layout, "Make the process visible.")
    footer = (
        line("M192 946H1728", GRAY, 2)
        + text("FFRAMES / MOTION STUDIES", 192, 1002, 28, MUTED)
        + text("24 SECONDS / SVG + RUST", 1728, 1002, 28, MUTED, anchor="end")
    )
    frames = []
    for frame in range(DURATION * FPS):
        scene, index = divmod(frame, 6 * FPS)
        if scene == 0:
            content = product(index)
        elif scene == 1:
            content = data(index, data_title)
        elif scene == 2:
            content = system(index, system_title)
        else:
            content = closing(index)
        frames.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}">'
            + rect(0, 0, WIDTH, HEIGHT, PAPER)
            + content
            + footer
            + rect(192, 945, PROGRESS.values[frame], 3, GREEN)
            + "</svg>"
        )
    return fframes.compile_video(
        fframes.VideoConfig(
            width=WIDTH, height=HEIGHT, fps=FPS, fonts=fonts, load_system_fonts=False
        ),
        tuple(frames),
        audio=(
            fframes.AudioTrack(source=assets["pulse"], gain_db=6.5, fade_in=0.08, fade_out=0.6),
        ),
    )


def main() -> None:
    """Render the complete study into output/native."""
    path = Path("output/native/signal_lab.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    fframes.render(build(), path)


if __name__ == "__main__":
    main()
