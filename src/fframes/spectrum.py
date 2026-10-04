"""Batched audio analysis with an immutable buffer suitable for NumPy views."""

from functools import cached_property
from typing import Annotated, Literal, Self, TypeAlias

from pydantic import Field, model_validator

from fframes import _native
from fframes.models import Model, PositiveInt, Source

SampleSize: TypeAlias = Literal[2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
Window: TypeAlias = Literal["hann", "hamming", "hamming_legacy"]


class Spectrum(Model):
    """Row-major magnitudes: frames by bins, packed float32 little-endian, read-only."""

    data: bytes
    frames: PositiveInt
    bins: PositiveInt
    fps: PositiveInt

    @model_validator(mode="after")
    def check_buffer(self) -> Self:
        """Require complete frames without reinterpreting or copying their storage."""
        if len(self.data) != self.frames * self.bins * 4:
            msg = "spectrum data length must equal frames * bins * 4"
            raise ValueError(msg)
        return self


class SpectrumSettings(Model):
    """Validated native batch input."""

    frames: PositiveInt
    fps: PositiveInt
    sample_size: SampleSize = 64
    smooth: Annotated[int, Field(ge=0, le=120)] = 4
    window: Window | None = None
    center: bool = False


class AudioData(Model):
    """Decode a local source to mono once for repeated native spectral analysis."""

    source: Source

    @cached_property
    def native(self) -> _native.AudioAnalysis:
        """Retain decoded samples independently of the input file's lifetime."""
        return _native.decode_audio(str(self.source))

    @property
    def duration(self) -> float:
        """Return the decoded sample count divided by its sample rate."""
        return self.native.duration

    @property
    def sample_rate(self) -> int:
        """Return the source's decoded sampling rate."""
        return self.native.sample_rate

    def spectrum(
        self,
        *,
        frames: int,
        fps: int,
        sample_size: SampleSize = 64,
        smooth: int = 4,
        window: Window | None = None,
        center: bool = False,
    ) -> Spectrum:
        """Calculate each FFT once, smooth nearby frames and optionally center low bins.

        Magnitudes omit Nyquist and are not normalized. Smoothing follows upstream:
        after the first 2*smooth+1 frames, average [frame-smooth, frame+smooth).
        Use hamming_legacy only to reproduce fframes 1.2.0's window coefficients.
        """
        settings = SpectrumSettings(
            frames=frames,
            fps=fps,
            sample_size=sample_size,
            smooth=smooth,
            window=window,
            center=center,
        )
        return Spectrum(
            data=self.native.spectrum(settings.model_dump_json()),
            frames=frames,
            fps=fps,
            bins=sample_size // 2,
        )
