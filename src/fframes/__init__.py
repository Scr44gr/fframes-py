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
from fframes.text import Font, TextLayout
from fframes.values import ColorTween, Samples, Tween
from fframes.video import Video, compile_video, render

__all__ = [
    "Animation",
    "ColorAnimation",
    "ColorKeyframe",
    "ColorTween",
    "ColorUniform",
    "CubicBezier",
    "FloatUniform",
    "Font",
    "ImageUniform",
    "IntUniform",
    "Keyframe",
    "RenderOptions",
    "Samples",
    "Shader",
    "ShaderBinding",
    "Spring",
    "SvgVideo",
    "TextLayout",
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
