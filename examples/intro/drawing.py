"""Beat math and reusable typography, independent of either authoring API."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, Literal, TypeAlias, TypeVar

import numpy as np
from numpy.typing import NDArray

from fframes import Font, Shader, TextLayout

FPS, WIDTH, HEIGHT, FRAMES = 60, 1920, 1080, 7650
BEAT, DOWNBEAT = float(np.float32(0.454522)), float(np.float32(2.14851))
BG, BONE, ORANGE, EMBER = "#0b0b0b", "#ece8e1", "#fb6a22", "#8a3712"
GREY, DIM, PAPER, INK = "#76726c", "#2b2926", "#e8e4db", "#121110"
DISPLAY, COND, MONO, SERIF = "Archivo Black", "Anton", "IBM Plex Mono", "Instrument Serif"
Pixels: TypeAlias = NDArray[np.float64]
Number: TypeAlias = float | Pixels
Words: TypeAlias = str | tuple[str, ...]
Box: TypeAlias = tuple[Number, Number, Number, Number]
Matrix: TypeAlias = tuple[Number, Number, Number, Number, Number, Number]
Anchor: TypeAlias = Literal["start", "middle", "end"]
N = TypeVar("N")


def beat_frame(beat: float) -> int:
    """Match the upstream f32 beat grid and positive round-to-nearest rule."""
    time = np.float32(DOWNBEAT) + np.float32(beat) * np.float32(BEAT)
    return int(np.floor(np.float32(time * FPS) + 0.5))


def prog(value: Pixels, a: float, b: float) -> Pixels:
    """Clamp progress on an interval."""
    return np.clip((value - a) / (b - a), 0, 1)


def out(value: Pixels) -> Pixels:
    """Evaluate the source exponential ease-out, including its exact endpoint."""
    value = np.clip(value, 0, 1)
    return np.where(value >= 1, 1, 1 - np.exp2(-10 * value))


def enter(value: Pixels) -> Pixels:
    """Evaluate the source exponential ease-in, including its exact endpoint."""
    value = np.clip(value, 0, 1)
    return np.where(value <= 0, 0, np.exp2(10 * value - 10))


def cubic(value: Pixels) -> Pixels:
    """Symmetric cubic easing."""
    return np.where(value < 0.5, 4 * value**3, 1 - (-2 * value + 2) ** 3 / 2)


def spring(value: Pixels, stiffness: float = 320, damping: float = 22) -> Pixels:
    """Sample the source damped oscillator in one NumPy pass."""
    time = np.maximum(value, 0) * BEAT
    w0 = np.sqrt(stiffness)
    zeta = damping / (2 * w0)
    wd = w0 * np.sqrt(1 - zeta**2)
    return np.where(
        value <= 0,
        0,
        1 - np.exp(-zeta * w0 * time) * (np.cos(wd * time) + zeta * w0 / wd * np.sin(wd * time)),
    )


def pulse(value: Pixels, sharpness: float) -> Pixels:
    """Restart an exponential pulse on every beat."""
    return np.exp(-(value - np.floor(value)) * sharpness)


def noise(value: Number) -> Pixels:
    """Keep f32 arithmetic for the original deterministic procedural hash."""
    value32 = np.asarray(value, dtype=np.float32)
    hashed = np.sin(value32 * np.float32(127.1) + np.float32(311.7)) * np.float32(43758.547)
    return np.asarray(hashed - np.floor(hashed), dtype=np.float64)


def typed(text: str, counts: Pixels) -> tuple[str, ...]:
    """Reveal a prefix without splitting Unicode code points."""
    return tuple(text[: max(0, int(n))] for n in counts)


def timecode(seconds: Pixels) -> tuple[str, ...]:
    """Format the original four-part frame timecode."""
    frames = np.asarray(np.asarray(seconds, dtype=np.float32) * FPS, dtype=np.int64)
    return tuple(f"00:{n // 3600 % 60:02}:{n // 60 % 60:02}:{n % 60:02}" for n in frames)


@dataclass(frozen=True)
class Pen:
    """An SVG outline shared by the two example painters."""

    color: Words = BONE
    width: float = 1
    dash: tuple[Number, ...] = ()
    offset: Number = 0


@dataclass(frozen=True)
class Window:
    """A render interval with the enclosing source scene's clock preserved."""

    first: int
    end: int
    scene_first: int
    beat: float


