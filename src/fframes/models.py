"""Immutable input schemas shared by both APIs."""

from itertools import pairwise
from math import isfinite
from os import cpu_count
from pathlib import Path
from typing import Annotated, Literal, Self, TypeAlias, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

Index: TypeAlias = Annotated[int, Field(ge=0, le=2**63 - 1, strict=True)]
PositiveInt: TypeAlias = Annotated[int, Field(gt=0, le=2**31 - 1, strict=True)]
FiniteFloat: TypeAlias = Annotated[float, Field(allow_inf_nan=False)]
Length: TypeAlias = Annotated[float, Field(gt=0, le=1e7, allow_inf_nan=False)]
Size: TypeAlias = tuple[Length, Length]
FontWeight: TypeAlias = Annotated[int, Field(ge=100, le=900)]
Seconds: TypeAlias = Annotated[float, Field(ge=0, le=3.4028234e38, allow_inf_nan=False)]
Svg: TypeAlias = Annotated[str, Field(min_length=1)]
Frames: TypeAlias = Annotated[tuple[Svg, ...], Field(min_length=1)]
BasicEasing: TypeAlias = Literal["linear", "ease_in", "ease_out", "ease_in_out"]
Backend: TypeAlias = Literal["cpu", "skia", "vulkan", "metal"]
Color: TypeAlias = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")]


