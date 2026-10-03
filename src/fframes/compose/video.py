"""Finite compositions and reusable native render sessions."""

from dataclasses import dataclass
from math import ceil, nextafter
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Self

from pydantic import ConfigDict, model_validator, validate_call

from fframes import _native
from fframes.compose.compiler import Compiler, Plan
from fframes.compose.components import Composition
from fframes.compose.media import Source
from fframes.models import Index, Model, OutputPath, PositiveInt
from fframes.models import RenderOptions as BaseRenderOptions


class RenderOptions(BaseRenderOptions):
    """Native encoder settings; audio is mixed and encoded at 48 kHz."""

    bitrate: PositiveInt = 8_000_000


@dataclass(frozen=True)
class CompiledVideo:
    """Owned native assets and timing, reusable without executing components again."""

    _scene: _native.SceneVideo

    def __len__(self) -> int:
        """Return the encoded frame count."""
        return len(self._scene)

    @validate_call(config=ConfigDict(strict=True))
    def rgba(self, index: Index = 0) -> bytes:
        """Render straight RGBA8 pixels; frame indices are zero based."""
        return self._scene.rgba(index)

    @validate_call(config=ConfigDict(strict=True))
    def save_png(self, path: OutputPath, *, index: Index = 0) -> Path:
        """Save one frame without encoding the video."""
        destination = Path(path)
        if destination.suffix.lower() != ".png":
            msg = "PNG output requires a .png extension"
            raise ValueError(msg)
        self._scene.save_png(index, destination)
        return destination

    def audio_samples(self) -> bytes:
        """Return the final stereo mix as interleaved float32 little-endian at 48 kHz."""
        return self._scene.audio_samples()

    @validate_call(config=ConfigDict(strict=True))
    def render(self, path: OutputPath, *, options: RenderOptions | None = None) -> Path:
        """Render and mix natively, replacing the destination only after success."""
        settings = options or RenderOptions()
        destination = Path(path)
        with TemporaryDirectory(prefix="fframes-py-", dir=destination.absolute().parent) as folder:
            staged = Path(folder) / destination.name
            self._scene.render(
                staged, Path(folder), settings.encoder, settings.concurrency, settings.bitrate
            )
            staged.replace(destination)
        return destination


class Video(Model):
    """Describe a finite video; compile explicitly to reuse loaded assets.

    The root composition must specify a duration. A fractional final frame is
    included, so the encoded duration is rounded up to a whole frame. Fonts may
    be supplied explicitly for reproducible rendering across operating systems.
    """

    composition: Composition
    resolution: tuple[PositiveInt, PositiveInt] = (1920, 1080)
    fps: PositiveInt = 30
    fonts: tuple[Source, ...] = ()
    load_system_fonts: bool = True

    @model_validator(mode="after")
    def check_duration(self) -> Self:
        """Require a finite root clock before compiling any assets."""
        if self.composition.duration is None:
            msg = "the root composition requires duration"
            raise ValueError(msg)
        return self

    def __len__(self) -> int:
        """Round the requested duration up to complete frames."""
        duration = self.composition.duration
        if duration is None:
            msg = "the root composition requires duration"
            raise ValueError(msg)
        return max(1, ceil(nextafter(duration * self.fps, float("-inf"))))

    @property
    def duration(self) -> float:
        """Return the encoded duration after frame rounding."""
        return len(self) / self.fps

    def compile(self) -> CompiledVideo:
        """Expand components once and transfer a typed scene to Rust."""
        compiler = Compiler()
        width, height = self.resolution
        compiler.visit(self.composition, None, 0.0, self.duration, (float(width), float(height)))
        plan = Plan(
            resolution=self.resolution,
            fps=self.fps,
            frames=len(self),
            layers=tuple(compiler.layers),
            sounds=tuple(compiler.sounds),
            fonts=self.fonts,
            load_system_fonts=self.load_system_fonts,
        )
        return CompiledVideo(_native.compile_scene(plan.model_dump_json()))

    def rgba(self, index: Index = 0) -> bytes:
        """Compile and preview one frame; use compile() to preview many."""
        return self.compile().rgba(index)

    def save_png(self, path: OutputPath, *, index: Index = 0) -> Path:
        """Compile and save one frame."""
        return self.compile().save_png(path, index=index)

    def render(self, path: OutputPath, *, options: RenderOptions | None = None) -> Path:
        """Compile, render and mix without Python callbacks per frame."""
        return self.compile().render(path, options=options)
