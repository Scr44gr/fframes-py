"""Build the original intro from reusable typed components, without XML authoring."""

from pathlib import Path
from typing import Literal

import numpy as np

import fframes
from examples.assets import files
from examples.intro.drawing import (
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
from examples.intro.effects import scalar
from examples.intro.sequence import arguments, overlay, pieces, soundtrack
from fframes import compose as c
from fframes.compose.components import Item
from fframes.models import Backend
from fframes.values import Paint


def paint(value: Words | None) -> Paint | None:
    """Keep discrete palette changes as a single native color timeline."""
    if value is None or isinstance(value, str):
        return None if value == "none" else value
    if all(v == value[0] for v in value):
        return value[0]
    return c.ColorSamples(values=value, fps=FPS)


def stroke(pen: Pen | None) -> c.Stroke | None:
    """Reuse the validated shared stroke model."""
    if pen is None:
        return None
    color = paint(pen.color)
    assert color is not None  # noqa: S101 - Pen always contains a visible color.
    return c.Stroke(
        color=color,
        width=pen.width,
        dash=tuple(scalar(v) for v in pen.dash),
        dash_offset=scalar(pen.offset),
    )


class Composed(Painter[Item]):
    """Translate sampled choreography directly into public compose components."""

    def ordered(self, children: tuple[Item, ...], depths: tuple[Pixels, ...]) -> Item:
        """Sort depth in Rust; preserve each source image and component by reference."""
        return c.Composition(
            children=tuple(
                c.Composition(z_index=scalar(depth), children=(child,))
                for child, depth in zip(children, depths, strict=True)
            )
        )

    def rect(
        self,
        box: Box,
        fill: Words | None = BONE,
        *,
        pen: Pen | None = None,
        radius: Number = 0,
        alpha: Number = 1,
    ) -> Item:
        """Create an animated rectangle."""
        x, y, w, h = box
        return c.Rectangle(
            size=(scalar(w), scalar(h)),
            position=c.Position(x=scalar(x), y=scalar(y)),
            fill=paint(fill),
            stroke=stroke(pen),
            radius=scalar(radius),
            opacity=scalar(np.clip(alpha, 0, 1)),
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
    ) -> Item:
        """Shape text once and let native timelines select changing readouts."""
        return c.Text(
            content=content
            if isinstance(content, str) and content
            else c.TextFrames(frames=content if isinstance(content, tuple) else (content,)),
            position=c.Position(x=scalar(x), y=scalar(y)),
            anchor="baseline",
            text_anchor=anchor,
            font_family=family,
            font_weight=weight,
            font_size=size,
            letter_spacing=spacing,
            font_style="italic" if italic else "normal",
            fill=paint(fill),
            stroke=stroke(pen),
            opacity=scalar(np.clip(alpha, 0, 1)),
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
    ) -> Item:
        """Place a circle by its explicit center."""
        return c.Circle(
            radius=scalar(radius),
            position=c.Position(x=scalar(x - radius), y=scalar(y - radius)),
            fill=paint(fill),
            stroke=stroke(pen),
            opacity=scalar(np.clip(alpha, 0, 1)),
        )

    def path(self, data: str, pen: Pen, *, alpha: Number = 1) -> Item:
        """Use the path parser once, then animate only stroke values."""
        return c.VectorPath(
            segments=data,
            size=(WIDTH, HEIGHT),
            fill=None,
            stroke=stroke(pen),
            opacity=scalar(np.clip(alpha, 0, 1)),
        )

    def group(
        self,
        children: tuple[Item, ...],
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
    ) -> Item:
        """Group reusable items with native masks and compositing."""
        if not np.any(np.asarray(alpha) > 0):
            return c.Composition()
        return c.Composition(
            children=children,
            position=c.Position(x=scalar(x), y=scalar(y)),
            scale=scalar(scale),
            rotation=scalar(rotation),
            origin=origin,
            opacity=scalar(np.clip(alpha, 0, 1)),
            blend_mode=blend,
            mask=c.Mask(
                position=(scalar(mask[0]), scalar(mask[1])),
                size=(scalar(mask[2]), scalar(mask[3])),
                radius=scalar(radius),
            )
            if mask
            else None,
            filter=c.Filter(
                region=(-0.1, -0.1, 1.2, 1.3), steps=(c.Blur(result="blur", sigma=(blur, blur)),)
            )
            if blur
            else None,
            matrix=(
                scalar(matrix[0]),
                scalar(matrix[1]),
                scalar(matrix[2]),
                scalar(matrix[3]),
                scalar(matrix[4]),
                scalar(matrix[5]),
            )
            if matrix
            else None,
        )

    def image(self, source: Path, box: Box, *, video: bool = False) -> Item:
        """Reuse decoded source pixels while animating the enclosing transform."""
        x, y, w, h = box
        width = float(w[0]) if isinstance(w, np.ndarray) else w
        height = float(h[0]) if isinstance(h, np.ndarray) else h
        child = (
            c.VideoClip(
                source=source,
                size=(width, height),
                fit="contain",
                loop=True,
                offset=((self.window.first - self.window.scene_first) / FPS)
                % fframes.probe_video(source).duration,
            )
            if video
            else c.Image(source=source, size=(width, height), fit="contain")
        )
        return self.group((child,), matrix=(w / width, 0, 0, h / height, x, y))

    def shader(self, program: fframes.Shader, box: Box = (0, 0, WIDTH, HEIGHT)) -> Item:
        """Animate the shader resolution as well as its uniforms."""
        x, y, w, h = box
        return c.ShaderLayer(
            shader=program,
            size=(scalar(w), scalar(h)),
            position=c.Position(x=scalar(x), y=scalar(y)),
        )

    def fade(self) -> Item:
        """Use the typed gradient without introducing an SVG escape hatch."""
        return c.Rectangle(
            position=c.Position(y=600),
            size=(1920, 480),
            fill=c.LinearGradient(
                end=(0, 1),
                stops=(c.Stop(offset=0, color="#0b0b0b00"), c.Stop(offset=1, color="#0b0b0be6")),
            ),
        )


def build(backend: Backend = "vulkan", *, frame: int | None = None) -> c.Video:
    """Prepare the same beat timeline using typed components and shared Rust rendering."""
    assets = files("intro")
    fonts = tuple(v for v in assets.values() if v.suffix == ".ttf")
    layout = fframes.TextLayout(fonts=fonts)
    first, end = (0, FRAMES) if frame is None else (frame, frame + 1)

    def factory(window: Window) -> Composed:
        return Composed(window, assets, layout)

    children: list[Item] = [c.Rectangle(size=(WIDTH, HEIGHT), fill="#0b0b0b")]
    children.extend(
        node.at((window.first - first) / FPS, duration=(window.end - window.first) / FPS)
        for window, node in pieces(factory, first, end)
    )
    children.append(overlay(factory(Window(first, end, 0, 0))))
    if frame is None:
        children.extend(
            c.Audio(source=t.source, gain_db=t.gain_db, fade_out=t.fade_out).at(t.start_at)
            for t in soundtrack(assets)
        )
    return c.Video(
        resolution=(WIDTH, HEIGHT),
        fps=FPS,
        fonts=fonts,
        backend=backend,
        load_system_fonts=False,
        composition=c.Composition(duration=(end - first) / FPS, children=tuple(children)),
    )


def main() -> None:
    """Render the intro or inspect a frame in output/compose."""
    args = arguments()
    output = Path("output/compose")
    output.mkdir(parents=True, exist_ok=True)
    video = build(args.backend, frame=args.frame)
    if args.frame is None:
        video.render(output / "intro.mp4", options=fframes.RenderOptions(concurrency=2))
    else:
        video.save_png(output / f"intro_{args.frame}.png")


if __name__ == "__main__":
    main()
