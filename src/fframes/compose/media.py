"""File-backed images and audio; files are loaded during compilation."""

from typing import Literal

from fframes.audio import AudioSettings
from fframes.compose.components import Item, Size, Visual
from fframes.media import ClipSource
from fframes.models import Source


class Image(Visual):
    """A raster image stretched to the explicit local size."""

    kind: Literal["image"] = "image"
    source: Source
    size: Size


class Audio(AudioSettings, Item):
    """Mix a file in local time, with optional looping from the source offset.

    Unlooped audio ends at its natural duration or the enclosing interval.
    Fades apply to the complete audible interval, including repetitions.
    """


class VideoClip(ClipSource, Visual):
    """Play a local video on the clip's local clock; add Audio separately to mix sound."""

    kind: Literal["video"] = "video"
    size: Size
