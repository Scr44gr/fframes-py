"""Pythonic in-memory SVG videos."""

from functools import cached_property
from pathlib import Path

from pydantic import ConfigDict, validate_call

from fframes import lowlevel
from fframes._native import SvgVideo
from fframes.models import Frames, Index, Model, OutputPath, RenderOptions, VideoConfig


class Video(Model):
    """A finite SVG sequence, transferred to Rust on first use."""

    config: VideoConfig = VideoConfig()
    frames: Frames

    def __len__(self) -> int:
        """Return the number of frames."""
        return len(self.frames)

    @property
    def duration(self) -> float:
        """Return the duration in seconds."""
        return len(self) / self.config.fps

    @cached_property
    def native(self) -> SvgVideo:
        """Return the cached low-level video."""
        return lowlevel.compile_video(self.config, self.frames)

    @validate_call(config=ConfigDict(strict=True))
    def rgba(self, index: Index = 0) -> bytes:
        """Render straight RGBA8 pixels in row-major order."""
        return self.native.rgba(index)

    @validate_call(config=ConfigDict(strict=True))
    def save_png(self, path: OutputPath, *, index: Index = 0) -> Path:
        """Render one frame to a PNG file."""
        destination = Path(path)
        if destination.suffix.lower() != ".png":
            msg = "PNG output requires a .png extension"
            raise ValueError(msg)
        self.native.save_png(index, destination)
        return destination

    def render(self, path: OutputPath, *, options: RenderOptions | None = None) -> Path:
        """Encode all frames; MPEG-4 is available in the default LGPL build."""
        return lowlevel.render(self.native, path, options)
