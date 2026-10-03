"""Shared file, mix and timing descriptions for native audio tracks."""

from typing import Annotated

from pydantic import Field

from fframes.models import Model, Seconds, Source
from fframes.values import Duration, Start


class AudioSettings(Model):
    """Decode a file once and apply mix settings to its audible interval."""

    source: Source
    gain_db: Annotated[float, Field(ge=-120, le=24, allow_inf_nan=False)] = 0.0
    pan: Annotated[float, Field(ge=-1, le=1, allow_inf_nan=False)] = 0.0
    offset: Seconds = 0.0
    fade_in: Seconds = 0.0
    fade_out: Seconds = 0.0
    loop: bool = False


class AudioTrack(AudioSettings):
    """Place a track on an SVG video's global clock; stop at its duration or EOF."""

    start_at: Start = 0.0
    duration: Duration | None = None
