"""Typed, validated Python bindings for fframes."""

import fframes._runtime  # noqa: F401  # Register DLLs before loading the extension.
from fframes._native import Animation, ColorAnimation, SvgVideo
from fframes.animation import Timeline, compile_animation, compile_color_animation
from fframes.audio import AudioTrack
from fframes.media import (
    ExifField,
    ImageBinding,
    ImageInfo,
    VideoBinding,
    VideoInfo,
    probe_image,
    probe_video,
)
from fframes.models import ColorKeyframe, CubicBezier, Keyframe, RenderOptions, Spring, VideoConfig
from fframes.shaders import (
    ColorUniform,
    FloatUniform,
    ImageUniform,
    IntUniform,
    Shader,
    ShaderBinding,
    VectorUniform,
    VideoUniform,
)
from fframes.spectrum import AudioData, Spectrum
from fframes.subtitles import Cue, CueSettings, Subtitles
from fframes.text import Font, TextLayout
from fframes.values import ColorSamples, ColorTween, Samples, Tween
from fframes.video import Video, compile_video, render

__all__ = [
    "Animation",
    "AudioData",
    "AudioTrack",
    "ColorAnimation",
    "ColorKeyframe",
    "ColorSamples",
    "ColorTween",
    "ColorUniform",
    "CubicBezier",
    "Cue",
    "CueSettings",
    "ExifField",
    "FloatUniform",
    "Font",
    "ImageBinding",
    "ImageInfo",
    "ImageUniform",
    "IntUniform",
    "Keyframe",
    "RenderOptions",
    "Samples",
    "Shader",
    "ShaderBinding",
    "Spectrum",
    "Spring",
    "Subtitles",
    "SvgVideo",
    "TextLayout",
    "Timeline",
    "Tween",
    "VectorUniform",
    "Video",
    "VideoBinding",
    "VideoConfig",
    "VideoInfo",
    "VideoUniform",
    "compile_animation",
    "compile_color_animation",
    "compile_video",
    "probe_image",
    "probe_video",
    "render",
]
