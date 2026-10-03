"""File-backed images and audio; files are loaded during compilation."""

from typing import Annotated, Literal

from pydantic import Field

from fframes.compose.components import Item, Size, Visual
from fframes.models import Seconds, Source


class Image(Visual):
    """A raster image stretched to the explicit local size."""

    kind: Literal["image"] = "image"
    source: Source
    size: Size


class Audio(Item):
    """Mix a file in local time, with optional looping from the source offset.

    Unlooped audio ends at its natural duration or the enclosing interval.
    Fades apply to the complete audible interval, including repetitions.
    """

    source: Source
    gain_db: Annotated[float, Field(ge=-120, le=24, allow_inf_nan=False)] = 0.0
    pan: Annotated[float, Field(ge=-1, le=1, allow_inf_nan=False)] = 0.0
    offset: Seconds = 0.0
    fade_in: Seconds = 0.0
    fade_out: Seconds = 0.0
    loop: bool = False
