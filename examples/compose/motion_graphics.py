"""Motion graphics, fitted quotes and a typing terminal using reusable components."""

from pathlib import Path

from examples.motion_graphics import (
    DURATIONS,
    FPS,
    HEIGHT,
    INSTALL,
    MOTION,
    QUOTE,
    URL,
    WIDTH,
    Scene,
    arguments,
    centered_width,
    fonts,
    quote_lines,
    terminal,
)
from fframes import Font, TextLayout
from fframes.compose import (
    Circle,
    Composition,
    Position,
    Rectangle,
    Stroke,
    Text,
    TextFrames,
    Video,
)


def motion(family: str) -> Composition:
    """Keep scale around the moving text's baseline origin."""
    return Composition(
        opacity=MOTION["fade"],
        children=(
            Composition(
                position=Position(x=960, y=MOTION["y"]),
                origin=(0, 0),
                scale=MOTION["scale"],
                opacity=MOTION["opacity"],
                children=(
                    Text(
                        content="I FIXED",
                        font_family=family,
                        font_size=340,
                        font_weight=700,
                        anchor="baseline",
                        text_anchor="middle",
                        baseline="central",
                        letter_spacing=20,
                        fill="#ffffff",
                    ),
                ),
            ),
            Text(
                content="CLAUDE CODE",
                font_family="Bebas Neue",
                font_size=280,
                position=Position(x=960, y=MOTION["second_y"]),
                opacity=MOTION["second_opacity"],
                anchor="baseline",
                text_anchor="middle",
                baseline="central",
                letter_spacing=14,
                fill="#ffffff",
            ),
            Rectangle(
                size=(MOTION["accent"], 3),
                radius=2,
                fill="#ffffff",
                opacity=0.25,
                position=Position(x=centered_width(MOTION["accent"], 4), y=455),
            ),
            Text(
                content="(for real)",
                font_family=family,
                font_size=60,
                font_weight=300,
                font_style="italic",
                letter_spacing=6,
                fill="#ffffff",
                anchor="baseline",
                text_anchor="middle",
                position=Position(x=960, y=MOTION["third_y"]),
                opacity=MOTION["third_opacity"],
            ),
        ),
    )


def quote(layout: TextLayout, text: str) -> Composition:
    """Fit each quote line once, then animate the block as one group."""
    return Composition(
        opacity=QUOTE["fade"],
        children=(
            Composition(
                opacity=QUOTE["opacity"],
                origin=(960, 540),
                scale=QUOTE["scale"],
                position=Position(y=QUOTE["slide"]),
                children=tuple(
                    Text(
                        content=line or " ",
                        font_family="Bebas Neue",
                        font_size=size,
                        fill="#ffffff",
                        anchor="baseline",
                        text_anchor="middle",
                        letter_spacing=20,
                        position=Position(x=960, y=y),
                    )
                    for line, size, y in quote_lines(layout, text)
                ),
            ),
        ),
    )


def install(layout: TextLayout) -> Composition:
    """Reveal the command and align the cursor using the native font advances."""
    size, x, lines, cursor, blink = terminal(layout)
    return Composition(
        opacity=INSTALL["fade"],
        children=(
            Composition(
                position=Position(x=960, y=INSTALL["y"]),
                origin=(0, 0),
                scale=INSTALL["scale"],
                opacity=INSTALL["opacity"],
                children=(
                    Text(
                        content="INSTALL FFF",
                        font_family="Bebas Neue",
                        font_size=200,
                        anchor="baseline",
                        text_anchor="middle",
                        baseline="central",
                        letter_spacing=16,
                        fill="#ffffff",
                    ),
                ),
            ),
            Rectangle(
                size=(INSTALL["accent"], 2),
                radius=1,
                fill="#ff8c00",
                opacity=0.6,
                position=Position(x=centered_width(INSTALL["accent"], 10), y=380),
            ),
            Composition(
                position=Position(y=INSTALL["box_y"]),
                opacity=INSTALL["box_opacity"],
                children=(
                    Rectangle(
                        size=(1520, 160),
                        radius=16,
                        position=Position(x=200, y=420),
                        fill="#1a1a2e",
                        stroke=Stroke(color="#553300", width=1.5),
                    ),
                    *(
                        Circle(radius=9, fill=color, position=Position(x=cx - 9, y=437))
                        for cx, color in ((232, "#ff5f57"), (258, "#febc2e"), (284, "#28c840"))
                    ),
                    Text(
                        content="$ ",
                        font_family="JetBrains Mono",
                        font_size=size,
                        fill="#ff8c00",
                        anchor="baseline",
                        baseline="central",
                        position=Position(x=250, y=506),
                    ),
                    Text(
                        content=TextFrames(frames=lines),
                        font_family="JetBrains Mono",
                        font_size=size,
                        fill="#e0e0ff",
                        anchor="baseline",
                        baseline="central",
                        position=Position(x=x, y=506),
                    ),
                    Rectangle(
                        size=(size * 0.55, size * 0.9),
                        fill="#e0e0ff",
                        opacity=blink,
                        position=Position(x=cursor, y=506 - size * 0.45),
                    ),
                ),
            ),
            Composition(
                position=Position(y=INSTALL["url_y"]),
                opacity=INSTALL["url_opacity"],
                children=(
                    Text(
                        content=URL,
                        font_family="JetBrains Mono",
                        font_size=32,
                        anchor="baseline",
                        text_anchor="middle",
                        letter_spacing=1,
                        position=Position(x=960, y=680),
                        fill="#ffffff",
                    ),
                ),
            ),
        ),
    )


def build(
    scene: Scene = "motion",
    *,
    text: str = "PERFORMANCE",
    family: str = "Helvetica Neue",
    extra_fonts: tuple[Path, ...] = (),
) -> Video:
    """Preserve the upstream timing and expose its system-font dependency."""
    sources = fonts(extra_fonts)
    layout = TextLayout(fonts=sources, load_system_fonts=scene == "motion")
    if scene == "motion":
        layout.width("I FIXED", Font(family=family))
        content = motion(family)
    elif scene == "quote":
        content = quote(layout, text)
    else:
        content = install(layout)
    return Video(
        resolution=(WIDTH, HEIGHT),
        fps=FPS,
        fonts=sources,
        load_system_fonts=scene == "motion",
        composition=Composition(
            duration=DURATIONS[scene], children=(Rectangle(size=(WIDTH, HEIGHT)), content)
        ),
    )


def main() -> None:
    """Render the selected study into output/compose."""
    args = arguments()
    path = Path(f"output/compose/motion_{args.scene}.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    build(args.scene, text=args.text, family=args.family, extra_fonts=tuple(args.font)).render(path)


if __name__ == "__main__":
    main()
