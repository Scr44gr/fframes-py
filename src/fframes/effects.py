"""Ordered per-track audio processing, performed once by the native mixer."""

from typing import Annotated, Literal, TypeAlias

from pydantic import Field

from fframes.models import Model

Frequency: TypeAlias = Annotated[float, Field(ge=1, le=23520, allow_inf_nan=False)]
Decibels: TypeAlias = Annotated[float, Field(ge=-120, le=24, allow_inf_nan=False)]
Quality: TypeAlias = Annotated[float, Field(ge=0.05, le=100, allow_inf_nan=False)]
Time: TypeAlias = Annotated[float, Field(ge=1e-5, le=60, allow_inf_nan=False)]


class NormalizeLufs(Model):
    """Normalize integrated loudness; silence and tracks shorter than 400 ms are unchanged."""

    kind: Literal["normalize_lufs"] = "normalize_lufs"
    lufs: Annotated[float, Field(ge=-70, le=0, allow_inf_nan=False)] = -16.0


class Cutoff(Model):
    """Shared parameters of a 12 dB/octave biquad filter."""

    hz: Frequency
    q: Quality = 0.70710678


class Highpass(Cutoff):
    """Attenuate frequencies below hz."""

    kind: Literal["highpass"] = "highpass"


class Lowpass(Cutoff):
    """Attenuate frequencies above hz."""

    kind: Literal["lowpass"] = "lowpass"


class Shelf(Model):
    """Shared cutoff and gain of a shelf filter."""

    hz: Frequency
    db: Decibels


class LowShelf(Shelf):
    """Apply db below hz, reaching half that gain at hz."""

    kind: Literal["low_shelf"] = "low_shelf"


class HighShelf(Shelf):
    """Apply db above hz, reaching half that gain at hz."""

    kind: Literal["high_shelf"] = "high_shelf"


class Peak(Shelf):
    """Bell EQ centered at hz with bandwidth hz/q."""

    kind: Literal["peak"] = "peak"
    q: Quality = 1.0


class Compressor(Model):
    """Stereo-linked peak compressor. Attack and release are in seconds."""

    kind: Literal["compressor"] = "compressor"
    threshold_db: Decibels = -18.0
    ratio: Annotated[float, Field(ge=1, le=100, allow_inf_nan=False)] = 3.0
    attack: Time = 0.01
    release: Time = 0.15
    knee_db: Annotated[float, Field(ge=0, le=60, allow_inf_nan=False)] = 6.0
    makeup_db: Decibels = 0.0


class StereoWidth(Model):
    """Mid/side width: 0 is mono, 1 preserves stereo; mono sources gain a delayed side."""

    kind: Literal["width"] = "width"
    width: Annotated[float, Field(ge=0, le=10, allow_inf_nan=False)] = 1.0


Effect: TypeAlias = Annotated[
    NormalizeLufs | Highpass | Lowpass | LowShelf | HighShelf | Peak | Compressor | StereoWidth,
    Field(discriminator="kind"),
]
