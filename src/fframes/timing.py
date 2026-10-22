"""Named timeline ranges and upstream frame/time selectors."""

from functools import cached_property
from typing import Annotated, Self

from pydantic import ConfigDict, Field, model_validator, validate_call

from fframes import _native
from fframes.inspection import NativeVideo
from fframes.models import Index, Model, PositiveInt


class SceneRange(Model):
    """A named half-open frame interval; repeated names and overlaps are allowed."""

    name: Annotated[str, Field(min_length=1)]
    frames: tuple[Index, Index]

    @model_validator(mode="after")
    def check_interval(self) -> Self:
        """Require at least one frame."""
        if self.frames[0] >= self.frames[1]:
            raise ValueError("scene frames require start < end")
        return self


class TimelineIndex(Model):
    """Resolve upstream time syntax against a video's named scenes."""

    fps: PositiveInt
    duration_in_frames: PositiveInt
    scenes: tuple[SceneRange, ...] = ()

    @model_validator(mode="after")
    def check_scenes(self) -> Self:
        """Reject scenes extending beyond the video."""
        if any(scene.frames[1] > self.duration_in_frames for scene in self.scenes):
            raise ValueError("scene frames must lie within duration_in_frames")
        return self

    @cached_property
    def native(self) -> _native.TimelineIndex:
        """Compile the immutable index once."""
        return _native.TimelineIndex(self.model_dump_json())

    @validate_call(config=ConfigDict(strict=True))
    def resolve_frame(self, spec: Annotated[str, Field(min_length=1)]) -> int:
        """Resolve a frame, timestamp, percentage or scene-relative position."""
        return self.native.resolve_frame(spec)

    @validate_call(config=ConfigDict(strict=True))
    def resolve_range(self, spec: Annotated[str, Field(min_length=1)]) -> tuple[int, int]:
        """Resolve an end-exclusive range; upstream clamps it to the timeline."""
        return self.native.resolve_range(spec)

    @validate_call(config=ConfigDict(strict=True))
    def scenes_at(self, frame: Index) -> tuple[SceneRange, ...]:
        """Return every scene visible at a frame, preserving declaration order."""
        return tuple(self.scenes[i] for i in self.native.scenes_at(frame))


@validate_call(config=ConfigDict(strict=True, arbitrary_types_allowed=True))
def inspect_timeline(video: NativeVideo) -> TimelineIndex:
    """Read compiled scene names, overlaps and frame ranges without rendering."""
    return TimelineIndex.model_validate_json(_native.inspect_timeline(video))
