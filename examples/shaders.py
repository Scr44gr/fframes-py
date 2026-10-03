"""Shared programs and timing from upstream examples/shaders."""

import argparse
import sys
from pathlib import Path

from fframes import ColorTween, ColorUniform, FloatUniform, Keyframe, Shader, Spring, Tween
from fframes.models import Backend

WIDTH, HEIGHT, FPS, DURATION = 1920, 1080, 30, 8
GPU_BACKEND: Backend = "metal" if sys.platform == "darwin" else "vulkan"
CARD_Y = Tween(from_value=300, to_value=160, start_at=0.3, duration=7.7, easing=Spring())
CARD_OPACITY = Tween(from_value=0, to_value=1, start_at=0.3, duration=0.6, easing="ease_out")
TITLE_OPACITY = Tween(from_value=0, to_value=1, start_at=0.6, duration=0.8, easing="ease_out")


def keyframe(tween: Tween) -> Keyframe:
    """Use the same motion description for native batch sampling and compose."""
    return Keyframe(
        start=tween.start_at,
        end=tween.start_at + tween.duration,
        from_value=tween.from_value,
        to_value=tween.to_value,
        easing=tween.easing,
    )


def programs(assets: dict[str, Path]) -> tuple[Shader, Shader]:
    """Read the verified original programs without copying them into Git."""
    return (
        Shader(
            source=assets["aurora"].read_text(encoding="utf-8"),
            uniforms=(
                ColorUniform(
                    name="uColorA",
                    value=ColorTween(
                        from_value="#22d3ee", to_value="#a855f7", duration=8, easing="ease_in_out"
                    ),
                ),
                ColorUniform(name="uColorB", value="#f472b6"),
                FloatUniform(name="uSpeed", value=0.6),
            ),
        ),
        Shader(source=assets["torus"].read_text(encoding="utf-8"), language="shadertoy"),
    )


class Arguments(argparse.Namespace):
    """Backend selection shared by the shader examples."""

    backend: Backend


def backend_argument() -> Backend:
    """Use the platform's GPU backend unless --backend skia is requested."""
    parser = argparse.ArgumentParser(description="Render with Skia on the CPU or GPU.")
    parser.add_argument("--backend", choices=("skia", "vulkan", "metal"), default=GPU_BACKEND)
    return parser.parse_args(namespace=Arguments()).backend
