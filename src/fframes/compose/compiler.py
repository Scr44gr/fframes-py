"""Expand custom components into a typed, flat native scene description."""

from typing import Annotated, Literal, TypeAlias

from pydantic import Field

from fframes.compose.components import (
    Circle,
    Clip,
    Component,
    Composition,
    Ellipse,
    Item,
    LayerMask,
    Rectangle,
    ShaderLayer,
    Text,
    VectorPath,
    Visual,
)
from fframes.compose.media import Audio, Image, LottieLayer, VideoClip
from fframes.compose.three_d import Scene3D
from fframes.models import Backend, Model, Size, Source
from fframes.timing import SceneRange


class Group(Visual):
    """A resolved canvas; children refer to this layer by index."""

    kind: Literal["group"] = "group"
    size: Size


Graphic: TypeAlias = Annotated[
    Group
    | Rectangle
    | Circle
    | Ellipse
    | Text
    | VectorPath
    | Image
    | ShaderLayer
    | VideoClip
    | Scene3D
    | LottieLayer,
    Field(discriminator="kind"),
]


class Layer(Model):
    """One occurrence with absolute timing and a local animation origin."""

    parent: int | None
    start: float
    end: float
    graphic: Graphic
    mask_index: int | None = None
    mask_mode: Literal["alpha", "luminance"] = "alpha"
    mask_region: tuple[float, float, float, float] = (-0.1, -0.1, 1.2, 1.2)
    mask_only: bool = False


class Sound(Model):
    """An audio occurrence bounded by all enclosing intervals."""

    start: float
    end: float
    audio: Audio


class Plan(Model):
    """Transfer descriptions once, without Python objects in the frame loop."""

    resolution: tuple[int, int]
    fps: int
    frames: int
    chapters: tuple[SceneRange, ...] = ()
    layers: tuple[Layer, ...]
    sounds: tuple[Sound, ...]
    fonts: tuple[Source, ...]
    load_system_fonts: bool
    backend: Backend = "cpu"


class Compiler:
    """Resolve reuse by object identity within one compilation."""

    def __init__(self) -> None:
        """Keep expansion caches local so future compilations see current files."""
        self.layers: list[Layer] = []
        self.sounds: list[Sound] = []
        self.chapters: list[tuple[str, float, float]] = []
        self.components: dict[int, Composition] = {}
        self.active: set[int] = set()

    def visit(
        self,
        item: Item,
        parent: int | None,
        start: float,
        end: float,
        size: Size,
        depth: int = 0,
    ) -> None:
        """Expand content and intersect each occurrence with its parent interval."""
        if depth > 64 or id(item) in self.active:
            msg = "component cycle or composition nesting exceeds 64 levels"
            raise ValueError(msg)
        if start >= end:
            return
        self.active.add(id(item))
        try:
            if isinstance(item, Component):
                key = id(item)
                if key not in self.components:
                    self.components[key] = item.compose()
                self.visit(self.components[key], parent, start, end, size, depth + 1)
            elif isinstance(item, Clip):
                start += item.start_at
                if item.duration is not None:
                    end = min(end, start + item.duration)
                self.visit(item.content, parent, start, end, size, depth + 1)
            elif isinstance(item, Composition):
                size = item.size or size
                if item.duration is not None:
                    end = min(end, start + item.duration)
                if item.name is not None and start < end:
                    self.chapters.append((item.name, start, end))
                index = len(self.layers)
                self.layers.append(
                    Layer(
                        parent=parent,
                        start=start,
                        end=end,
                        graphic=Group(
                            id=item.id,
                            size=size,
                            position=item.position,
                            opacity=item.opacity,
                            z_index=item.z_index,
                            rotation=item.rotation,
                            scale=item.scale,
                            origin=item.origin,
                            matrix=item.matrix,
                            mask=item.mask,
                            filter=item.filter,
                            blend_mode=item.blend_mode,
                        ),
                    )
                )
                for child in item.children:
                    self.visit(child, index, start, end, size, depth + 1)
            elif isinstance(item, Audio):
                self.sounds.append(Sound(start=start, end=end, audio=item))
            elif isinstance(
                item,
                (
                    Rectangle,
                    Circle,
                    Ellipse,
                    Text,
                    VectorPath,
                    Image,
                    ShaderLayer,
                    VideoClip,
                    Scene3D,
                    LottieLayer,
                ),
            ):
                index = len(self.layers)
                self.layers.append(Layer(parent=parent, start=start, end=end, graphic=item))
            else:
                msg = f"unsupported item: {type(item).__name__}; subclass Component"
                raise TypeError(msg)
            if isinstance(item, Visual) and isinstance(item.mask, LayerMask):
                owner = self.layers[index]
                root = len(self.layers)
                sound_count = len(self.sounds)
                chapter_count = len(self.chapters)
                self.visit(
                    Composition(children=(item.mask.content,), size=size),
                    None,
                    start,
                    end,
                    size,
                    depth + 1,
                )
                if len(self.sounds) != sound_count:
                    raise ValueError(
                        "LayerMask contains visuals only; place Audio outside the mask"
                    )
                del self.chapters[chapter_count:]
                self.layers[root] = self.layers[root].model_copy(update={"mask_only": True})
                self.layers[index] = owner.model_copy(
                    update={
                        "graphic": owner.graphic.model_copy(update={"mask": None}),
                        "mask_index": root,
                        "mask_mode": item.mask.mode,
                        "mask_region": item.mask.region,
                    }
                )
        finally:
            self.active.remove(id(item))
