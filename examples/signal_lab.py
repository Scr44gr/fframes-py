"""Shared clocks, palette and measurements for the four Signal Lab studies."""

from functools import cache

from examples.shaders import keyframe
from fframes import CubicBezier, Font, Samples, Spring, TextLayout, Tween, compile_animation

WIDTH, HEIGHT, FPS, DURATION = 1920, 1080, 30, 24
PAPER, INK, MUTED, LIME = "#eeeae2", "#152c2b", "#53645e", "#d2f87a"
GREEN, GRAY = "#709542", "#b4bdb1"
TITLES = ("PRODUCT ANNOUNCEMENT", "DATA STORY", "TECHNICAL EXPLAINER", "CREATED WITH FFRAMES")
CARDS = (
    ("01", "Describe", "Rust + SVG"),
    ("02", "Inspect", "Frames + sound"),
    ("03", "Render", "Video file"),
)


def ramp(start: float) -> Tween:
    """Use the original 800 ms Bézier entrance."""
    return Tween(
        from_value=0,
        to_value=1,
        start_at=start,
        duration=0.8,
        easing=CubicBezier(x1=0.16, y1=1, x2=0.3, y2=1),
    )


def rise(start: float) -> Tween:
    """Move upward with the original three-second spring."""
    return Tween(
        from_value=56,
        to_value=0,
        start_at=start,
        duration=3,
        easing=Spring(stiffness=180, damping=20),
    )


@cache
def sample(value: Tween, duration: int = 6) -> tuple[float, ...]:
    """Evaluate native animations in one batch during construction."""
    return tuple(compile_animation((keyframe(value),)).sample_many(range(duration * FPS), FPS))


@cache
def bars(index: int) -> tuple[Samples, Samples, tuple[str, ...]]:
    """Share bar heights, positions and rounded readouts across both APIs."""
    value = (24, 41, 58, 76)[index]
    progress = sample(ramp(0.25 + index * 0.1))
    heights = tuple(max(0.5, value * 4.3 * p) for p in progress)
    return (
        Samples(values=heights, fps=FPS),
        Samples(values=tuple(798 - h for h in heights), fps=FPS),
        tuple(f"{value * p:.0f}" for p in progress),
    )


def heading(layout: TextLayout, text: str) -> str:
    """Fit the static heading once with the upstream font advances."""
    return layout.fit(text, Font(family="DM Sans", size=108, weight=500), width=1536)


PROGRESS = Samples(
    values=tuple(max(0.5, i / FPS / DURATION * 1536) for i in range(DURATION * FPS)), fps=FPS
)
TRAVEL = Tween(from_value=1508, to_value=412, start_at=1.2, duration=2.8, easing="linear")
