"""Reusable components, local placement and immutable visual primitives."""

from abc import ABC, abstractmethod
from typing import Annotated, Literal, Self, TypeAlias

from pydantic import Field, model_validator

from fframes.compose.animation import Duration, Paint, Scalar, endpoints
from fframes.compose.filters import Filter
from fframes.models import FiniteFloat, Model, Seconds
from fframes.shaders import Shader

Length: TypeAlias = Annotated[float, Field(gt=0, le=1e7, allow_inf_nan=False)]
Size: TypeAlias = tuple[Length, Length]


class Position(Model):
    """Place the untransformed bounds in the parent's local pixel coordinates."""

    x: Scalar | Literal["left", "center", "right"] = 0.0
    y: Scalar | Literal["top", "center", "bottom"] = 0.0


class Mask(Model):
    """Clip a visual or group to a local rectangle with optional rounded corners."""

    size: Size
    radius: Annotated[float, Field(ge=0, le=1e7, allow_inf_nan=False)] = 0.0
    position: tuple[FiniteFloat, FiniteFloat] = (0.0, 0.0)


class Item(Model):
    """Content that can appear inside a composition."""

    def at(self, start_at: float, *, duration: float | None = None) -> "Clip":
        """Place this same content in a new interval without mutating it."""
        return Clip(content=self, start_at=start_at, duration=duration)


class Clip(Item):
    """A half-open interval relative to its parent; duration caps the content."""

    content: Item
    start_at: Seconds = 0.0
    duration: Duration | None = None


class Component(Item, ABC):
    """Subclass with typed Pydantic fields and expand once per compilation."""

    @abstractmethod
    def compose(self) -> "Composition":
        """Describe this component using existing items, without frame callbacks."""


class Visual(Item):
    """Placement and transforms shared by graphics and visual groups."""

    position: Position = Position()
    opacity: Scalar = 1.0
    rotation: Scalar = 0.0
    scale: Scalar = 1.0
    origin: tuple[FiniteFloat, FiniteFloat] | None = None
    mask: Mask | None = None
    filter: Filter | None = None

    @model_validator(mode="after")
    def check_transform(self) -> Self:
        """Validate the entire animated range, not just its initial value."""
        if not all(0 <= value <= 1 for value in endpoints(self.opacity)):
            msg = "opacity must stay between 0 and 1"
            raise ValueError(msg)
        if not all(0 < value <= 1e4 for value in endpoints(self.scale)):
            msg = "scale must stay between 0 (exclusive) and 10000"
            raise ValueError(msg)
        if self.origin is not None and any(abs(value) > 1e7 for value in self.origin):
            msg = "origin coordinates must stay between -10000000 and 10000000"
            raise ValueError(msg)
        return self


class Composition(Visual):
    """Layer children in order, using a local clock and an optional canvas size.

    A missing duration or size inherits the enclosing interval or canvas. Size
    defines layout coordinates, not a clipping mask. Rotation and scale use the
    center of these bounds; group opacity applies after compositing its children.
    """

    children: tuple[Item, ...] = ()
    duration: Duration | None = None
    size: Size | None = None


class Stroke(Model):
    """An outline centered on the shape boundary."""

    color: Paint
    width: Length = 1.0


class Shape(Visual):
    """Shared paint for vector geometry."""

    fill: Paint | None = "#000000"
    stroke: Stroke | None = None


class Rectangle(Shape):
    """A rectangle with an optional corner radius."""

    kind: Literal["rectangle"] = "rectangle"
    size: Size
    radius: Annotated[float, Field(ge=0, le=1e7, allow_inf_nan=False)] = 0.0


class Circle(Shape):
    """A circle whose local bounds start at (0, 0)."""

    kind: Literal["circle"] = "circle"
    radius: Length


class ShaderLayer(Visual):
    """Draw a shared shader program in a rectangle using the local frame clock."""

    kind: Literal["shader"] = "shader"
    shader: Shader
    size: Size


class TextTemplate(Model):
    """Format {frame} and {seconds:.2f} in Rust using the component's local clock."""

    template: Annotated[
        str,
        Field(pattern=r"^(?:[^{}\r\n\x00]|\{\{|\}\}|\{frame\}|\{seconds:\.[0-9]f\})+$"),
    ]


Line: TypeAlias = Annotated[str, Field(min_length=1, pattern=r"^[^\r\n\x00]+$")]


class TextFrames(Model):
    """Precomputed lines, one per local frame; hold the last line after the sequence."""

    frames: Annotated[tuple[Line, ...], Field(min_length=1)]


class Text(Visual):
    """Single-line text positioned using its shaped visual bounds."""

    kind: Literal["text"] = "text"
    content: Line | TextTemplate | TextFrames
    fill: Paint = "#000000"
    font_family: Annotated[str, Field(min_length=1)] = "sans-serif"
    font_size: Length = 32.0
    font_weight: Annotated[int, Field(ge=100, le=900)] = 400
    anchor: Literal["bounds", "baseline"] = "bounds"
    letter_spacing: FiniteFloat = 0.0

    @model_validator(mode="after")
    def check_template_anchor(self) -> Self:
        """Use explicit baseline coordinates for text whose visual bounds change."""
        if not isinstance(self.content, str) and (
            self.anchor != "baseline"
            or isinstance(self.position.x, str)
            or isinstance(self.position.y, str)
        ):
            msg = "text templates require anchor='baseline' and numeric positions"
            raise ValueError(msg)
        return self


class MoveTo(Model):
    """Start a path subcontour at an absolute coordinate."""

    kind: Literal["move"] = "move"
    x: FiniteFloat
    y: FiniteFloat


class LineTo(Model):
    """Draw a straight segment to an absolute coordinate."""

    kind: Literal["line"] = "line"
    x: FiniteFloat
    y: FiniteFloat


class CubicTo(Model):
    """Draw a cubic Bézier using two control points and an endpoint."""

    kind: Literal["cubic"] = "cubic"
    control1: tuple[FiniteFloat, FiniteFloat]
    control2: tuple[FiniteFloat, FiniteFloat]
    end: tuple[FiniteFloat, FiniteFloat]


class Close(Model):
    """Close the current subcontour."""

    kind: Literal["close"] = "close"


Segment: TypeAlias = Annotated[MoveTo | LineTo | CubicTo | Close, Field(discriminator="kind")]


class VectorPath(Shape):
    """Typed path segments with explicit local layout bounds."""

    kind: Literal["path"] = "path"
    size: Size
    segments: Annotated[tuple[Segment, ...], Field(min_length=2)]

    @model_validator(mode="after")
    def check_start(self) -> Self:
        """Reject paths that have no initial current point."""
        if not isinstance(self.segments[0], MoveTo):
            msg = "a path must begin with MoveTo"
            raise ValueError(msg)
        return self
