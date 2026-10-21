"""Inspect compiled videos and save diagnostic previews without Python frame loops."""

from pathlib import Path
from typing import Annotated, Literal, TypeAlias

from pydantic import ConfigDict, Field, TypeAdapter, validate_call

from fframes import _native
from fframes.models import FiniteFloat, Index, Model, OutputPath, PositiveInt

NativeVideo: TypeAlias = _native.SvgVideo | _native.SceneVideo
Indices: TypeAlias = Annotated[tuple[Index, ...], Field(min_length=1)]
Resolution: TypeAlias = tuple[PositiveInt, PositiveInt]
Crop: TypeAlias = tuple[Index, Index, PositiveInt, PositiveInt]
_validation = ConfigDict(strict=True, arbitrary_types_allowed=True)


class Diagnostic(Model):
    """A concrete upstream finding; optional details depend on kind."""

    kind: Literal[
        "missing_media",
        "missing_font",
        "missing_glyph",
        "renderer_warning",
        "text_clipped",
        "text_off_canvas",
        "invalid_transform",
        "empty_frame",
        "panic",
    ]
    severity: Literal["info", "warning", "error"]
    key: str
    message: str
    media: Literal["image", "audio", "video", "subtitles", "lottie"] | None = None
    name: str | None = None
    text: str | None = None
    bbox: tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat] | None = None
    id: str | None = None


class Element(Model):
    """A named SVG element's bounds, in the video's coordinates."""

    id: str
    kind: Literal["path", "group", "image", "text"]
    x: FiniteFloat
    y: FiniteFloat
    width: FiniteFloat
    height: FiniteFloat


class FrameReport(Model):
    """Structural SVG findings; 3D interiors are checked through rendered pixels."""

    frame: Index
    seconds: FiniteFloat
    diagnostics: tuple[Diagnostic, ...]
    elements: tuple[Element, ...]


class Pop(Model):
    """An abrupt local change, expressed in pixels of the requested inspection resolution."""

    frame: Index
    kind: Literal["step", "flash"]
    x: Index
    y: Index
    width: PositiveInt
    height: PositiveInt
    strength: FiniteFloat


_reports = TypeAdapter(tuple[FrameReport, ...])
_pops = TypeAdapter(tuple[Pop, ...])


def _png(path: OutputPath) -> Path:
    destination = Path(path)
    if destination.suffix.lower() != ".png":
        raise ValueError("diagnostic images require a .png extension")
    return destination


@validate_call(config=_validation)
def inspect_frames(video: NativeVideo, frames: Indices = (0,)) -> tuple[FrameReport, ...]:
    """Inspect selected frames in native parallel workers, preserving the requested order."""
    return _reports.validate_json(_native.inspect_video(video, frames))


@validate_call(config=_validation)
def save_preview(
    video: NativeVideo,
    path: OutputPath,
    *,
    frame: Index = 0,
    size: Resolution | None = None,
    crop: Crop | None = None,
    labels: bool = False,
) -> Path:
    """Save a PNG, optionally resized, labelled and then cropped in preview pixels."""
    destination = _png(path)
    _native.preview_video(video, frame, destination, size, crop, labels)
    return destination


@validate_call(config=_validation)
def contact_sheet(
    video: NativeVideo,
    path: OutputPath,
    *,
    frames: Indices,
    columns: PositiveInt = 4,
    size: Resolution | None = None,
    onion: bool = False,
) -> Path:
    """Save labelled frames in a grid, or overlay them as an onion skin."""
    destination = _png(path)
    _native.sheet_video(video, frames, destination, columns, size, onion)
    return destination


@validate_call(config=_validation)
def detect_pops(
    video: NativeVideo,
    *,
    start: Index = 0,
    end: PositiveInt | None = None,
    size: Resolution | None = None,
) -> tuple[Pop, ...]:
    """Scan consecutive frames in constant memory; results are review cues, not pass/fail."""
    return _pops.validate_json(
        _native.detect_pops(video, start, len(video) if end is None else end, size)
    )
