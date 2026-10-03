"""In-memory SVG video compilation and rendering."""

from functools import cached_property
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import ConfigDict, validate_call

from fframes import _native
from fframes._native import SvgVideo
from fframes.models import Frames, Index, Model, OutputPath, RenderOptions, VideoConfig


@validate_call(config=ConfigDict(strict=True))
def compile_video(config: VideoConfig, frames: Frames) -> SvgVideo:
    """Transfer a validated SVG sequence to an immutable native video."""
    return _native.compile_video(
        config.width, config.height, config.fps, frames, config.load_system_fonts
    )


@validate_call(config=ConfigDict(strict=True, arbitrary_types_allowed=True))
def render(video: SvgVideo, path: OutputPath, options: RenderOptions | None = None) -> Path:
    """Encode a native video and always clean up its temporary segments."""
    if options is None:
        options = RenderOptions()
    destination = Path(path)
    # Share the destination filesystem so the final native rename is atomic.
    with TemporaryDirectory(prefix="fframes-py-", dir=destination.absolute().parent) as directory:
        video.render(destination, Path(directory), options.encoder, options.concurrency)
    return destination


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
        return compile_video(self.config, self.frames)

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
        return render(self.native, path, options)
