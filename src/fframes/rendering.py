"""Poll rendering progress or cancel from another thread without frame callbacks."""

from typing import Literal

from pydantic import ConfigDict, validate_call

from fframes import _native
from fframes.models import Index, Model


@validate_call(config=ConfigDict(strict=True))
def available_encoders(media: Literal["video", "audio"] = "video") -> list[str]:
    """List encoders in the linked library; hardware entries still require a device."""
    return _native.available_encoders(audio=media == "audio")


class RenderProgress(Model):
    """A snapshot of one render, including upstream encoder warnings."""

    state: Literal["idle", "rendering", "muxing", "complete", "cancelled", "failed"]
    frames: Index
    total_frames: Index
    audio_frames: Index
    total_audio_frames: Index
    warnings: tuple[str, ...]


class RenderControl:
    """Thread-safe control for one export; pass it as render(control=control)."""

    __slots__ = ("_native",)

    def __init__(self) -> None:
        """Create an idle control; create another for each subsequent export."""
        self._native = _native.RenderControl()

    def cancel(self) -> None:
        """Request cancellation; completed exports are unaffected."""
        self._native.cancel()

    @property
    def progress(self) -> RenderProgress:
        """Read native counters without waiting for rendering to finish."""
        return RenderProgress.model_validate_json(self._native.snapshot())
