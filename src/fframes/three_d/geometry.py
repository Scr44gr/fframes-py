"""Immutable geometry recipes, built and shared by the native renderer."""

from math import pi
from typing import Annotated, Literal, Self, TypeAlias

from pydantic import ConfigDict, Field, TypeAdapter, model_validator, validate_call

from fframes import _native
from fframes.models import Model, Source
from fframes.three_d.types import IDENTITY, Matrix, Nonnegative, Number, Positive, Vec2, Vec3, Vec4

Segments: TypeAlias = Annotated[int, Field(ge=3, le=4096)]


class Geometry(Model):
    """Geometry-local transform and optional normal reconstruction."""

    transform: Matrix = IDENTITY
    normals: Literal["original", "flat", "smooth"] = "original"
    crease: Annotated[float, Field(ge=0, le=180, allow_inf_nan=False)] = 60.0


class Box(Geometry):
    """A cuboid centered at the origin."""

    kind: Literal["box"] = "box"
    size: tuple[Positive, Positive, Positive] = (1.0, 1.0, 1.0)
    radius: Nonnegative = 0.0
    segments: Annotated[int, Field(ge=1, le=128)] = 3

    @model_validator(mode="after")
    def check_radius(self) -> Self:
        """Do not silently clamp rounded corners to half the smallest side."""
        if self.radius > min(self.size) / 2:
            raise ValueError("radius cannot exceed half the smallest box dimension")
        return self


class Sphere(Geometry):
    """A UV sphere; angular ranges are in radians."""

    kind: Literal["sphere"] = "sphere"
    radius: Positive = 1.0
    segments: tuple[Segments, Segments] = (32, 24)
    theta: tuple[Nonnegative, Positive] = (0.0, pi)

    @model_validator(mode="after")
    def check_angles(self) -> Self:
        """Keep a partial sphere within its spherical coordinate domain."""
        if sum(self.theta) > pi + 1e-9:
            raise ValueError("theta start + length must be <= pi")
        return self


class Cylinder(Geometry):
    """A Y-axis cylinder, frustum or cone (top=0), with optional open ends."""

    kind: Literal["cylinder"] = "cylinder"
    top: Nonnegative = 1.0
    bottom: Nonnegative = 1.0
    height: Positive = 1.0
    segments: Segments = 32
    open: bool = False

    @model_validator(mode="after")
    def check_radii(self) -> Self:
        """Allow one zero radius for a cone, but reject two."""
        if self.top == self.bottom == 0:
            raise ValueError("at least one cylinder radius must be positive")
        return self


class Capsule(Geometry):
    """Two hemispheres separated by a Y-axis cylinder of the given length."""

    kind: Literal["capsule"] = "capsule"
    radius: Positive = 0.5
    length: Nonnegative = 1.0
    cap_segments: Segments = 8
    radial_segments: Segments = 24


class Torus(Geometry):
    """A ring in XY, optionally restricted to an arc in radians."""

    kind: Literal["torus"] = "torus"
    radius: Positive = 1.0
    tube: Positive = 0.25
    segments: tuple[Segments, Segments] = (16, 64)
    arc: Annotated[float, Field(gt=0, le=2 * pi, allow_inf_nan=False)] = 2 * pi


class Plane(Geometry):
    """XY has normalized top-left UVs; an XZ floor repeats textures per world unit."""

    kind: Literal["plane"] = "plane"
    size: tuple[Positive, Positive] = (1.0, 1.0)
    axis: Literal["xy", "xz"] = "xy"
    segments: tuple[Annotated[int, Field(ge=1, le=4096)], Annotated[int, Field(ge=1, le=4096)]] = (
        1,
        1,
    )


class Ring(Geometry):
    """An XY ring; inner=0 makes a filled disk."""

    kind: Literal["ring"] = "ring"
    inner: Nonnegative = 0.0
    outer: Positive = 1.0
    segments: Segments = 64

    @model_validator(mode="after")
    def check_radii(self) -> Self:
        """Reject an inverted or empty annulus."""
        if self.inner >= self.outer:
            raise ValueError("inner must be smaller than outer")
        return self


class Lathe(Geometry):
    """Revolve (radius, height) profile points around +Y."""

    kind: Literal["lathe"] = "lathe"
    points: Annotated[tuple[Vec2, ...], Field(min_length=2)]
    segments: Segments = 32

    @model_validator(mode="after")
    def check_profile(self) -> Self:
        """Reject negative radii or a profile without surface area."""
        if any(radius < 0 for radius, _ in self.points) or not any(r > 0 for r, _ in self.points):
            raise ValueError("lathe radii must be nonnegative, with at least one positive radius")
        if len(set(self.points)) < 2:
            raise ValueError("lathe needs at least two distinct profile points")
        return self


class Shape(Model):
    """A 2D polygon and its holes, used for extrusion."""

    outer: Annotated[tuple[Vec2, ...], Field(min_length=3)]
    holes: tuple[Annotated[tuple[Vec2, ...], Field(min_length=3)], ...] = ()


