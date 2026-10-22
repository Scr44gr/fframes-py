"""In-memory SVG video compilation and rendering."""

from functools import cached_property
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import ConfigDict, TypeAdapter, validate_call

from fframes import _native
from fframes._native import SvgVideo
from fframes.audio import AudioTrack
from fframes.buffers import Buffers
from fframes.lottie import LottieBinding
from fframes.media import ImageBinding, VideoBinding
from fframes.models import (
    AudioMixOptions,
    Frames,
    Index,
    Model,
    OutputPath,
    RenderOptions,
    VideoConfig,
)
from fframes.rendering import RenderControl
from fframes.shaders import ShaderBinding
from fframes.three_d import SceneBinding
from fframes.timing import SceneRange, TimelineIndex, inspect_timeline

_bindings = TypeAdapter(tuple[ShaderBinding, ...])


class MediaBindings(Model):
    """Transfer explicit local resources together to the native engine."""

    audio: tuple[AudioTrack, ...] = ()
    images: tuple[ImageBinding, ...] = ()
    clips: tuple[VideoBinding, ...] = ()
    scenes: tuple[SceneBinding, ...] = ()
    lotties: tuple[LottieBinding, ...] = ()
    chapters: tuple[SceneRange, ...] = ()


@validate_call(config=ConfigDict(strict=True))
def compile_video(
    config: VideoConfig,
    frames: Frames,
    *,
    shaders: tuple[ShaderBinding, ...] = (),
    audio: tuple[AudioTrack, ...] = (),
    images: tuple[ImageBinding, ...] = (),
    clips: tuple[VideoBinding, ...] = (),
    scenes: tuple[SceneBinding, ...] = (),
    lotties: tuple[LottieBinding, ...] = (),
    chapters: tuple[SceneRange, ...] = (),
) -> SvgVideo:
    """Transfer a validated SVG sequence to an immutable native video."""
    buffers = Buffers()
    shaders_json = _bindings.dump_json(shaders, context=buffers).decode()
    media_json = MediaBindings(
        audio=audio,
        images=images,
        clips=clips,
        scenes=scenes,
        lotties=lotties,
        chapters=chapters,
    ).model_dump_json(context=buffers)
    return _native.compile_video(
        config.model_dump_json(),
        frames,
        shaders_json,
        media_json,
        buffers.data,
    )


@validate_call(config=ConfigDict(strict=True, arbitrary_types_allowed=True))
def render(
    video: SvgVideo | _native.SceneVideo,
    path: OutputPath,
    options: RenderOptions | None = None,
    *,
    control: RenderControl | None = None,
) -> Path:
    """Encode a native video and always clean up its temporary segments."""
    if options is None:
        options = RenderOptions()
    destination = Path(path)
    # Share the destination filesystem so the final native rename is atomic.
    with TemporaryDirectory(prefix="fframes-py-", dir=destination.absolute().parent) as directory:
        video.render(
            destination,
            Path(directory),
            options.model_dump_json(),
            control._native if control is not None else None,
        )
    return destination


class Video(Model):
    """A finite SVG sequence, transferred to Rust on first use."""

    config: VideoConfig = VideoConfig()
    frames: Frames
    shaders: tuple[ShaderBinding, ...] = ()
    audio: tuple[AudioTrack, ...] = ()
    images: tuple[ImageBinding, ...] = ()
    clips: tuple[VideoBinding, ...] = ()
    scenes: tuple[SceneBinding, ...] = ()
    lotties: tuple[LottieBinding, ...] = ()
    chapters: tuple[SceneRange, ...] = ()

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
        return compile_video(
            self.config,
            self.frames,
            shaders=self.shaders,
            audio=self.audio,
            images=self.images,
            clips=self.clips,
            scenes=self.scenes,
            lotties=self.lotties,
            chapters=self.chapters,
        )

    @cached_property
    def timeline(self) -> TimelineIndex:
        """Return named chapter ranges with upstream time selectors."""
        return inspect_timeline(self.native)

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

    def render(
        self,
        path: OutputPath,
        *,
        options: RenderOptions | None = None,
        control: RenderControl | None = None,
    ) -> Path:
        """Encode the selected frame range, or the whole video, using H.264 by default."""
        return render(self.native, path, options, control=control)

    @validate_call(config=ConfigDict(strict=True))
    def audio_samples(self, *, mix: AudioMixOptions | None = None) -> bytes:
        """Return owned stereo float32 little-endian PCM at 48 kHz."""
        return self.native.audio_samples(mix.model_dump_json() if mix is not None else None)
