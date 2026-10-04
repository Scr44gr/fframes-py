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
    Rectangle,
    ShaderLayer,
    Size,
    Text,
    VectorPath,
    Visual,
)
from fframes.compose.media import Audio, Image, VideoClip
from fframes.models import Backend, Model, Source


class Group(Visual):
    """A resolved canvas; children refer to this layer by index."""

    kind: Literal["group"] = "group"
    size: Size


Graphic: TypeAlias = Annotated[
    Group | Rectangle | Circle | Ellipse | Text | VectorPath | Image | ShaderLayer | VideoClip,
    Field(discriminator="kind"),
]


class Layer(Model):
    """One occurrence with absolute timing and a local animation origin."""

    parent: int | None
    start: float
    end: float
    graphic: Graphic


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
                index = len(self.layers)
                self.layers.append(
                    Layer(
                        parent=parent,
                        start=start,
                        end=end,
                        graphic=Group(
                            size=size,
                            position=item.position,
                            opacity=item.opacity,
                            rotation=item.rotation,
                            scale=item.scale,
                            origin=item.origin,
                            matrix=item.matrix,
                            mask=item.mask,
                            filter=item.filter,
                        ),
                    )
                )
                for child in item.children:
                    self.visit(child, index, start, end, size, depth + 1)
            elif isinstance(item, Audio):
                self.sounds.append(Sound(start=start, end=end, audio=item))
            elif isinstance(
                item, (Rectangle, Circle, Ellipse, Text, VectorPath, Image, ShaderLayer, VideoClip)
            ):
                self.layers.append(Layer(parent=parent, start=start, end=end, graphic=item))
            else:
                msg = f"unsupported item: {type(item).__name__}; subclass Component"
                raise TypeError(msg)
        finally:
            self.active.remove(id(item))
