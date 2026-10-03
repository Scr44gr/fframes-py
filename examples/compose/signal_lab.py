"""Four reusable motion studies: product, data, process and closing title."""

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from examples.assets import files
from examples.signal_lab import (
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
from fframes import Samples, TextLayout, Tween
from fframes.compose import (
    Audio,
    Circle,
    Composition,
    LineTo,
    MoveTo,
    Position,
    Rectangle,
    Stroke,
    Text,
    TextFrames,
    VectorPath,
    Video,
)
from fframes.values import Scalar

if TYPE_CHECKING:
    from fframes.compose.components import Item


def text(
    content: str | TextFrames,
    x: Scalar,
    y: Scalar,
    size: int,
    color: str = INK,
    *,
    anchor: Literal["start", "middle", "end"] = "start",
    spacing: int = 0,
) -> Text:
    """Reuse the study's baseline and typography without implicit layout."""
    return Text(
        content=content,
        position=Position(x=x, y=y),
        font_family="DM Sans",
        font_size=size,
        font_weight=500,
        fill=color,
        anchor="baseline",
        text_anchor=anchor,
        letter_spacing=spacing,
    )


def line(points: tuple[tuple[float, float], ...], color: str, width: int) -> VectorPath:
    """Construct a connected open path in canvas coordinates."""
    return VectorPath(
        size=(WIDTH, HEIGHT),
        fill=None,
        stroke=Stroke(color=color, width=width),
        segments=(
            MoveTo(x=points[0][0], y=points[0][1]),
            *(LineTo(x=x, y=y) for x, y in points[1:]),
        ),
    )


def label(index: int) -> Composition:
    """Identify a study in the shared header."""
    return Composition(
        children=(
            Circle(radius=17, fill=GREEN, position=Position(x=192, y=130)),
            text(TITLES[index], 252, 158, 30),
            text(f"0{index + 1} / 04", 1728, 158, 30, anchor="end"),
        )
    )


def product() -> Composition:
    """Introduce Signal and spring the release checklist into place."""
    rows: tuple[Item, ...] = tuple(
        Composition(
            opacity=ramp(0.7 + i * 0.12),
            position=Position(y=rise(0.7 + i * 0.12)),
            children=(
                Rectangle(
                    size=(540, 82),
                    radius=14,
                    fill="#29403d",
                    position=Position(x=1088, y=424 + i * 105),
                ),
                text(name, 1124, 478 + i * 105, 38, PAPER),
                text("Ready", 1586, 478 + i * 105, 30, LIME, anchor="end"),
            ),
        )
        for i, name in enumerate(("Build", "Review", "Publish"))
    )
    return Composition(
        children=(
            label(0),
            text("Signal.", 183, 445, 208, spacing=-10),
            text("Your next release,", 192, 543, 52),
            text("in motion.", 192, 610, 52),
            Composition(
                opacity=ramp(0.4),
                children=(
                    Rectangle(size=(380, 76), radius=38, fill=INK, position=Position(x=192, y=703)),
                    text("A FICTIONAL PRODUCT", 382, 753, 32, LIME, anchor="middle"),
                ),
            ),
            Composition(
                position=Position(y=rise(0)),
                children=(
                    Rectangle(
                        size=(728, 576), radius=32, fill=INK, position=Position(x=1000, y=262)
                    ),
                    Circle(radius=14, fill=LIME, position=Position(x=1081, y=338)),
                    text("Release / 01", 1138, 365, 38, PAPER),
                    *rows,
                    Composition(
                        position=Position(x=1650, y=278),
                        origin=(0, 0),
                        rotation=Tween(from_value=0, to_value=48, duration=6),
                        children=(
                            Circle(radius=73, fill=LIME, position=Position(x=-73, y=-73)),
                            *(
                                line(points, INK, 7)
                                for points in (
                                    ((-34, 0), (34, 0)),
                                    ((0, -34), (0, 34)),
                                    ((-24, -24), (24, 24)),
                                    ((-24, 24), (24, -24)),
                                )
                            ),
                        ),
                    ),
                ),
            ),
        )
    )


def data(layout: TextLayout) -> Composition:
    """Animate four measurements and their labels from the same sampled easing."""
    columns: list[Item] = []
    for i in range(4):
        heights, positions, labels = bars(i)
        x = 982 + i * 188
        columns.extend(
            (
                Rectangle(
                    size=(126, heights),
                    radius=8,
                    fill=GREEN if i == 3 else GRAY,
                    position=Position(x=x, y=positions),
                ),
                text(
                    TextFrames(frames=labels),
                    x + 63,
                    Samples(values=tuple(y - 23 for y in positions.values), fps=FPS),
                    36,
                    anchor="middle",
                ),
                text(f"0{i + 1}", x + 63, 851, 30, MUTED, anchor="middle"),
            )
        )
    return Composition(
        children=(
            label(1),
            text(heading(layout, "Give numbers a rhythm."), 192, 314, 108, spacing=-4),
            text(
                TextFrames(frames=tuple(f"{76 * p:.0f}" for p in sample(ramp(0.55)))),
                180,
                646,
                248,
                spacing=-12,
            ),
            text("Weekly activations", 192, 734, 46),
            text("ILLUSTRATIVE DATA / WEEKS 01\u201304", 192, 802, 30, MUTED),
            *columns,
        )
    )


def system(layout: TextLayout) -> Composition:
    """Connect the three cards and trace their revision loop."""
    return Composition(
        children=(
            label(2),
            text(heading(layout, "Make the process visible."), 192, 314, 108, spacing=-4),
            Composition(
                opacity=ramp(0.4),
                children=tuple(
                    line(points, GREEN, 5)
                    for points in (
                        ((632, 591), (740, 591)),
                        ((1180, 591), (1288, 591)),
                        ((718, 577), (740, 591), (718, 605)),
                        ((1266, 577), (1288, 591), (1266, 605)),
                    )
                ),
            ),
            *(
                Composition(
                    opacity=ramp(0.12 + i * 0.1),
                    position=Position(y=rise(0.12 + i * 0.1)),
                    children=(
                        Rectangle(
                            size=(440, 302),
                            radius=24,
                            fill=INK,
                            position=Position(x=192 + i * 548, y=440),
                        ),
                        text(number, 228 + i * 548, 505, 30, LIME),
                        text(title, 228 + i * 548, 612, 64, PAPER),
                        text(subtitle, 228 + i * 548, 684, 32, GRAY),
                    ),
                )
                for i, (number, title, subtitle) in enumerate(CARDS)
            ),
            Composition(
                opacity=ramp(0.65),
                children=(
                    line(((412, 780), (412, 824), (1508, 824), (1508, 780)), GRAY, 3),
                    Circle(
                        radius=12,
                        fill=GREEN,
                        position=Position(
                            x=Samples(values=tuple(x - 12 for x in sample(TRAVEL)), fps=FPS), y=812
                        ),
                    ),
                    text("REVISE AND REPEAT", 960, 894, 30, MUTED, anchor="middle"),
                ),
            ),
        )
    )


def closing() -> Composition:
    """Close the study with the original spring and use-case banner."""
    return Composition(
        children=(
            label(3),
            Composition(
                position=Position(y=rise(0.2)),
                children=(
                    text("Built from code.", 183, 457, 146, spacing=-6),
                    text("Ready to revise.", 183, 631, 146, spacing=-6),
                ),
            ),
            Composition(
                opacity=ramp(0.2),
                children=(
                    Rectangle(
                        size=(1536, 90), radius=16, fill=INK, position=Position(x=192, y=750)
                    ),
                    text("PRODUCT DEMOS", 240, 809, 34, PAPER),
                    text("DATA STORIES", 716, 809, 34, PAPER),
                    text("VISUAL EXPLAINERS", 1152, 809, 34, PAPER),
                    *(
                        Circle(radius=7, fill=LIME, position=Position(x=x - 7, y=790))
                        for x in (664, 1100)
                    ),
                ),
            ),
        )
    )


def build() -> Video:
    """Compose four local clocks with one uninterrupted progress bar and soundtrack."""
    assets = files("signal_lab")
    fonts = (assets["dm_sans"],)
    layout = TextLayout(fonts=fonts)
    return Video(
        resolution=(WIDTH, HEIGHT),
        fps=FPS,
        fonts=fonts,
        load_system_fonts=False,
        composition=Composition(
            duration=DURATION,
            children=(
                Rectangle(size=(WIDTH, HEIGHT), fill=PAPER),
                *(
                    scene.at(i * 6, duration=6)
                    for i, scene in enumerate((product(), data(layout), system(layout), closing()))
                ),
                line(((192, 946), (1728, 946)), GRAY, 2),
                Rectangle(size=(PROGRESS, 3), fill=GREEN, position=Position(x=192, y=945)),
                text("FFRAMES / MOTION STUDIES", 192, 1002, 28, MUTED),
                text("24 SECONDS / SVG + RUST", 1728, 1002, 28, MUTED, anchor="end"),
                Audio(source=assets["pulse"], gain_db=6.5, fade_in=0.08, fade_out=0.6),
            ),
        ),
    )


def main() -> None:
    """Render the complete study into output/compose."""
    path = Path("output/compose/signal_lab.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    build().render(path)


if __name__ == "__main__":
    main()
