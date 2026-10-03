"""Scalar animation descriptions evaluated by Rust."""

from math import isfinite
from typing import Annotated, Self, TypeAlias

from pydantic import Field, model_validator

from fframes.models import Color, Easing, FiniteFloat, Model

Duration: TypeAlias = Annotated[float, Field(gt=0, le=86400, allow_inf_nan=False)]


class Tween(Model):
    """Interpolate in local seconds, holding endpoints outside the interval."""

    from_value: FiniteFloat
    to_value: FiniteFloat
    duration: Duration
    easing: Easing = "linear"

    @model_validator(mode="after")
    def check_range(self) -> Self:
        """Keep interpolation representable before native compilation."""
        if not isfinite(self.to_value - self.from_value):
            msg = "interpolation range must be finite"
            raise ValueError(msg)
        return self


class ColorTween(Model):
    """Interpolate RGBA channels with the upstream color animation rules."""

    from_value: Color
    to_value: Color
    duration: Duration
    easing: Easing = "linear"


Scalar: TypeAlias = FiniteFloat | Tween
Paint: TypeAlias = Color | ColorTween


def endpoints(value: Scalar) -> tuple[float, float]:
    """Return the extrema of a scalar or monotonic tween."""
    if isinstance(value, Tween):
        return value.from_value, value.to_value
    return value, value
