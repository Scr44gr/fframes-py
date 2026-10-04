"""Typed shader programs and uniforms shared by SVG and component scenes."""

from typing import Annotated, Literal, Self, TypeAlias

from pydantic import Field, model_validator

from fframes.media import ClipSource
from fframes.models import Model, Source
from fframes.values import Duration, Paint, Scalar, Start

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
    """A float2, float3 or float4 uniform with independently animated coordinates."""

    kind: Literal["vector"] = "vector"
    name: Name
    value: (
        tuple[Scalar, Scalar]
        | tuple[Scalar, Scalar, Scalar]
        | tuple[Scalar, Scalar, Scalar, Scalar]
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


class VideoUniform(ClipSource):
    """A synchronized child shader, transparent at EOF unless loop is enabled."""

    kind: Literal["video"] = "video"
    name: Name


Uniform: TypeAlias = Annotated[
    FloatUniform | ColorUniform | VectorUniform | IntUniform | ImageUniform | VideoUniform,
    Field(discriminator="kind"),
]


class Shader(Model):
    """A reusable SkSL or Shadertoy program, checked when the video compiles."""

    source: Annotated[str, Field(min_length=1, pattern=r"^[^\x00]+$")]
    language: Literal["sksl", "shadertoy"] = "sksl"
    uniforms: tuple[Uniform, ...] = ()
    time_offset: Start = 0.0

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
    start_at: Start = 0.0
    duration: Duration | None = None
