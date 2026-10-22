"""Typed, validated Python bindings for fframes."""

import fframes._runtime  # noqa: F401  # Register DLLs before loading the extension.
from fframes._native import Animation, ColorAnimation, SvgVideo
from fframes.analysis import (
    AudioAnalysisOptions,
    AudioInspection,
    AudioReport,
    AudioSection,
    analyze_audio,
)
from fframes.animation import Timeline, compile_animation, compile_color_animation
from fframes.audio import AudioTrack
from fframes.buffers import ImageBuffer, Pcm, VideoFrames
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
from fframes.models import (
    AudioEncoderOptions,
    AudioMixOptions,
    ColorKeyframe,
    CubicBezier,
    Keyframe,
    LimiterOptions,
    RenderOptions,
    Spring,
    VideoConfig,
)
from fframes.rendering import RenderControl, RenderProgress, available_encoders
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
from fframes.timing import SceneRange, TimelineIndex, inspect_timeline
from fframes.values import ColorSamples, ColorTween, Samples, Tween
from fframes.video import Video, compile_video, render

__all__ = [
    "Animation",
    "AudioAnalysisOptions",
    "AudioData",
    "AudioEncoderOptions",
    "AudioInspection",
    "AudioMixOptions",
    "AudioReport",
    "AudioSection",
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
    "ImageBuffer",
    "ImageInfo",
    "ImageUniform",
    "IntUniform",
    "Keyframe",
    "LimiterOptions",
    "Lottie",
    "LottieBinding",
    "LottieInfo",
    "Pcm",
    "RenderControl",
    "RenderOptions",
    "RenderProgress",
    "Samples",
    "SceneBinding",
    "SceneRange",
    "Shader",
    "ShaderBinding",
    "Spectrum",
    "Spring",
    "Subtitles",
    "SvgVideo",
    "TextLayout",
    "Timeline",
    "TimelineIndex",
    "Tween",
    "VectorUniform",
    "Video",
    "VideoBinding",
    "VideoConfig",
    "VideoFrames",
    "VideoInfo",
    "VideoUniform",
    "analyze_audio",
    "available_encoders",
    "compile_animation",
    "compile_color_animation",
    "compile_video",
    "contact_sheet",
    "detect_pops",
    "inspect_frames",
    "inspect_timeline",
    "probe_image",
    "probe_video",
    "render",
    "save_preview",
]
