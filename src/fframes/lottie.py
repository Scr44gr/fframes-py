"""Lottie shape animations rendered by the upstream vector evaluator."""

from functools import cached_property
from typing import Annotated

from pydantic import Field

from fframes import _native
from fframes.models import Model, PositiveInt, Source
from fframes.values import Duration, Start


class LottieInfo(Model):
    """Intrinsic canvas size and duration in seconds."""

    width: PositiveInt
    height: PositiveInt
    duration: Duration


class Lottie(Model):
    """Play vector shape layers. Upstream does not support text, images or expressions."""

    source: Source
    offset: Start = 0.0
    speed: Annotated[float, Field(gt=0, le=100, allow_inf_nan=False)] = 1.0
    loop: bool = False

    @cached_property
    def info(self) -> LottieInfo:
        """Parse the file once when metadata is requested."""
        width, height, duration = _native.lottie_info(self.source)
        return LottieInfo(width=width, height=height, duration=duration)


class LottieBinding(Model):
    """Expose an animation as href='lottie:name' in an SVG frame."""

    name: Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]
    animation: Lottie
    size: tuple[PositiveInt, PositiveInt]
    start_at: Start = 0.0
    duration: Duration | None = None
