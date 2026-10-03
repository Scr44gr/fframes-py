"""Explicit local image bindings and synchronized video sources."""

from typing import Annotated, TypeAlias

from pydantic import ConfigDict, Field, validate_call

from fframes import _native
from fframes.models import Model, PositiveInt, Source
from fframes.values import Duration, Start

Name: TypeAlias = Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]


class ImageBinding(Model):
    """Bind a local raster file to an SVG image href='image:name'."""

    name: Name
    source: Source


class ClipSource(Model):
    """Decode at the composition's frame rate, with a source offset and optional loop."""

    source: Source
    offset: Start = 0.0
    loop: bool = False


class VideoBinding(ClipSource):
    """Bind synchronized pixels to an SVG image href='video:name'."""

    name: Name
    start_at: Start = 0.0
    duration: Duration | None = None


class VideoInfo(Model):
    """Native source dimensions, duration in seconds and stream frame rate."""

    width: PositiveInt
    height: PositiveInt
    duration: Duration
    fps: Annotated[float, Field(gt=0, allow_inf_nan=False)]


@validate_call(config=ConfigDict(strict=True))
def probe_video(source: Source) -> VideoInfo:
    """Inspect and decode the first source frame using the upstream decoder."""
    width, height, duration, fps = _native.video_info(str(source))
    return VideoInfo(width=width, height=height, duration=duration, fps=fps)