class Model(BaseModel):
    """Validate once and prevent mutation during native work."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True, validate_default=True)


class Spring(Model):
    """Upstream spring physics; duration caps its natural settling time."""

    kind: Literal["spring"] = "spring"
    mass: Annotated[float, Field(gt=0, le=1e4, allow_inf_nan=False)] = 1.0
    stiffness: Annotated[float, Field(gt=0, le=1e4, allow_inf_nan=False)] = 180.0
    damping: Annotated[float, Field(gt=0, le=1e4, allow_inf_nan=False)] = 20.0

    @model_validator(mode="after")
    def check_settling(self) -> Self:
        """Avoid pathological upstream settling-time loops and float32 overflow."""
        if not 1e-3 <= self.damping / self.mass <= 1e6 or not (
            1e-3 <= self.stiffness / self.mass <= 1e6
        ):
            msg = "spring damping/mass and stiffness/mass must be between 0.001 and 1000000"
            raise ValueError(msg)
        return self


class CubicBezier(Model):
    """A custom upstream easing curve with control points in the unit square."""

    kind: Literal["cubic_bezier"] = "cubic_bezier"
    x1: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    y1: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    x2: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    y2: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


Easing: TypeAlias = BasicEasing | Spring | CubicBezier


def _source(value: str | Path) -> str | Path:
    if not str(value) or "\0" in str(value):
        msg = "source must be a nonempty filesystem path without NUL characters"
        raise ValueError(msg)
    return value


Source: TypeAlias = Annotated[str | Path, AfterValidator(_source)]


class VideoConfig(Model):
    """Canvas dimensions, integer frame rate and optional system fonts."""

    width: PositiveInt = 1920
    height: PositiveInt = 1080
    fps: PositiveInt = 30
    load_system_fonts: bool = False
    fonts: tuple[Source, ...] = ()
    backend: Backend = "cpu"


CodecName: TypeAlias = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_]+$")]
CodecValue: TypeAlias = Annotated[str, Field(min_length=1, pattern=r"^[^\x00]+$")]


class LimiterOptions(Model):
    """Master peak limiter; times are milliseconds and ceiling is dBFS."""

    ceiling_db: Annotated[float, Field(ge=-120, le=0, allow_inf_nan=False)] = -1.0
    lookahead_ms: Annotated[float, Field(ge=0, le=1000, allow_inf_nan=False)] = 5.0
    release_ms: Annotated[float, Field(gt=0, le=60000, allow_inf_nan=False)] = 80.0


class AudioMixOptions(Model):
    """Settings shared by audio previews, analysis and encoded output."""

    master_gain_db: Annotated[float, Field(ge=-120, le=24, allow_inf_nan=False)] = 0.0
    limiter: LimiterOptions | None = LimiterOptions()
    declick: bool = True


class CodecOptions(Model):
    """Encoder-specific string options; unsupported options fail before rendering."""

    codec_params: tuple[tuple[CodecName, CodecValue], ...] = ()

    @model_validator(mode="after")
    def check_parameters(self) -> Self:
        """Reject duplicate parameter keys instead of relying on FFmpeg ordering."""
        names = [name for name, _ in self.codec_params]
        if len(names) != len(set(names)):
            raise ValueError("codec_params keys must be unique")
        return self


class AudioEncoderOptions(CodecOptions):
    """Audio codec, sample format, bitrate and output rate."""

    encoder: CodecName = "aac"
    bitrate: PositiveInt = 192_000
    sample_rate: PositiveInt = 48_000
    sample_format: Literal["fltp", "flt", "s16", "s16p", "s32", "s32p"] = "fltp"


class RenderOptions(CodecOptions):
    """Encoding settings and an optional half-open range of original frame indices."""

    encoder: CodecName = "libopenh264"
    concurrency: PositiveInt = Field(default_factory=lambda: cpu_count() or 1)
    bitrate: PositiveInt = 8_000_000
    color_matrix: Literal["bt601", "bt709"] = "bt601"
    frame_range: tuple[Index, Index] | None = None
    pixel_format: CodecName | None = None
    bitrate_tolerance: Annotated[int, Field(ge=0, le=2**31 - 1)] = 0
    qmin: Annotated[int, Field(ge=0, le=255)] = 15
    qmax: Annotated[int, Field(ge=0, le=255)] = 60
    qcompress: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] = 0.6
    max_qdiff: Annotated[int, Field(ge=0, le=255)] = 4
    gop_size: Annotated[int, Field(ge=0, le=2**31 - 1)] = 24
    tag: Annotated[str, Field(pattern=r"^[ -~]{4}$")] | None = None
    audio: AudioEncoderOptions = AudioEncoderOptions()
    audio_mix: AudioMixOptions = AudioMixOptions()
    fps: PositiveInt | None = None
    scale: Annotated[float, Field(gt=0, le=64, allow_inf_nan=False)] = 1.0

    @model_validator(mode="after")
    def check_frame_range(self) -> Self:
        """Reject empty or reversed exports rather than silently changing their bounds."""
        if self.frame_range is not None and self.frame_range[0] >= self.frame_range[1]:
            raise ValueError("frame_range requires start < end; end is exclusive")
        if self.qmin > self.qmax:
            raise ValueError("qmin must be less than or equal to qmax")
        return self


class Interval(Model):
    """A finite interpolation interval shared by scalar and color keyframes."""

    start: Seconds
    end: Seconds
    easing: Easing = "linear"

    @model_validator(mode="after")
    def check_interval(self) -> Self:
        """Reject zero or negative duration before crossing the native boundary."""
        if self.end <= self.start:
            msg = "end must be greater than start"
            raise ValueError(msg)
        return self


class Keyframe(Interval):
    """Interpolate a scalar over the half-open interval [start, end)."""

    from_value: FiniteFloat
    to_value: FiniteFloat

    @model_validator(mode="after")
    def check_range(self) -> Self:
        """Reject interpolation ranges that overflow native arithmetic."""
        if not isfinite(self.to_value - self.from_value):
            msg = "interpolation range must be finite"
            raise ValueError(msg)
        return self


class ColorKeyframe(Interval):
    """Interpolate RGBA channels using the original fframes color rules."""

    from_value: Color
    to_value: Color


Key = TypeVar("Key", bound=Interval)


def _ordered(keyframes: tuple[Key, ...]) -> tuple[Key, ...]:
    for previous, current in pairwise(keyframes):
        if current.start < previous.end:
            msg = "keyframes must be ordered and must not overlap"
            raise ValueError(msg)
    return keyframes


Keyframes: TypeAlias = Annotated[
    tuple[Keyframe, ...], Field(min_length=1), AfterValidator(_ordered)
]
ColorKeyframes: TypeAlias = Annotated[
    tuple[ColorKeyframe, ...], Field(min_length=1), AfterValidator(_ordered)
]


def _check_path(path: str | Path) -> str | Path:
    if not str(path) or "\0" in str(path) or not Path(path).suffix:
        msg = "output path must have an extension and contain no NUL characters"
        raise ValueError(msg)
    return path


OutputPath: TypeAlias = Annotated[str | Path, AfterValidator(_check_path)]
