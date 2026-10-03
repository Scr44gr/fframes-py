"""Typed, validated Python bindings for fframes."""

import fframes._runtime  # noqa: F401  # Register DLLs before loading the extension.
from fframes.animation import Timeline
from fframes.models import Keyframe, RenderOptions, VideoConfig
from fframes.video import Video

__all__ = ["Keyframe", "RenderOptions", "Timeline", "Video", "VideoConfig"]
