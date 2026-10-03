"""Pythonic scalar animation backed by the upstream Rust timeline."""

from collections.abc import Iterable
from functools import cached_property

from pydantic import ConfigDict, validate_call

from fframes import lowlevel
from fframes._native import Animation
from fframes.models import Index, Keyframes, Model, PositiveInt


class Timeline(Model):
    """Ordered keyframes compiled once and reused for all samples."""

    keyframes: Keyframes

    @cached_property
    def native(self) -> Animation:
        """Return the cached low-level animation."""
        return lowlevel.compile_animation(self.keyframes)

    @validate_call(config=ConfigDict(strict=True))
    def sample(self, index: Index, *, fps: PositiveInt = 30) -> float:
        """Sample one frame, holding the endpoint values outside the timeline."""
        return self.native.sample(index, fps)

    @validate_call(config=ConfigDict(strict=True))
    def sample_many(self, indices: Iterable[Index], *, fps: PositiveInt = 30) -> list[float]:
        """Sample a batch with one native call and the GIL released."""
        return self.native.sample_many(tuple(indices), fps)
