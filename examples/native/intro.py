"""Author the original intro through SVG frames and explicit fframes media bindings."""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from itertools import count
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeAlias

import numpy as np

import fframes
from examples.assets import files
from examples.shared.intro.drawing import (
    BONE,
    DISPLAY,
    FPS,
    FRAMES,
    HEIGHT,
    WIDTH,
    Anchor,
    Box,
    Matrix,
    Number,
    Painter,
    Pen,
    Pixels,
    Window,
    Words,
)
from examples.shared.intro.sequence import arguments, overlay, pieces, soundtrack

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from fframes.models import Backend

Attribute: TypeAlias = Number | Words


def at(value: Attribute, index: int) -> str:
    """Serialize a static attribute or one precomputed sample."""
    if isinstance(value, np.ndarray | tuple):
        return str(value[index])
    return str(value)


@dataclass(frozen=True, slots=True)
class Svg:
    """An example-only XML fragment evaluated while preparing the finite SVG sequence."""

    tag: str
    attrs: dict[str, Attribute] = field(default_factory=dict)
    children: tuple[Svg, ...] = ()
    content: Words = ""
    order: NDArray[np.int64] | None = None

    def frame(self, index: int, definitions: set[str] | None = None) -> str:
        """Expand one fragment; no Python callbacks survive video compilation."""
        if float(at(self.attrs.get("opacity", 1.0), index)) <= 0:
            return ""
        if definitions is None:
            definitions = set()
        if self.tag in ("clipPath", "filter", "linearGradient"):
            name = at(self.attrs["id"], index)
            if name in definitions:
                return ""
            definitions.add(name)
        attrs = " ".join(f'{k}="{escape(at(v, index), quote=True)}"' for k, v in self.attrs.items())
        children = (
            self.children
            if self.order is None
            else tuple(self.children[int(i)] for i in self.order[:, index])
        )
        body = escape(at(self.content, index)) + "".join(
            c.frame(index, definitions) for c in children
        )
        return f"<{self.tag} {attrs}>{body}</{self.tag}>"


@dataclass
class Bindings:
    """Share unique IDs and owned resource declarations across all scene windows."""

    ids: count[int] = field(default_factory=count)
    images: dict[Path, str] = field(default_factory=dict)
    clips: list[fframes.VideoBinding] = field(default_factory=list)
    shaders: list[fframes.ShaderBinding] = field(default_factory=list)
    first: int = 0


