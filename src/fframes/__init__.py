"""Typed, validated Python bindings for fframes."""

import fframes._runtime  # noqa: F401  # Register DLLs before loading the extension.
from fframes._native import Animation, ColorAnimation, SvgVideo
from fframes.animation import Timeline, compile_animation, compile_color_animation
from fframes.audio import AudioTrack
from fframes.media import ImageBinding, VideoBinding, VideoInfo, probe_video
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
    "AudioTrack",
    "ColorAnimation",
    "ColorKeyframe",
    "ColorTween",
    "ColorUniform",
    "CubicBezier",
    "FloatUniform",
    "Font",
    "ImageBinding",
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
    "VideoBinding",
    "VideoConfig",
    "VideoInfo",
    "compile_animation",
    "compile_color_animation",
    "compile_video",
    "probe_video",
    "render",
]
