"""Typed, validated Python bindings for fframes."""

import fframes._runtime  # noqa: F401  # Register DLLs before loading the extension.
from fframes._native import Animation, ColorAnimation, SvgVideo, available_encoders
from fframes.animation import Timeline, compile_animation, compile_color_animation
from fframes.audio import AudioTrack
from fframes.inspection import contact_sheet, detect_pops, inspect_frames, save_preview
from fframes.lottie import Lottie, LottieBinding, LottieInfo
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
from fframes.three_d import SceneBinding
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
    "Lottie",
    "LottieBinding",
    "LottieInfo",
    "RenderOptions",
    "Samples",
    "SceneBinding",
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
    "available_encoders",
    "compile_animation",
    "compile_color_animation",
    "compile_video",
    "contact_sheet",
    "detect_pops",
    "inspect_frames",
    "probe_image",
    "probe_video",
    "render",
    "save_preview",
]
