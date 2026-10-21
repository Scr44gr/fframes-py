"""Shared file, mix and timing descriptions for native audio tracks."""

from typing import Annotated, Literal

from pydantic import Field

from fframes.effects import Effect
from fframes.models import Model, Seconds, Source
from fframes.values import Duration, Start


class Ducking(Model):
    """Lower this track around intervals marked voice=True, independently of their signal."""

    depth_db: Annotated[float, Field(ge=-120, le=0, allow_inf_nan=False)] = -12.0
    attack: Seconds = 0.2
    hold: Seconds = 0.3
    release: Seconds = 0.8
    merge_gap: Seconds = 0.8


class AudioSettings(Model):
    """Decode a file once and apply mix settings to its audible interval."""

    source: Source
    gain_db: Annotated[float, Field(ge=-120, le=24, allow_inf_nan=False)] = 0.0
    pan: Annotated[float, Field(ge=-1, le=1, allow_inf_nan=False)] = 0.0
    offset: Seconds = 0.0
    fade_in: Seconds = 0.0
    fade_out: Seconds = 0.0
    loop: bool = False
    rate: Annotated[float, Field(ge=0.05, le=20, allow_inf_nan=False)] = 1.0
    effects: tuple[Effect, ...] = ()
    fade_curve: Literal["linear", "equal_power", "s_curve", "exponential"] = "equal_power"
    voice: bool = False
    duck: Ducking | None = None


class AudioTrack(AudioSettings):
    """Place a track on an SVG video's global clock; stop at its duration or EOF."""

    start_at: Start = 0.0
    duration: Duration | None = None
