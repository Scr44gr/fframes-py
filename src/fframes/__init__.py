"""Typed, validated Python bindings for fframes."""

import fframes._runtime  # noqa: F401  # Register DLLs before loading the extension.
from fframes._native import Animation, SvgVideo
from fframes.animation import Timeline, compile_animation
from fframes.models import Keyframe, RenderOptions, VideoConfig
from fframes.video import Video, compile_video, render

__all__ = [
    "Animation",
    "Keyframe",
    "RenderOptions",
    "SvgVideo",
    "Timeline",
    "Video",
    "VideoConfig",
    "compile_animation",
    "compile_video",
    "render",
]