class Native(Painter[Svg]):
    """Emit SVG directly, without importing the compose API."""

    bindings: Bindings

    def ordered(self, children: tuple[Svg, ...], depths: tuple[Pixels, ...]) -> Svg:
        """Precompute the original depth order without copying any scene nodes."""
        return Svg(
            "g", children=children, order=np.argsort(np.stack(depths), axis=0, kind="stable")
        )

    def pen(self, pen: Pen | None) -> dict[str, Attribute]:
        """Serialize the source stroke, including sampled dash lengths."""
        if pen is None:
            return {}
        attrs: dict[str, Attribute] = {
            "stroke": pen.color,
            "stroke-width": pen.width,
            "stroke-dashoffset": pen.offset,
        }
        if pen.dash:
            attrs["stroke-dasharray"] = tuple(
                " ".join(at(v, i) for v in pen.dash) for i in range(len(self.frames))
            )
        return attrs

    def rect(
        self,
        box: Box,
        fill: Words | None = BONE,
        *,
        pen: Pen | None = None,
        radius: Number = 0,
        alpha: Number = 1,
    ) -> Svg:
        """Write a raw rectangle."""
        x, y, w, h = box
        return Svg(
            "rect",
            {
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "rx": radius,
                "fill": fill if fill is not None else "none",
                "opacity": alpha,
                **self.pen(pen),
            },
        )

    def text(
        self,
        x: Number,
        y: Number,
        content: Words,
        size: int,
        fill: Words = BONE,
        *,
        family: str = DISPLAY,
        weight: int = 400,
        spacing: float = 0,
        anchor: Anchor = "start",
        italic: bool = False,
        alpha: Number = 1,
        pen: Pen | None = None,
    ) -> Svg:
        """Keep SVG's original whitespace and baseline semantics."""
        return Svg(
            "text",
            {
                "x": x,
                "y": y,
                "font-family": family,
                "font-size": size,
                "font-weight": weight,
                "letter-spacing": spacing,
                "text-anchor": anchor,
                "xml:space": "preserve",
                "font-style": "italic" if italic else "normal",
                "fill": fill,
                "opacity": alpha,
                **self.pen(pen),
            },
            content=content,
        )

    def circle(
        self,
        x: Number,
        y: Number,
        radius: Number,
        fill: Words | None = BONE,
        *,
        pen: Pen | None = None,
        alpha: Number = 1,
    ) -> Svg:
        """Write a raw circle."""
        return Svg(
            "circle",
            {
                "cx": x,
                "cy": y,
                "r": radius,
                "fill": fill or "none",
                "opacity": alpha,
                **self.pen(pen),
            },
        )

    def path(self, data: str, pen: Pen, *, alpha: Number = 1) -> Svg:
        """Write a path with its explicit stroke."""
        return Svg("path", {"d": data, "fill": "none", "opacity": alpha, **self.pen(pen)})

    def group(
        self,
        children: tuple[Svg, ...],
        *,
        x: Number = 0,
        y: Number = 0,
        scale: Number = 1,
        rotation: Number = 0,
        origin: tuple[float, float] = (0, 0),
        alpha: Number = 1,
        mask: Box | None = None,
        radius: Number = 0,
        blend: Literal["normal", "difference"] = "normal",
        blur: float = 0,
        matrix: Matrix | None = None,
    ) -> Svg:
        """Group SVG nodes with unique local masks and filters."""
        ox, oy = origin
        transforms = tuple(
            (f"matrix({' '.join(at(v, i) for v in matrix)}) " if matrix else "")
            + f"translate({at(x, i)} {at(y, i)}) translate({ox} {oy}) "
            + f"rotate({at(rotation, i)}) scale({at(scale, i)}) translate({-ox} {-oy})"
            for i in range(len(self.frames))
        )
        attrs: dict[str, Attribute] = {
            "transform": transforms,
            "opacity": alpha,
            "style": f"mix-blend-mode:{blend}",
        }
        definitions = []
        if mask:
            name = f"mask{next(self.bindings.ids)}"
            attrs["clip-path"] = f"url(#{name})"
            definitions.append(Svg("clipPath", {"id": name}, (self.rect(mask, radius=radius),)))
        if blur:
            name = f"blur{next(self.bindings.ids)}"
            attrs["filter"] = f"url(#{name})"
            definitions.append(
                Svg(
                    "filter",
                    {"id": name, "x": "-10%", "y": "-10%", "width": "120%", "height": "130%"},
                    (Svg("feGaussianBlur", {"stdDeviation": blur}),),
                )
            )
        return Svg("g", attrs, (*children, *definitions))

    def image(self, source: Path, box: Box, *, video: bool = False) -> Svg:
        """Bind each image once and each clip to its enclosing source scene clock."""
        if video:
            name = f"clip{next(self.bindings.ids)}"
            self.bindings.clips.append(
                fframes.VideoBinding(
                    name=name,
                    source=source,
                    loop=True,
                    start_at=(self.window.first - self.bindings.first) / FPS,
                    duration=(self.window.end - self.window.first) / FPS,
                    offset=((self.window.first - self.window.scene_first) / FPS)
                    % fframes.probe_video(source).duration,
                )
            )
            href = f"video:{name}"
        else:
            if source not in self.bindings.images:
                self.bindings.images[source] = f"image{next(self.bindings.ids)}"
            href = f"image:{self.bindings.images[source]}"
        x, y, w, h = box
        return Svg("image", {"href": href, "x": x, "y": y, "width": w, "height": h})

    def shader(self, program: fframes.Shader, box: Box = (0, 0, WIDTH, HEIGHT)) -> Svg:
        """Give the raw binding exactly the same local interval as the scene."""
        name = f"shader{next(self.bindings.ids)}"
        self.bindings.shaders.append(
            fframes.ShaderBinding(
                name=name,
                shader=program,
                start_at=(self.window.first - self.bindings.first) / FPS,
                duration=(self.window.end - self.window.first) / FPS,
            )
        )
        x, y, w, h = box
        return Svg("image", {"href": f"shader:{name}", "x": x, "y": y, "width": w, "height": h})

    def fade(self) -> Svg:
        """Write the source's vertical fade with a unique paint server."""
        name = f"fade{next(self.bindings.ids)}"
        gradient = Svg(
            "linearGradient",
            {"id": name, "x2": 0, "y2": 1},
            (
                Svg("stop", {"offset": 0, "stop-color": "#0b0b0b", "stop-opacity": 0}),
                Svg("stop", {"offset": 1, "stop-color": "#0b0b0b", "stop-opacity": 0.9}),
            ),
        )
        return Svg(
            "g",
            children=(
                Svg("defs", children=(gradient,)),
                self.rect((0, 600, 1920, 480), f"url(#{name})"),
            ),
        )


def build(backend: Backend = "vulkan", *, frame: int | None = None) -> fframes.Video:
    """Prepare the full upstream intro or one original global frame entirely offline."""
    assets = files("intro")
    fonts = tuple(v for v in assets.values() if v.suffix == ".ttf")
    layout = fframes.TextLayout(fonts=fonts)
    first, end = (0, FRAMES) if frame is None else (frame, frame + 1)
    bindings = Bindings(first=first)

    def factory(window: Window) -> Native:
        painter = Native(window, assets, layout)
        painter.bindings = bindings
        return painter

    fragments: list[list[str]] = [[] for _ in range(end - first)]
    for window, node in pieces(factory, first, end):
        for i in range(window.end - window.first):
            fragments[window.first - first + i].append(node.frame(i))
    top = overlay(factory(Window(first, end, 0, 0)))
    frames = tuple(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
        '<rect width="1920" height="1080" fill="#0b0b0b"/>'
        + "".join(nodes)
        + top.frame(i)
        + "</svg>"
        for i, nodes in enumerate(fragments)
    )
    return fframes.Video(
        config=fframes.VideoConfig(
            width=WIDTH, height=HEIGHT, fps=FPS, fonts=fonts, backend=backend
        ),
        frames=frames,
        images=tuple(
            fframes.ImageBinding(name=name, source=path) for path, name in bindings.images.items()
        ),
        shaders=tuple(bindings.shaders),
        clips=tuple(bindings.clips),
        audio=soundtrack(assets) if frame is None else (),
    )


def main() -> None:
    """Render the intro or inspect a frame in output/native."""
    args = arguments()
    output = Path("output/native")
    output.mkdir(parents=True, exist_ok=True)
    video = build(args.backend, frame=args.frame)
    if args.frame is None:
        video.render(output / "intro.mp4", options=fframes.RenderOptions(concurrency=2))
    else:
        video.save_png(output / f"intro_{args.frame}.png")


if __name__ == "__main__":
    main()
