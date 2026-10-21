"""Named animation clips using upstream glTF interpolation rules."""

from itertools import pairwise
from typing import Annotated, Literal, Self, TypeAlias

from pydantic import Field, model_validator

from fframes.models import Model
from fframes.three_d.types import Coordinate, Number, Quaternion, UnitValue, Vec3
from fframes.values import Duration, Scalar, Start


class Playback(Model):
    """Play a named clip. time=None uses scene time * speed + offset."""

    name: str
    time: Scalar | None = None
    speed: Coordinate = 1.0
    offset: Coordinate = 0.0
    weight: UnitValue = 1.0
    loop: bool = True

    @model_validator(mode="after")
    def check_clock(self) -> Self:
        """Reject clock settings that an explicit time would replace."""
        if self.time is not None and (self.speed != 1.0 or self.offset != 0.0):
            raise ValueError("time replaces speed and offset; provide one clock definition")
        return self


class Keyframes(Model):
    """Keyframe times in seconds; cubic_spline stores in tangent, value, out tangent."""

    node: str
    times: Annotated[tuple[Start, ...], Field(min_length=1)]
    interpolation: Literal["step", "linear", "cubic_spline"] = "linear"

    @model_validator(mode="after")
    def check_times(self) -> Self:
        """Require strictly increasing sample times."""
        if any(a >= b for a, b in pairwise(self.times)):
            raise ValueError("keyframe times must be strictly increasing")
        return self

    def _check_count(self, count: int) -> None:
        expected = len(self.times) * (3 if self.interpolation == "cubic_spline" else 1)
        if count != expected:
            raise ValueError(f"{self.interpolation} requires {expected} values for these times")


class VectorKeyframes(Keyframes):
    """Three-dimensional translation or scale values."""

    values: tuple[Vec3, ...]

    @model_validator(mode="after")
    def check_count(self) -> Self:
        """Validate the value/tangent count."""
        self._check_count(len(self.values))
        return self


class Translation(VectorKeyframes):
    """Animate a node's local position."""

    kind: Literal["translation"] = "translation"


class Scaling(VectorKeyframes):
    """Animate scale; negative values mirror geometry, zero is singular."""

    kind: Literal["scale"] = "scale"

    @model_validator(mode="after")
    def check_scale(self) -> Self:
        """Reject zero scale keyframes before native rendering."""
        values = self.values[1::3] if self.interpolation == "cubic_spline" else self.values
        if any(v == 0 for vector in values for v in vector):
            raise ValueError("scale keyframes must be nonzero")
        return self


class Rotation(Keyframes):
    """Quaternion keyframes (x, y, z, w); linear interpolation uses spherical interpolation."""

    kind: Literal["rotation"] = "rotation"
    values: tuple[Quaternion, ...]

    @model_validator(mode="after")
    def check_quaternions(self) -> Self:
        """Validate nonzero orientation values and the required tangent count."""
        self._check_count(len(self.values))
        values = self.values[1::3] if self.interpolation == "cubic_spline" else self.values
        if any(sum(v * v for v in q) < 1e-12 for q in values):
            raise ValueError("rotation keyframes must be nonzero quaternions")
        return self


class MorphWeights(Keyframes):
    """One weight per morph target at each keyframe."""

    kind: Literal["weights"] = "weights"
    values: Annotated[
        tuple[Annotated[tuple[Number, ...], Field(min_length=1)], ...], Field(min_length=1)
    ]

    @model_validator(mode="after")
    def check_targets(self) -> Self:
        """Keep target count consistent for all values and tangents."""
        self._check_count(len(self.values))
        if len({len(value) for value in self.values}) != 1:
            raise ValueError("every morph keyframe must have the same target count")
        return self


Channel: TypeAlias = Annotated[
    Translation | Scaling | Rotation | MorphWeights, Field(discriminator="kind")
]


class Animation(Playback):
    """A reusable clip applied after base node transforms, before model pose overrides."""

    duration: Duration
    channels: Annotated[tuple[Channel, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def check_duration(self) -> Self:
        """Prevent clip duration from silently cutting off keyframes."""
        if any(channel.times[-1] > self.duration for channel in self.channels):
            raise ValueError("animation duration must include every channel's last keyframe")
        targets = [(channel.node, channel.kind) for channel in self.channels]
        if len(set(targets)) != len(targets):
            raise ValueError("each animation may have only one channel per node and property")
        return self