class Painter(ABC, Generic[N]):
    """Small drawing vocabulary used only to share this example's choreography."""

    def __init__(self, window: Window, assets: dict[str, Path], layout: TextLayout) -> None:
        """Create local sample arrays; slicing scenes never restarts their choreography."""
        self.window, self.assets, self.layout = window, assets, layout
        self.metrics: dict[tuple[str, str, int, int, bool], float] = {}
        self.frames = np.arange(window.first, window.end, dtype=np.float64)
        self.seconds = np.asarray(np.asarray(self.frames, dtype=np.float32) / FPS, dtype=np.float64)
        self.b = (
            np.asarray(
                (self.seconds.astype(np.float32) - np.float32(DOWNBEAT)) / np.float32(BEAT),
                dtype=np.float64,
            )
            - window.beat
        )
        self.local_seconds = (self.frames - window.scene_first) / FPS

    def measure(
        self, text: str, family: str, size: int, weight: int = 400, italic: bool = False
    ) -> float:
        """Cache source integer font advances within this scene's lifetime."""
        key = text, family, size, weight, italic
        if key not in self.metrics:
            self.metrics[key] = float(
                self.layout.width(
                    text,
                    Font(
                        family=family,
                        size=size,
                        weight=weight,
                        style="italic" if italic else "normal",
                    ),
                )
            )
        return self.metrics[key]

    @abstractmethod
    def rect(
        self,
        box: Box,
        fill: Words | None = BONE,
        *,
        pen: Pen | None = None,
        radius: Number = 0,
        alpha: Number = 1,
    ) -> N:
        """Draw a rectangle with optional animated geometry."""

    @abstractmethod
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
    ) -> N:
        """Draw baseline-anchored text or a precomputed text sequence."""

    @abstractmethod
    def circle(
        self,
        x: Number,
        y: Number,
        radius: Number,
        fill: Words | None = BONE,
        *,
        pen: Pen | None = None,
        alpha: Number = 1,
    ) -> N:
        """Draw a circle around its explicit center."""

    @abstractmethod
    def path(self, data: str, pen: Pen, *, alpha: Number = 1) -> N:
        """Draw an unfilled path with an optional sampled stroke reveal."""

    @abstractmethod
    def group(
        self,
        children: tuple[N, ...],
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
    ) -> N:
        """Transform, clip and composite children in order."""

    @abstractmethod
    def image(self, source: Path, box: Box, *, video: bool = False) -> N:
        """Place cached artwork or a looping synchronized source clip."""

    @abstractmethod
    def shader(self, program: Shader, box: Box = (0, 0, WIDTH, HEIGHT)) -> N:
        """Bind a shader using this scene's local clock."""

    @abstractmethod
    def fade(self) -> N:
        """Overlay the source's transparent-to-dark vertical gradient."""

    @abstractmethod
    def ordered(self, children: tuple[N, ...], depths: tuple[Pixels, ...]) -> N:
        """Paint sampled depth keys from low to high while preserving ties."""

    def label(
        self,
        x: Number,
        y: Number,
        content: Words,
        color: Words = GREY,
        size: int = 18,
        anchor: Anchor = "start",
        alpha: Number = 1,
    ) -> N:
        """Use the original shared monospace label style."""
        return self.text(
            x,
            y,
            content,
            size,
            color,
            family=MONO,
            weight=500,
            spacing=2.5,
            anchor=anchor,
            alpha=alpha,
        )

    def corners(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        arm: float,
        color: str = BONE,
        width: float = 2,
    ) -> N:
        """Draw eight crop-mark arms as one path."""
        d = (
            f"M{x} {y + arm}V{y}H{x + arm} M{x + w - arm} {y}H{x + w}V{y + arm} "
            f"M{x + w} {y + h - arm}V{y + h}H{x + w - arm} M{x + arm} {y + h}H{x}V{y + h - arm}"
        )
        return self.path(d, Pen(color, width))

    def callout(
        self,
        target: tuple[float, float],
        end: tuple[float, float],
        text: str,
        progress: Pixels,
        color: str = ORANGE,
    ) -> N:
        """Draw the original elbow, rings and delayed label."""
        tx, ty = target
        lx, ly = end
        distance = abs(lx - tx) + abs(ly - ty) + 0.02
        return self.group(
            (
                self.circle(tx, ty, 5, color, alpha=progress),
                self.circle(tx, ty, 12, None, pen=Pen(color, 1.5), alpha=progress * 0.6),
                self.path(
                    f"M{tx} {ty}H{lx}V{ly}", Pen(color, 1.5, (distance * progress, distance))
                ),
                self.text(
                    lx + (10 if lx >= tx else -10),
                    ly + 6,
                    text,
                    20,
                    color,
                    family=MONO,
                    weight=500,
                    spacing=2,
                    anchor="start" if lx >= tx else "end",
                    alpha=np.clip((progress - 0.6) / 0.4, 0, 1),
                ),
            )
        )

    def slam(
        self,
        x: Number,
        y: Number,
        text: Words,
        size: int,
        since: Pixels,
        dx: float = 0,
        dy: float = 150,
        color: str = BONE,
        family: str = DISPLAY,
        anchor: Anchor = "start",
        italic: bool = False,
    ) -> N:
        """Spring type into place with the three original lagging colored trails."""
        motion = 1 - spring(since)
        copies = []
        for lag, tint, opacity in (
            (0.16, EMBER, 0.35),
            (0.10, "#c4531c", 0.5),
            (0.05, ORANGE, 0.65),
            (0, color, 1),
        ):
            offset = 1 - spring(since - lag)
            distance = np.abs(offset - motion) * np.hypot(dx, dy)
            visible = (
                prog(since, 0, 0.06)
                if lag == 0
                else np.where(
                    (distance > 2) & (since > lag * 0.5), opacity * np.minimum(distance / 40, 1), 0
                )
            )
            copies.append(
                self.text(
                    x + offset * dx,
                    y + offset * dy,
                    text,
                    size,
                    tint,
                    family=family,
                    spacing=0 if italic else -size * 0.035,
                    anchor=anchor,
                    italic=italic,
                    alpha=visible,
                )
            )
        return self.group(tuple(copies))
