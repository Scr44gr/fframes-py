"""Shared scene data from upstream examples/hello-world at the pinned revision."""

from itertools import pairwise

from fframes import ColorKeyframe, Keyframe

WIDTH, HEIGHT, FPS, DURATION = 1920, 1080, 30, 30
BACKGROUND = ("#FFFFFF", "#F8FAFC", "#FFF7ED", "#FEF2F2", "#F7FEE7", "#ECFDF5", "#FAF5FF")
MOVEMENT = (
    (0, 2, (400, 400), (600, 880)),
    (2, 6, (600, 880), (1150, 0)),
    (6, 10, (1150, 0), (1710, 880)),
)


def background() -> tuple[ColorKeyframe, ...]:
    """Transition through the shared global background, five seconds per color."""
    return tuple(
        ColorKeyframe(start=i * 5, end=(i + 1) * 5, from_value=a, to_value=b)
        for i, (a, b) in enumerate(pairwise(BACKGROUND))
    )


def coordinate(axis: int) -> tuple[Keyframe, ...]:
    """Describe the original square's absolute coordinates for batch sampling."""
    return tuple(
        Keyframe(start=start, end=end, from_value=a[axis], to_value=b[axis])
        for start, end, a, b in MOVEMENT
    )
