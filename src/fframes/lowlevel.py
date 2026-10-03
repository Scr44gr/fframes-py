"""Validated entry points to reusable fframes objects implemented in Rust."""

from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import ConfigDict, validate_call

from fframes import _native
from fframes._native import Animation, SvgVideo
from fframes.models import Frames, Keyframes, OutputPath, RenderOptions, VideoConfig

__all__ = ["Animation", "SvgVideo", "compile_animation", "compile_video", "render"]

_STRICT = ConfigDict(strict=True)


@validate_call(config=_STRICT)
def compile_animation(keyframes: Keyframes) -> Animation:
    """Prepare the upstream keyframe animation once for scalar or batch sampling."""
    return _native.compile_animation(
        [(k.start, k.end, k.from_value, k.to_value, k.easing) for k in keyframes]
    )


@validate_call(config=_STRICT)
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
