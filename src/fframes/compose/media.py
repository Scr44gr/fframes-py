"""File-backed images and audio; files are loaded during compilation."""

from typing import Literal

from fframes.audio import AudioSettings
from fframes.compose.components import Item, Size, Visual
from fframes.media import ClipSource
from fframes.models import Source


class MediaVisual(Visual):
    """Size a media viewport by stretching, letterboxing or cropping its source."""

    size: Size
    fit: Literal["fill", "contain", "cover"] = "fill"


class Image(MediaVisual):
    """A raster image loaded once, with explicit size and fitting."""

    kind: Literal["image"] = "image"
    source: Source


class Audio(AudioSettings, Item):
    """Mix a file in local time, with optional looping from the source offset.

    Unlooped audio ends at its natural duration or the enclosing interval.
    Fades apply to the complete audible interval, including repetitions.
    """


class VideoClip(ClipSource, MediaVisual):
    """Play a local video on the clip's local clock; add Audio separately to mix sound."""

    kind: Literal["video"] = "video"
