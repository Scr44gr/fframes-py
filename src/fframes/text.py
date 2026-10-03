"""Upstream font metrics, fitting and wrapping shared by both authoring APIs."""

from functools import cached_property
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, validate_call

from fframes import _native
from fframes.models import Model, PositiveInt, Source


class Font(Model):
    """A font query for upstream's integer advance-width metrics."""

    family: Annotated[str, Field(min_length=1)]
    size: Annotated[int, Field(gt=0, le=100000)] = 32
    weight: Annotated[int, Field(ge=100, le=900)] = 400
    style: Literal["normal", "italic", "oblique"] = "normal"


class TextLayout(Model):
    """Own font data once; measure and lay out text before rendering."""

    fonts: tuple[Source, ...] = ()
    load_system_fonts: bool = False

    @cached_property
    def native(self) -> _native.TextLayout:
        """Load the font database on first use."""
        return _native.compile_text_layout(self.model_dump_json())

    @validate_call(config=ConfigDict(strict=True))
    def widths(self, texts: tuple[str, ...], font: Font) -> tuple[int, ...]:
        """Measure a batch with one native call, including trailing spaces."""
        return tuple(self.native.widths(texts, font.model_dump_json()))

    def width(self, text: str, font: Font) -> int:
        """Measure one line using the same metrics as upstream fframes."""
        return self.widths((text,), font)[0]

    @validate_call(config=ConfigDict(strict=True))
    def fit(self, text: str, font: Font, width: PositiveInt, *, marker: str = "…") -> str:
        """Shorten a line at a Unicode character boundary and append a marker."""
        return self.native.fit(text, font.model_dump_json(), width, marker)

    @validate_call(config=ConfigDict(strict=True))
    def wrap(self, text: str, font: Font, width: PositiveInt) -> tuple[str, ...]:
        """Wrap words; an indivisible word can exceed the requested width."""
        return tuple(self.native.wrap(text, font.model_dump_json(), width))
