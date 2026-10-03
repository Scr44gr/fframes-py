"""Typed shader programs and uniforms shared by SVG and component scenes."""

from typing import Annotated, Literal, Self, TypeAlias

from pydantic import Field, model_validator

from fframes.models import FiniteFloat, Model, Source
from fframes.values import Paint, Scalar

Name: TypeAlias = Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]


class FloatUniform(Model):
    """A float uniform, optionally animated on the layer's local clock."""

    kind: Literal["float"] = "float"
    name: Name
    value: Scalar


class ColorUniform(Model):
    """An RGBA color bound to a float4/half4 uniform in the range 0-1."""

    kind: Literal["color"] = "color"
    name: Name
    value: Paint


class VectorUniform(Model):
    """A float2, float3 or float4 uniform."""

    kind: Literal["vector"] = "vector"
    name: Name
    value: (
        tuple[FiniteFloat, FiniteFloat]
        | tuple[FiniteFloat, FiniteFloat, FiniteFloat]
        | tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat]
    )


class IntUniform(Model):
    """A signed 32-bit integer uniform."""

    kind: Literal["int"] = "int"
    name: Name
    value: Annotated[int, Field(ge=-(2**31), le=2**31 - 1)]


class ImageUniform(Model):
    """An owned raster image sampled by a child `uniform shader`."""

    kind: Literal["image"] = "image"
    name: Name
    source: Source


Uniform: TypeAlias = Annotated[
    FloatUniform | ColorUniform | VectorUniform | IntUniform | ImageUniform,
    Field(discriminator="kind"),
]


class Shader(Model):
    """A reusable SkSL or Shadertoy program, checked when the video compiles."""

    source: Annotated[str, Field(min_length=1, pattern=r"^[^\x00]+$")]
    language: Literal["sksl", "shadertoy"] = "sksl"
    uniforms: tuple[Uniform, ...] = ()

    @model_validator(mode="after")
    def check_names(self) -> Self:
        """Reject duplicate bindings and built-ins managed by the renderer."""
        names = [uniform.name for uniform in self.uniforms]
        if len(names) != len(set(names)) or set(names) & {
            "iResolution",
            "iTime",
            "iTimeDelta",
            "iFrame",
        }:
            msg = "uniform names must be unique and cannot override renderer built-ins"
            raise ValueError(msg)
        return self


class ShaderBinding(Model):
    """Make a shader available to SVG images through `href='shader:name'`."""

    name: Name
    shader: Shader
