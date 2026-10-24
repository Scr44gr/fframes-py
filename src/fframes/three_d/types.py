"""Validated coordinates shared by the 3D scene descriptions."""

from typing import Annotated, TypeAlias

from pydantic import AfterValidator, Field

from fframes.models import FiniteFloat, Model, PositiveInt
from fframes.values import ColorSamples, ColorTween, Paint, Samples, Scalar, endpoints

Number: TypeAlias = Annotated[float, Field(ge=-1e7, le=1e7, allow_inf_nan=False)]
Positive: TypeAlias = Annotated[float, Field(gt=0, le=1e7, allow_inf_nan=False)]
Nonnegative: TypeAlias = Annotated[float, Field(ge=0, le=1e7, allow_inf_nan=False)]
Unit: TypeAlias = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Vec2: TypeAlias = tuple[Number, Number]
Vec3: TypeAlias = tuple[Number, Number, Number]
Vec4: TypeAlias = tuple[Number, Number, Number, Number]
MatrixValues: TypeAlias = tuple[
    Number,
    Number,
    Number,
    Number,
    Number,
    Number,
    Number,
    Number,
    Number,
    Number,
    Number,
    Number,
    Number,
    Number,
    Number,
    Number,
]


def _affine(value: MatrixValues) -> MatrixValues:
    if (value[3], value[7], value[11], value[15]) != (0, 0, 0, 1):
        raise ValueError("transform must be an affine, column-major 4x4 matrix")
    a, b, c, d, e, f, g, h, i = (value[j] for j in (0, 4, 8, 1, 5, 9, 2, 6, 10))
    if abs(a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)) < 1e-12:
        raise ValueError("transform must be invertible; zero scale is singular")
    return value


Matrix: TypeAlias = Annotated[MatrixValues, AfterValidator(_affine)]
IDENTITY: Matrix = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)


def _coordinate(value: Scalar) -> Scalar:
    low, high = endpoints(value)
    if low < -1e7 or high > 1e7:
        raise ValueError("3D coordinates must stay between -10000000 and 10000000")
    return value


def _nonnegative(value: Scalar) -> Scalar:
    low, high = endpoints(value)
    if low < 0 or high > 1e7:
        raise ValueError("value must stay between 0 and 10000000 throughout its animation")
    return value


def _positive(value: Scalar) -> Scalar:
    if endpoints(value)[0] <= 0:
        raise ValueError("value must stay strictly positive throughout its animation")
    return _nonnegative(value)


def _unit(value: Scalar) -> Scalar:
    low, high = endpoints(value)
    if low < 0 or high > 1:
        raise ValueError("value must stay between 0 and 1 throughout its animation")
    return value


Coordinate: TypeAlias = Annotated[Scalar, AfterValidator(_coordinate)]
PositiveValue: TypeAlias = Annotated[Scalar, AfterValidator(_positive)]
NonnegativeValue: TypeAlias = Annotated[Scalar, AfterValidator(_nonnegative)]
UnitValue: TypeAlias = Annotated[Scalar, AfterValidator(_unit)]
Vector: TypeAlias = tuple[Coordinate, Coordinate, Coordinate]


def _direction(value: Vector) -> Vector:
    if value == (0, 0, 0):
        raise ValueError("direction must be nonzero")
    return value


Direction: TypeAlias = Annotated[Vector, AfterValidator(_direction)]


def _static_direction(value: Vec3) -> Vec3:
    if value == (0, 0, 0):
        raise ValueError("direction must be nonzero")
    return value


StaticDirection: TypeAlias = Annotated[Vec3, AfterValidator(_static_direction)]


def _nonzero(value: Scalar) -> Scalar:
    _coordinate(value)
    if isinstance(value, Samples):
        invalid = 0 in value.values
    else:
        low, high = endpoints(value)
        invalid = low <= 0 <= high
    if invalid:
        raise ValueError("scale must stay nonzero; use visible=False to hide a node")
    return value


NonzeroValue: TypeAlias = Annotated[Scalar, AfterValidator(_nonzero)]
Scale: TypeAlias = tuple[NonzeroValue, NonzeroValue, NonzeroValue]


def _opaque(value: Paint) -> Paint:
    colors: tuple[str, ...]
    if isinstance(value, ColorTween):
        colors = (value.from_value, value.to_value)
    elif isinstance(value, ColorSamples):
        colors = value.values
    else:
        colors = (value,)
    if any(len(color) == 9 and color[-2:].lower() != "ff" for color in colors):
        raise ValueError("3D RGB colors cannot carry alpha; set material or particle opacity")
    return value


RGB: TypeAlias = (
    Annotated[Paint, AfterValidator(_opaque)] | tuple[Nonnegative, Nonnegative, Nonnegative]
)
Quaternion: TypeAlias = tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat]


class VisibilityFrames(Model):
    """Boolean visibility samples on a local frame clock, holding the last value."""

    values: Annotated[tuple[bool, ...], Field(min_length=1)]
    fps: PositiveInt
