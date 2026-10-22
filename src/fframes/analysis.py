"""Inspect the final audio mix with upstream loudness and peak analysis."""

from typing import Annotated, Self

from pydantic import ConfigDict, Field, model_validator, validate_call

from fframes import _native
from fframes.effects import Effect
from fframes.inspection import NativeVideo
from fframes.models import AudioMixOptions, FiniteFloat, Index, Model, PositiveInt, Seconds


class AudioSection(Model):
    """A named half-open interval in seconds on the original timeline."""

    name: Annotated[str, Field(min_length=1)]
    start: Seconds
    end: Seconds

    @model_validator(mode="after")
    def check_interval(self) -> Self:
        """Require an audible interval."""
        if self.start >= self.end:
            raise ValueError("audio section requires start < end")
        return self


class SectionLoudness(Model):
    """Levels of a named interval; times are relative to the analyzed range."""

    name: str
    start_seconds: Seconds
    end_seconds: Seconds
    integrated_lufs: FiniteFloat | None
    true_peak_dbtp: FiniteFloat | None


class AudioReport(Model):
    """Native loudness, peaks and silence; None represents an undefined silent level."""

    duration_seconds: Seconds
    sample_rate: PositiveInt
    integrated_lufs: FiniteFloat | None
    loudness_range_lu: FiniteFloat | None
    max_momentary_lufs: FiniteFloat | None
    max_short_term_lufs: FiniteFloat | None
    sample_peak_dbfs: FiniteFloat | None
    true_peak_dbtp: FiniteFloat | None
    clipped_samples: Index
    silent_ranges: tuple[tuple[Seconds, Seconds], ...]
    sections: tuple[SectionLoudness, ...]


class ActiveTrack(Model):
    """Source position and effective per-track gain before the master bus."""

    file: str
    file_seconds: Seconds
    gain_db: FiniteFloat | None
    voice: bool
    ducked_db: FiniteFloat
    rate: FiniteFloat
    effects: tuple[Effect, ...]


class AudioActivity(Model):
    """Tracks active at one original timeline position."""

    seconds: Seconds
    tracks: tuple[ActiveTrack, ...]


class Waveform(Model):
    """Stereo min/max bins spanning the entire analyzed interval, including its tail."""

    left: tuple[tuple[FiniteFloat, FiniteFloat], ...]
    right: tuple[tuple[FiniteFloat, FiniteFloat], ...]


class AudioInspection(Model):
    """Measurements, waveform and selected track activity from one native mix."""

    start_seconds: Seconds
    report: AudioReport
    waveform: Waveform
    activity: tuple[AudioActivity, ...]


class AudioAnalysisOptions(Model):
    """Configure the mix and requested measurements without changing the video."""

    mix: AudioMixOptions = AudioMixOptions()
    sample_rate: PositiveInt = 48_000
    frame_range: tuple[Index, Index] | None = None
    sections: tuple[AudioSection, ...] = ()
    at: tuple[Seconds, ...] = ()
    waveform_bins: Annotated[int, Field(ge=1, le=65536)] = 1024

    @model_validator(mode="after")
    def check_range(self) -> Self:
        """Reject empty or reversed ranges before mixing."""
        if self.frame_range is not None and self.frame_range[0] >= self.frame_range[1]:
            raise ValueError("frame_range requires start < end")
        return self


@validate_call(config=ConfigDict(strict=True, arbitrary_types_allowed=True))
def analyze_audio(
    video: NativeVideo, *, options: AudioAnalysisOptions | None = None
) -> AudioInspection:
    """Mix and analyze in Rust; pass Video.native or a compiled compose video's native."""
    return AudioInspection.model_validate_json(
        _native.analyze_audio(video, (options or AudioAnalysisOptions()).model_dump_json())
    )
