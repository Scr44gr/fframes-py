"""Shared shader, flicker and readout from upstream examples/neon-triangle."""

from math import tau
from pathlib import Path

from fframes import ColorUniform, FloatUniform, Keyframe, Shader, Spring, Tween

WIDTH, HEIGHT, FPS, DURATION = 1920, 1080, 60, 6
TITLE = tuple(
    Keyframe(start=start, end=end, from_value=a, to_value=b)
    for start, end, a, b in (
        (0.20, 0.24, 0.0, 1.0),
        (0.30, 0.33, 1.0, 0.15),
        (0.40, 0.43, 0.15, 1.0),
        (0.56, 0.58, 1.0, 0.4),
        (0.66, 0.80, 0.4, 1.0),
    )
)
SUBTITLE_OPACITY = Tween(from_value=0, to_value=1, start_at=0.9, duration=0.6, easing="ease_out")
SUBTITLE_X = Tween(
    from_value=-40, to_value=0, start_at=0.9, duration=5.1, easing=Spring(stiffness=140)
)


def program(assets: dict[str, Path]) -> Shader:
    """Bind the original constant angular velocities and magenta tint."""
    return Shader(
        source=assets["triangle"].read_text(encoding="utf-8"),
        uniforms=(
            FloatUniform(
                name="uYaw",
                value=Tween(from_value=0, to_value=DURATION * tau / 4, duration=DURATION),
            ),
            FloatUniform(
                name="uRoll",
                value=Tween(from_value=0, to_value=DURATION * tau / 12, duration=DURATION),
            ),
            ColorUniform(name="uColor", value="#ff2bd6"),
        ),
    )


def readouts() -> tuple[str, ...]:
    """Prepare the finite readout once; no Python formatting runs during rendering."""
    return tuple(
        f"yaw {i / FPS * 90 % 360:03.0f}°  roll {i / FPS * 30 % 360:03.0f}°  frame {i:03}"
        for i in range(DURATION * FPS)
    )