class GlyphShapes(Model):
    """Glyph-local outlines and baseline origin; whitespace has no shapes."""

    character: str
    origin: Vec2
    advance: Nonnegative
    shapes: tuple[Shape, ...]


_glyphs = TypeAdapter(tuple[GlyphShapes, ...])


@validate_call(config=ConfigDict(strict=True))
def text_shapes(
    font: Source,
    text: str,
    *,
    size: Positive = 1.0,
    letter_spacing: Number = 0.0,
) -> tuple[GlyphShapes, ...]:
    """Extract reusable outlines natively; extrude each shape to animate individual glyphs."""
    return _glyphs.validate_json(_native.text_shapes(str(font), text, size, letter_spacing))


class Extrude(Geometry):
    """Extrude a polygon along +Z, including holes and rounded bevels."""

    kind: Literal["extrude"] = "extrude"
    shape: Shape
    depth: Positive = 0.2
    bevel: Nonnegative = 0.0
    bevel_segments: Annotated[int, Field(ge=1, le=128)] = 3


class TextGeometry(Geometry):
    """Extruded font outlines; height is one em in scene units, without kerning."""

    kind: Literal["text"] = "text"
    text: str
    font: Source
    height: Positive = 1.0
    depth: Positive = 0.1
    bevel: Nonnegative = 0.0


class Icosahedron(Geometry):
    """A subdivided icosahedron projected onto a sphere."""

    kind: Literal["icosahedron"] = "icosahedron"
    radius: Positive = 1.0
    detail: Annotated[int, Field(ge=0, le=6)] = 0


class Tube(Geometry):
    """A circular tube following a sampled 3D path."""

    kind: Literal["tube"] = "tube"
    path: Annotated[tuple[Vec3, ...], Field(min_length=2)]
    radius: Positive = 0.1
    segments: Segments = 12


class MorphTarget(Model):
    """Per-vertex position and normal deltas."""

    name: str | None = None
    positions: tuple[Vec3, ...]
    normals: tuple[Vec3, ...] = ()


class SkinWeights(Model):
    """Four joint indices and weights per vertex, in the mesh skin's joint order."""

    joints: tuple[
        tuple[
            Annotated[int, Field(ge=0, le=65535)],
            Annotated[int, Field(ge=0, le=65535)],
            Annotated[int, Field(ge=0, le=65535)],
            Annotated[int, Field(ge=0, le=65535)],
        ],
        ...,
    ]
    weights: tuple[tuple[Nonnegative, Nonnegative, Nonnegative, Nonnegative], ...]

    @model_validator(mode="after")
    def check_normalized(self) -> Self:
        """Keep affine skin transforms normalized instead of silently shrinking vertices."""
        if any(abs(sum(weights) - 1) > 1e-5 for weights in self.weights):
            raise ValueError("skin weights must sum to 1 for each vertex")
        return self


class MeshGeometry(Geometry):
    """Indexed triangles; normals are computed when omitted. Buffers copy once at compilation."""

    kind: Literal["mesh"] = "mesh"
    positions: Annotated[tuple[Vec3, ...], Field(min_length=3)]
    indices: Annotated[tuple[Annotated[int, Field(ge=0, le=2**32 - 1)], ...], Field(min_length=3)]
    vertex_normals: tuple[Vec3, ...] = ()
    uvs: tuple[Vec2, ...] = ()
    colors: tuple[Vec4, ...] = ()
    skin: SkinWeights | None = None
    morph_targets: tuple[MorphTarget, ...] = ()

    @model_validator(mode="after")
    def check_buffers(self) -> Self:
        """Reject truncated triangles and mismatched attributes before native conversion."""
        count = len(self.positions)
        if len(self.indices) % 3 or max(self.indices) >= count:
            raise ValueError(
                "indices must contain complete triangles referencing existing vertices"
            )
        for name, size in (
            ("vertex_normals", len(self.vertex_normals)),
            ("uvs", len(self.uvs)),
            ("colors", len(self.colors)),
        ):
            if size not in (0, count):
                raise ValueError(f"{name} must be empty or have one value per vertex")
        if self.skin is not None and (
            len(self.skin.joints) != count or len(self.skin.weights) != count
        ):
            raise ValueError("skin joints and weights must have one entry per vertex")
        for target in self.morph_targets:
            if len(target.positions) != count or len(target.normals) not in (0, count):
                raise ValueError("morph target deltas must match the vertex count")
        return self


class STL(Geometry):
    """A binary or ASCII STL file; use normals='smooth' to weld its face normals."""

    kind: Literal["stl"] = "stl"
    source: Source


class Merged(Geometry):
    """Combine geometries once before rendering."""

    kind: Literal["merged"] = "merged"
    parts: Annotated[tuple["GeometryType", ...], Field(min_length=1)]


GeometryType: TypeAlias = Annotated[
    Box
    | Sphere
    | Cylinder
    | Capsule
    | Torus
    | Plane
    | Ring
    | Lathe
    | Extrude
    | TextGeometry
    | Icosahedron
    | Tube
    | MeshGeometry
    | STL
    | Merged,
    Field(discriminator="kind"),
]
Merged.model_rebuild()
