"""Finite compositions and reusable native render sessions."""

from dataclasses import dataclass
from math import ceil, nextafter
from pathlib import Path
from typing import Self

from pydantic import ConfigDict, model_validator, validate_call

from fframes import _native
from fframes.buffers import Buffers
from fframes.compose.compiler import Compiler, Plan
from fframes.compose.components import Composition
from fframes.models import AudioMixOptions, Backend, Index, Model, OutputPath, PositiveInt, Source
from fframes.models import RenderOptions as RenderOptions
from fframes.rendering import RenderControl
from fframes.three_d.scene import Texture, _CompositionTexture
from fframes.timing import SceneRange, TimelineIndex, inspect_timeline
from fframes.video import render


@dataclass(frozen=True)
class CompiledVideo:
    """Owned native assets and timing, reusable without executing components again."""

    _scene: _native.SceneVideo

    @property
    def native(self) -> _native.SceneVideo:
        """Access the compiled engine session for batch inspection and previews."""
        return self._scene

    def __len__(self) -> int:
        """Return the encoded frame count."""
        return len(self._scene)

    @property
    def timeline(self) -> TimelineIndex:
        """Inspect the compiled composition names and their visible frame ranges."""
        return inspect_timeline(self._scene)

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

    @validate_call(config=ConfigDict(strict=True))
    def audio_samples(self, *, mix: AudioMixOptions | None = None) -> bytes:
        """Return the final stereo mix as interleaved float32 little-endian at 48 kHz."""
        return self._scene.audio_samples(mix.model_dump_json() if mix is not None else None)

    def render(
        self,
        path: OutputPath,
        *,
        options: RenderOptions | None = None,
        control: RenderControl | None = None,
    ) -> Path:
        """Render and mix natively, replacing the destination only after success."""
        return render(self._scene, path, options, control=control)


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
    backend: Backend = "cpu"

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

    def _plan(self) -> Plan:
        compiler = Compiler()
        width, height = self.resolution
        compiler.visit(self.composition, None, 0.0, self.duration, (float(width), float(height)))
        return Plan(
            resolution=self.resolution,
            fps=self.fps,
            frames=len(self),
            chapters=tuple(
                SceneRange(name=name, frames=(first, end))
                for name, start, stop in compiler.chapters
                if (first := max(0, ceil(nextafter(start * self.fps, float("-inf")))))
                < (end := min(len(self), ceil(nextafter(stop * self.fps, float("-inf")))))
            ),
            layers=tuple(compiler.layers),
            sounds=tuple(compiler.sounds),
            fonts=self.fonts,
            load_system_fonts=self.load_system_fonts,
            backend=self.backend,
        )

    def compile(self) -> CompiledVideo:
        """Expand components once and transfer a typed scene to Rust."""
        buffers = Buffers()
        plan = self._plan().model_dump_json(context=buffers)
        return CompiledVideo(_native.compile_scene(plan, buffers.data))

    def texture(self) -> Texture:
        """Use this video's visuals on a 3D surface; put audio in the outer composition."""
        plan = self._plan()
        if plan.sounds:
            raise ValueError(
                "a texture contains visuals only; place Audio in the outer composition"
            )
        buffers = Buffers()
        description = plan.model_dump_json(context=buffers)
        return Texture(
            source=_CompositionTexture(
                plan=description,
                buffers=tuple(buffers.data.items()),
            )
        )

    def rgba(self, index: Index = 0) -> bytes:
        """Compile and preview one frame; use compile() to preview many."""
        return self.compile().rgba(index)

    def save_png(self, path: OutputPath, *, index: Index = 0) -> Path:
        """Compile and save one frame."""
        return self.compile().save_png(path, index=index)

    def render(
        self,
        path: OutputPath,
        *,
        options: RenderOptions | None = None,
        control: RenderControl | None = None,
    ) -> Path:
        """Compile, render and mix without Python callbacks per frame."""
        return self.compile().render(path, options=options, control=control)
