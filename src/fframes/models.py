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
Seconds: TypeAlias = Annotated[float, Field(ge=0, le=3.4028234e38, allow_inf_nan=False)]
Svg: TypeAlias = Annotated[str, Field(min_length=1)]
Frames: TypeAlias = Annotated[tuple[Svg, ...], Field(min_length=1)]
Easing: TypeAlias = Literal["linear", "ease_in", "ease_out", "ease_in_out"]
Color: TypeAlias = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")]


class Model(BaseModel):
    """Validate once and prevent mutation during native work."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True, validate_default=True)


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


class RenderOptions(Model):
    """Encoder selection and number of parallel rendering workers."""

    encoder: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_]+$")] = "mpeg4"
    concurrency: PositiveInt = Field(default_factory=lambda: cpu_count() or 1)


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
