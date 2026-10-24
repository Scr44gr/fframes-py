"""Typed SVG filter graphs, evaluated by the selected native renderer."""

from typing import Annotated, Literal, Self, TypeAlias

from pydantic import Field, model_validator

from fframes.buffers import ImageBuffer
from fframes.models import Color, FiniteFloat, Model, PositiveInt, Source

Name: TypeAlias = Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]
Deviation: TypeAlias = Annotated[float, Field(ge=0, le=1e4, allow_inf_nan=False)]
Row: TypeAlias = tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat]
Region: TypeAlias = tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat]
BlendMode: TypeAlias = Literal[
    "normal",
    "multiply",
    "screen",
    "overlay",
    "darken",
    "lighten",
    "color-dodge",
    "color-burn",
    "hard-light",
    "soft-light",
    "difference",
    "exclusion",
    "hue",
    "saturation",
    "color",
    "luminosity",
]


class Primitive(Model):
    """Named filter output with an optional local-pixel subregion."""

    result: Name
    region: Region | None = None

    @model_validator(mode="after")
    def check_region(self) -> Self:
        """Reject empty subregions instead of silently dropping a primitive."""
        if self.region is not None and (self.region[2] <= 0 or self.region[3] <= 0):
            raise ValueError("filter subregion width and height must be positive")
        return self


class Blur(Primitive):
    """Blur an earlier result or SourceGraphic/SourceAlpha by sigma pixels."""

    kind: Literal["blur"] = "blur"
    source: Name = "SourceGraphic"
    sigma: tuple[Deviation, Deviation]


class Flood(Primitive):
    """Fill the filter region with a color, including its alpha channel."""

    kind: Literal["flood"] = "flood"
    color: Color


class Offset(Primitive):
    """Translate a filter input by local pixels."""

    kind: Literal["offset"] = "offset"
    source: Name = "SourceGraphic"
    dx: FiniteFloat = 0.0
    dy: FiniteFloat = 0.0


class ColorMatrix(Primitive):
    """Transform RGBA using four rows of five coefficients, including a bias column."""

    kind: Literal["colormatrix"] = "colormatrix"
    source: Name = "SourceGraphic"
    values: tuple[Row, Row, Row, Row]


class Composite(Primitive):
    """Combine two earlier results using a Porter-Duff operation."""

    kind: Literal["composite"] = "composite"
    source: Name
    destination: Name
    operator: Literal["over", "in", "out", "atop", "xor", "arithmetic"] = "over"
    coefficients: tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat] | None = None

    @model_validator(mode="after")
    def check_operator(self) -> Self:
        """Arithmetic uses k1*i1*i2 + k2*i1 + k3*i2 + k4."""
        if (self.operator == "arithmetic") != (self.coefficients is not None):
            raise ValueError("coefficients must be provided exactly when operator='arithmetic'")
        return self


class Merge(Primitive):
    """Paint earlier results in order; repeated sources are allowed."""

    kind: Literal["merge"] = "merge"
    sources: Annotated[tuple[Name, ...], Field(min_length=1)]


class Blend(Primitive):
    """Blend two filter inputs using a CSS blend mode."""

    kind: Literal["blend"] = "blend"
    source: Name
    destination: Name
    mode: BlendMode = "normal"


class DisplacementMap(Primitive):
    """Displace source pixels using channels from another filter result."""

    kind: Literal["displacement"] = "displacement"
    source: Name = "SourceGraphic"
    destination: Name
    scale: FiniteFloat = 0.0
    x_channel: Literal["R", "G", "B", "A"] = "A"
    y_channel: Literal["R", "G", "B", "A"] = "A"


class Morphology(Primitive):
    """Expand or erode a shape by positive x/y pixel radii."""

    kind: Literal["morphology"] = "morphology"
    source: Name = "SourceGraphic"
    operator: Literal["erode", "dilate"] = "erode"
    radius: tuple[Annotated[float, Field(gt=0, le=1e4)], Annotated[float, Field(gt=0, le=1e4)]]


class Turbulence(Primitive):
    """Seeded procedural noise, optionally seamless across the filter region."""

    kind: Literal["turbulence"] = "turbulence"
    frequency: tuple[Deviation, Deviation] = (0.05, 0.05)
    octaves: Annotated[int, Field(ge=1, le=16)] = 1
    seed: Annotated[int, Field(ge=-(2**24), le=2**24)] = 0
    noise: Literal["fractalNoise", "turbulence"] = "turbulence"
    stitch: bool = False


class Tile(Primitive):
    """Repeat an input's subregion to fill this primitive's region."""

    kind: Literal["tile"] = "tile"
    source: Name


