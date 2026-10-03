"""Typed, validated Python bindings for fframes."""

import fframes._runtime  # noqa: F401  # Register DLLs before loading the extension.
from fframes._native import Animation, ColorAnimation, SvgVideo
from fframes.animation import Timeline, compile_animation, compile_color_animation
from fframes.models import ColorKeyframe, CubicBezier, Keyframe, RenderOptions, Spring, VideoConfig
from fframes.shaders import (
    ColorUniform,
    FloatUniform,
    ImageUniform,
    IntUniform,
    Shader,
    ShaderBinding,
    VectorUniform,
)
from fframes.values import ColorTween, Tween
from fframes.video import Video, compile_video, render

__all__ = [
    "Animation",
    "ColorAnimation",
    "ColorKeyframe",
    "ColorTween",
    "ColorUniform",
    "CubicBezier",
    "FloatUniform",
    "ImageUniform",
    "IntUniform",
    "Keyframe",
    "RenderOptions",
    "Shader",
    "ShaderBinding",
    "Spring",
    "SvgVideo",
    "Timeline",
    "Tween",
    "VectorUniform",
    "Video",
    "VideoConfig",
    "compile_animation",
    "compile_color_animation",
    "compile_video",
    "render",
]
