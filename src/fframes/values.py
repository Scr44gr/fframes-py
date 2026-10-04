"""Scalar animation descriptions evaluated by Rust."""

from math import exp, isfinite, pi, sqrt
from typing import Annotated, Self, TypeAlias

from pydantic import Field, model_validator

from fframes.models import Color, Easing, FiniteFloat, Model, PositiveInt, Spring

Duration: TypeAlias = Annotated[float, Field(gt=0, le=86400, allow_inf_nan=False)]
Start: TypeAlias = Annotated[float, Field(ge=0, le=86400, allow_inf_nan=False)]


class Tween(Model):
    """Interpolate in local seconds, holding endpoints outside the interval."""

    from_value: FiniteFloat
    to_value: FiniteFloat
    duration: Duration
    easing: Easing = "linear"
    start_at: Start = 0.0

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
    start_at: Start = 0.0


class Samples(Model):
    """Hold precomputed values at a fixed rate on the local clock, then hold the last."""

    values: Annotated[tuple[FiniteFloat, ...], Field(min_length=1)]
    fps: PositiveInt


class ColorSamples(Model):
    """Hold sampled RGBA colors on the local clock without interpolating between them."""

    values: Annotated[tuple[Color, ...], Field(min_length=1)]
    fps: PositiveInt


Scalar: TypeAlias = FiniteFloat | Tween | Samples
Paint: TypeAlias = Color | ColorTween | ColorSamples


def endpoints(value: Scalar) -> tuple[float, float]:
    """Bound a scalar's full range, including an underdamped spring's overshoot."""
    if isinstance(value, Samples):
        return min(value.values), max(value.values)
    if isinstance(value, Tween):
        a, b = value.from_value, value.to_value
        if isinstance(value.easing, Spring):
            spring = value.easing
            damping = spring.damping / (2 * sqrt(spring.stiffness * spring.mass))
            if damping < 1:
                b += (b - a) * exp(-damping * pi / sqrt(1 - damping * damping))
        return min(a, b), max(a, b)
    return value, value