class ConvolveMatrix(Primitive):
    """Apply a row-major convolution kernel with explicit edge handling."""

    kind: Literal["convolve"] = "convolve"
    source: Name = "SourceGraphic"
    order: tuple[PositiveInt, PositiveInt]
    kernel: tuple[FiniteFloat, ...]
    divisor: FiniteFloat | None = None
    bias: FiniteFloat = 0.0
    target: tuple[Annotated[int, Field(ge=0)], Annotated[int, Field(ge=0)]] | None = None
    edge: Literal["duplicate", "wrap", "none"] = "duplicate"
    preserve_alpha: bool = False

    @model_validator(mode="after")
    def check_kernel(self) -> Self:
        """Require a complete kernel and a target inside it."""
        if len(self.kernel) != self.order[0] * self.order[1]:
            raise ValueError("kernel length must equal order[0] * order[1]")
        if self.divisor == 0:
            raise ValueError("divisor must be nonzero; None uses the kernel sum or 1")
        if self.target is not None and any(
            t >= n for t, n in zip(self.target, self.order, strict=True)
        ):
            raise ValueError("target must lie inside the kernel order")
        return self


class TableTransfer(Model):
    """Interpolated or discrete channel lookup table; values are clamped to 0-1."""

    kind: Literal["table", "discrete"] = "table"
    values: Annotated[tuple[FiniteFloat, ...], Field(min_length=1)]


class LinearTransfer(Model):
    """Apply slope * channel + intercept."""

    kind: Literal["linear"] = "linear"
    slope: FiniteFloat = 1.0
    intercept: FiniteFloat = 0.0


class GammaTransfer(Model):
    """Apply amplitude * channel**exponent + offset."""

    kind: Literal["gamma"] = "gamma"
    amplitude: FiniteFloat = 1.0
    exponent: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 1.0
    offset: FiniteFloat = 0.0


Transfer: TypeAlias = Annotated[
    TableTransfer | LinearTransfer | GammaTransfer, Field(discriminator="kind")
]


class ComponentTransfer(Primitive):
    """Apply independent RGBA transfer functions; None leaves a channel unchanged."""

    kind: Literal["transfer"] = "transfer"
    source: Name = "SourceGraphic"
    red: Transfer | None = None
    green: Transfer | None = None
    blue: Transfer | None = None
    alpha: Transfer | None = None


class DistantLight(Model):
    """A filter light with azimuth and elevation in degrees."""

    kind: Literal["distant"] = "distant"
    azimuth: FiniteFloat = 0.0
    elevation: FiniteFloat = 45.0


class PointLight(Model):
    """A filter light at x/y/z in local pixel coordinates."""

    kind: Literal["point"] = "point"
    position: tuple[FiniteFloat, FiniteFloat, FiniteFloat]


class SpotLight(Model):
    """A filter light aimed at a point, optionally limited by a cone in degrees."""

    kind: Literal["spot"] = "spot"
    position: tuple[FiniteFloat, FiniteFloat, FiniteFloat]
    target: tuple[FiniteFloat, FiniteFloat, FiniteFloat] = (0.0, 0.0, 0.0)
    exponent: Deviation = 1.0
    cone: Annotated[float, Field(gt=0, le=90, allow_inf_nan=False)] | None = None


LightSource: TypeAlias = Annotated[
    DistantLight | PointLight | SpotLight, Field(discriminator="kind")
]


class Lighting(Primitive):
    """Shade the alpha height field with diffuse or specular lighting."""

    kind: Literal["lighting"] = "lighting"
    source: Name = "SourceAlpha"
    light: LightSource
    mode: Literal["diffuse", "specular"] = "diffuse"
    color: Color = "#ffffff"
    surface_scale: FiniteFloat = 1.0
    constant: Deviation = 1.0
    exponent: Annotated[float, Field(ge=1, le=128, allow_inf_nan=False)] | None = None

    @model_validator(mode="after")
    def check_exponent(self) -> Self:
        """Specular lighting requires its exponent; diffuse lighting does not use it."""
        if (self.mode == "specular") != (self.exponent is not None):
            raise ValueError("exponent must be provided exactly when mode='specular'")
        return self


class FilterImage(Primitive):
    """Load an image into the filter graph, fitting its primitive region."""

    kind: Literal["image"] = "image"
    source: Source | ImageBuffer
    fit: Literal["contain", "cover", "stretch"] = "contain"


Step: TypeAlias = Annotated[
    Blur
    | Flood
    | Offset
    | ColorMatrix
    | Composite
    | Merge
    | Blend
    | DisplacementMap
    | Morphology
    | Turbulence
    | Tile
    | ConvolveMatrix
    | ComponentTransfer
    | Lighting
    | FilterImage,
    Field(discriminator="kind"),
]


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
                case (
                    Blur()
                    | Offset()
                    | ColorMatrix()
                    | Morphology()
                    | Tile()
                    | ConvolveMatrix()
                    | ComponentTransfer()
                    | Lighting()
                ):
                    inputs = (step.source,)
                case Composite() | Blend() | DisplacementMap():
                    inputs = (step.source, step.destination)
                case Merge():
                    inputs = step.sources
                case Flood() | Turbulence() | FilterImage():
                    inputs = ()
            if step.result in names or not set(inputs) <= names:
                msg = "filter results must be unique and inputs must refer to prior results"
                raise ValueError(msg)
            names.add(step.result)
        return self
