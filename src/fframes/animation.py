"""Scalar animation backed by the upstream Rust timeline."""

from collections.abc import Iterable
from functools import cached_property

from pydantic import ConfigDict, validate_call

from fframes import _native
from fframes._native import Animation
from fframes.models import Index, Keyframes, Model, PositiveInt


@validate_call(config=ConfigDict(strict=True))
def compile_animation(keyframes: Keyframes) -> Animation:
    """Prepare the upstream keyframe animation once for scalar or batch sampling."""
    return _native.compile_animation(
        [(k.start, k.end, k.from_value, k.to_value, k.easing) for k in keyframes]
    )


class Timeline(Model):
    """Ordered keyframes compiled once and reused for all samples."""

    keyframes: Keyframes

    @cached_property
    def native(self) -> Animation:
        """Return the cached low-level animation."""
        return compile_animation(self.keyframes)

    @validate_call(config=ConfigDict(strict=True))
    def sample(self, index: Index, *, fps: PositiveInt = 30) -> float:
        """Sample one frame, holding the endpoint values outside the timeline."""
        return self.native.sample(index, fps)

    @validate_call(config=ConfigDict(strict=True))
    def sample_many(self, indices: Iterable[Index], *, fps: PositiveInt = 30) -> list[float]:
        """Sample a batch with one native call and the GIL released."""
        return self.native.sample_many(tuple(indices), fps)
