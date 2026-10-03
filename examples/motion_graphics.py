"""Shared timing and font measurements for the three upstream motion studies."""

import argparse
from functools import cache
from pathlib import Path
from typing import Literal, TypeAlias

from examples.assets import files
from examples.shaders import keyframe
from fframes import Font, Samples, Spring, TextLayout, Tween, compile_animation
from fframes.models import Easing

Scene: TypeAlias = Literal["motion", "quote", "install"]
WIDTH, HEIGHT, FPS = 1920, 1080, 60
SPRING = Spring(stiffness=300, damping=26)
COMMAND = "curl -L https://dmtrkovalenko.dev/install-fff-mcp.sh | bash"
URL = "https://github.com/dmtrKovalenko/fff.nvim"
DURATIONS: dict[Scene, int] = {"motion": 4, "quote": 3, "install": 10}


def tween(a: float, b: float, start: float, end: float, easing: Easing = "ease_in_out") -> Tween:
    """Express the upstream interval as a reusable native tween."""
    return Tween(from_value=a, to_value=b, start_at=start, duration=end - start, easing=easing)


@cache
def sample(value: Tween, duration: int) -> tuple[float, ...]:
    """Batch native evaluation once for SVG authoring and procedural values."""
    return tuple(compile_animation((keyframe(value),)).sample_many(range(duration * FPS), FPS))


MOTION = {
    "scale": tween(1.4, 1, 0.2, 0.6, SPRING),
    "opacity": tween(0, 1, 0.2, 0.5, "ease_out"),
    "y": tween(540, 280, 0.7, 1.1),
    "second_opacity": tween(0, 1, 0.8, 1.4),
    "second_y": tween(720, 620, 0.8, 1.5),
    "accent": tween(0.5, 1000, 1, 1.6),
    "third_y": tween(890, 810, 1.3, 1.8, "ease_out"),
    "third_opacity": tween(0, 0.6, 1.3, 1.8, "ease_out"),
    "fade": tween(1, 0, 3.2, 3.8, "ease_in"),
}
QUOTE = {
    "scale": tween(1.6, 1, 0, 0.8, SPRING),
    "slide": tween(80, 0, 0, 0.6, SPRING),
    "opacity": tween(0, 1, 0, 0.3, "ease_out"),
    "fade": tween(1, 0, 2.2, 2.8, "ease_in"),
}
INSTALL = {
    "scale": tween(1.5, 1, 0, 0.6, SPRING),
    "opacity": tween(0, 1, 0, 0.3, "ease_out"),
    "y": tween(440, 260, 0.5, 1),
    "box_opacity": tween(0, 1, 0.7, 1.2, "ease_out"),
    "box_y": tween(40, 0, 0.7, 1.3, SPRING),
    "typed": tween(0, len(COMMAND), 1, 2.2, "linear"),
    "cursor": tween(0, 1, 1, 1.1, "linear"),
    "url_opacity": tween(0, 0.7, 2.5, 3, "ease_out"),
    "url_y": tween(30, 0, 2.5, 3, SPRING),
    "accent": tween(0.5, 600, 0.4, 1),
    "fade": tween(1, 0, 9.2, 9.8, "ease_in"),
}


def centered_width(value: Tween, duration: int) -> Samples:
    """Keep the expanding accent centered without stretching its corner radius."""
    return Samples(values=tuple(960 - v / 2 for v in sample(value, duration)), fps=FPS)


def fonts(extra: tuple[Path, ...] = ()) -> tuple[Path, ...]:
    """Use the pinned font files plus any explicitly supplied system-family file."""
    assets = files("motion_graphics")
    return assets["bebas_neue"], assets["jetbrains_mono"], *extra


def fit_size(
    layout: TextLayout, text: str, family: str, maximum: int, minimum: int, step: int, width: int
) -> int:
    """Follow upstream's discrete font-size search, once during construction."""
    for size in range(maximum, minimum - 1, -step):
        if layout.width(text, Font(family=family, size=size)) <= width:
            return size
    return minimum


def quote_lines(layout: TextLayout, text: str) -> tuple[tuple[str, int, float], ...]:
    """Resolve independent line sizes and center the resulting block vertically."""
    lines = text.splitlines()
    if not lines or not any(lines):
        raise ValueError("quote text must contain a visible line")
    sizes = [fit_size(layout, line, "Bebas Neue", 500, 60, 10, 1520) for line in lines]
    y = 540 - sum(sizes) * 0.9 / 2
    result = []
    for line, size in zip(lines, sizes, strict=True):
        y += size * 0.9
        result.append((line, size, y))
    return tuple(result)


def terminal(layout: TextLayout) -> tuple[int, float, tuple[str, ...], Samples, Samples]:
    """Precompute Unicode-safe typing, advance widths and the original cursor blink."""
    size = fit_size(layout, COMMAND, "JetBrains Mono", 42, 16, 2, 1360)
    font = Font(family="JetBrains Mono", size=size)
    text_x = 250 + layout.width("$ ", font)
    counts = sample(INSTALL["typed"], 10)
    lines = tuple(COMMAND[: int(count)] for count in counts)
    widths = layout.widths(lines, font)
    cursor = Samples(values=tuple(text_x + width + 2 for width in widths), fps=FPS)
    fade = sample(INSTALL["cursor"], 10)
    blink = Samples(
        values=tuple(
            float((i // 30) % 2 == 0) if n >= len(COMMAND) else fade[i]
            for i, n in enumerate(counts)
        ),
        fps=FPS,
    )
    return size, text_x, lines, cursor, blink


class Arguments(argparse.Namespace):
    """CLI options common to the native and component ports."""

    scene: Scene
    text: str
    family: str
    font: list[Path]


def arguments() -> Arguments:
    """Select a scene and explicitly choose a replacement for missing Helvetica Neue."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", choices=tuple(DURATIONS), default="motion")
    parser.add_argument("--text", default="PERFORMANCE")
    parser.add_argument("--family", default="Helvetica Neue")
    parser.add_argument("--font", type=Path, action="append", default=[])
    args = parser.parse_args(namespace=Arguments())
    args.text = args.text.replace("\\n", "\n")
    return args
