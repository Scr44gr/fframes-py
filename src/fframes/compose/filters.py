"""Typed SVG filter graphs, evaluated by the selected native renderer."""

from typing import Annotated, Literal, Self, TypeAlias

from pydantic import Field, model_validator

from fframes.models import Color, FiniteFloat, Model

Name: TypeAlias = Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]
Deviation: TypeAlias = Annotated[float, Field(ge=0, le=1e4, allow_inf_nan=False)]


class Blur(Model):
    """Blur an earlier result or SourceGraphic/SourceAlpha by sigma pixels."""

    kind: Literal["blur"] = "blur"
    result: Name
    source: Name = "SourceGraphic"
    sigma: tuple[Deviation, Deviation]


class Flood(Model):
    """Fill the filter region with a color, including its alpha channel."""

    kind: Literal["flood"] = "flood"
    result: Name
    color: Color


class Composite(Model):
    """Combine two earlier results using a Porter-Duff operation."""

    kind: Literal["composite"] = "composite"
    result: Name
    source: Name
    destination: Name
    operator: Literal["over", "in", "out", "atop", "xor"] = "over"


class Merge(Model):
    """Paint earlier results in order; repeated sources are allowed."""

    kind: Literal["merge"] = "merge"
    result: Name
    sources: Annotated[tuple[Name, ...], Field(min_length=1)]


Step: TypeAlias = Annotated[Blur | Flood | Composite | Merge, Field(discriminator="kind")]


class Filter(Model):
    """An ordered graph; region is x/y/width/height relative to the object's bounds."""

    steps: Annotated[tuple[Step, ...], Field(min_length=1)]
    region: tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat] = (-0.1, -0.1, 1.2, 1.2)
    units: Literal["bounds", "user"] = "bounds"
    color_space: Literal["linear", "srgb"] = "linear"

    @model_validator(mode="after")
    def check_graph(self) -> Self:
        """Require named prior inputs and a nonempty, finite filter region."""
        if self.region[2] <= 0 or self.region[3] <= 0:
            msg = "filter width and height must be positive"
            raise ValueError(msg)
        names = {"SourceGraphic", "SourceAlpha"}
        for step in self.steps:
            inputs: tuple[str, ...]
            match step:
                case Blur():
                    inputs = (step.source,)
                case Composite():
                    inputs = (step.source, step.destination)
                case Merge():
                    inputs = step.sources
                case Flood():
                    inputs = ()
            if step.result in names or not set(inputs) <= names:
                msg = "filter results must be unique and inputs must refer to prior results"
                raise ValueError(msg)
            names.add(step.result)
        return self
