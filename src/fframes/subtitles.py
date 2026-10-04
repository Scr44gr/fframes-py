"""Validated WebVTT data parsed in Rust before rendering."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from fframes import _native
from fframes.models import Model, Seconds


class CueSettings(Model):
    """Optional WebVTT layout settings; rendering applies an explicit text style."""

    vertical: Literal["rl", "lr"] | None = None
    line: (
        Annotated[str, Field(pattern=r"^[+-]?\d+(?:\.\d+)?%?(?:,(?:start|center|end))?$")] | None
    ) = None
    position: Annotated[float, Field(ge=0, le=100)] | None = None
    position_align: Literal["line-left", "center", "line-right"] | None = None
    size: Annotated[float, Field(ge=0, le=100)] | None = None
    align: Literal["start", "center", "end", "left", "right"] | None = None
    region: str | None = None


class Cue(Model):
    """One cue; text preserves WebVTT markup and line breaks for the caller."""

    start: Seconds
    end: Seconds
    text: str
    name: str | None = None
    settings: CueSettings | None = None

    @model_validator(mode="after")
    def check_interval(self) -> Self:
        """Reject backwards timing before placing a cue on a composition."""
        if self.end < self.start:
            msg = "cue end must not precede its start"
            raise ValueError(msg)
        return self


class Subtitles(Model):
    """Cues in source order, plus header, CSS, comments and region definitions."""

    cues: tuple[Cue, ...]
    description: str | None = None
    styles: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()

    @classmethod
    def parse(cls, text: str) -> Self:
        """Parse WebVTT text natively, retaining timing and settings without rendering."""
        return cls.model_validate_json(_native.parse_subtitles(text))
