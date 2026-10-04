"""Reusable fills and outlines, resolved to native paint servers at compilation."""

from itertools import pairwise
from typing import Annotated, Literal, Self, TypeAlias

from pydantic import Field, model_validator

from fframes.models import Color, FiniteFloat, Length, Model, Size, Source
from fframes.values import Paint, Scalar

Matrix: TypeAlias = tuple[Scalar, Scalar, Scalar, Scalar, Scalar, Scalar]


class Stop(Model):
    """One gradient color at a fractional offset; alpha is part of the hex color."""

    offset: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    color: Color


class Gradient(Model):
    """Shared coordinate space, spread and ordered colors for gradients."""

    stops: Annotated[tuple[Stop, ...], Field(min_length=2)]
    units: Literal["bounds", "user"] = "bounds"
    spread: Literal["pad", "reflect", "repeat"] = "pad"
    matrix: Matrix | None = None

    @model_validator(mode="after")
    def check_order(self) -> Self:
        """Allow sharp transitions, but require explicit ascending stop order."""
        if any(a.offset > b.offset for a, b in pairwise(self.stops)):
            raise ValueError("gradient stops must have ascending offsets")
        return self


class LinearGradient(Gradient):
    """Interpolate colors between two points in bounds fractions or local pixels."""

    kind: Literal["linear_gradient"] = "linear_gradient"
    start: tuple[FiniteFloat, FiniteFloat] = (0.0, 0.0)
    end: tuple[FiniteFloat, FiniteFloat] = (1.0, 0.0)


class RadialGradient(Gradient):
    """Interpolate outward from a focal point to a circle."""

    kind: Literal["radial_gradient"] = "radial_gradient"
    center: tuple[FiniteFloat, FiniteFloat] = (0.5, 0.5)
    radius: Length = 0.5
    focus: tuple[FiniteFloat, FiniteFloat] | None = None


class Pattern(Model):
    """Repeat a local raster image in pixel-sized tiles, with an optional transform."""

    kind: Literal["pattern"] = "pattern"
    source: Source
    size: Size
    matrix: Matrix | None = None


Brush: TypeAlias = Paint | LinearGradient | RadialGradient | Pattern
