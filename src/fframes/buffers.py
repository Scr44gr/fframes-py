"""Immutable binary media; payloads cross the native boundary outside JSON."""

from typing import Annotated, Literal, Self

from pydantic import Field, SerializationInfo, field_serializer, model_validator

from fframes.models import Index, Model, PositiveInt


class Buffers:
    """Private compilation context retaining distinct bytes objects once."""

    def __init__(self) -> None:
        """Collect shared payloads for one native compilation."""
        self.data: dict[str, bytes] = {}


class BinaryMedia(Model):
    """Retain immutable bytes; mutable arrays require an explicit bytes snapshot."""

    data: Annotated[bytes, Field(min_length=1)]

    @field_serializer("data")
    def reference(self, data: bytes, info: SerializationInfo[object]) -> str:
        """Transfer identity references without base64 encoding or expanding pixels."""
        context = info.context
        if not isinstance(context, Buffers):
            raise ValueError("binary media requires video or renderer compilation")
        key = str(id(data))
        context.data.setdefault(key, data)
        return key


class Pcm(BinaryMedia):
    """Interleaved float32 little-endian PCM; slices share the original bytes."""

    kind: Literal["pcm"] = "pcm"
    sample_rate: PositiveInt = 48_000
    channels: Literal[1, 2] = 2
    start: Index = 0
    end: Index | None = None

    @property
    def frames(self) -> int:
        """Return sample frames in this view, not individual channel values."""
        end = self.end if self.end is not None else len(self.data) // (4 * self.channels)
        return end - self.start

    @model_validator(mode="after")
    def check_data(self) -> Self:
        """Require complete sample frames and a nonempty view."""
        count, remainder = divmod(len(self.data), 4 * self.channels)
        end = self.end if self.end is not None else count
        if remainder or not 0 <= self.start < end <= count:
            raise ValueError(
                "PCM requires complete float32 frames and 0 <= start < end <= sample count"
            )
        return self

    def slice(self, start: int, end: int) -> "Pcm":
        """Select relative sample frames without copying; end is exclusive."""
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= self.frames:
            raise ValueError("PCM slice requires integer bounds with 0 <= start < end <= frames")
        return Pcm(
            data=self.data,
            sample_rate=self.sample_rate,
            channels=self.channels,
            start=self.start + start,
            end=self.start + end,
        )


class ImageBuffer(BinaryMedia):
    """Encoded image bytes, or straight RGBA8 when size is specified."""

    kind: Literal["image_buffer"] = "image_buffer"
    size: tuple[PositiveInt, PositiveInt] | None = None

    @model_validator(mode="after")
    def check_data(self) -> Self:
        """Check raw pixel storage without reading or copying the buffer."""
        if self.size is not None and len(self.data) != self.size[0] * self.size[1] * 4:
            raise ValueError("image buffer requires width * height * 4 RGBA8 bytes")
        return self


class VideoFrames(BinaryMedia):
    """Contiguous straight RGBA8 frames, sampled on the source clock."""

    kind: Literal["video_frames"] = "video_frames"
    size: tuple[PositiveInt, PositiveInt]
    fps: PositiveInt = 30

    @model_validator(mode="after")
    def check_data(self) -> Self:
        """Require complete frames without expanding them into Python objects."""
        if len(self.data) % (self.size[0] * self.size[1] * 4):
            raise ValueError("video buffer length must be a multiple of width * height * 4")
        return self
