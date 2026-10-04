"""Seeded photo choreography shared by both Pixel Memory authoring APIs."""

import argparse
import math
import re
from collections import deque
from dataclasses import dataclass
from functools import cache
from itertools import pairwise
from pathlib import Path
from random import Random
from typing import Literal, TypeAlias

import numpy as np
from numpy.typing import NDArray

from examples.assets import files
from fframes import (
    Font,
    ImageInfo,
    Keyframe,
    Samples,
    Spring,
    TextLayout,
    compile_animation,
    probe_image,
    probe_video,
)
from fframes.models import Easing

WIDTH, HEIGHT, FPS = 1920, 1080, 30
KINDS = ("float", "fibonacci", "polaroid", "spiral", "parallax", "video")
Kind: TypeAlias = Literal["float", "fibonacci", "polaroid", "spiral", "parallax", "video"]
SONGS = {
    "The_Farewell": (166.0, 1.12),
    "vostok_zapomny": (185.62, 1.08),
    "naruto_grief": (196.0, 1.22),
    "revenge": (132.0, 1.05),
}
INTRO = "They say dogs live shorter lives because they already know how to love unconditionally"
GOLD = (
    ("#ffffff", "#f5f0e0", "#e1c78c"),
    ("#f8f5e8", "#e8dfc0", "#c0b090"),
    ("#f0ebd8", "#d8cba8", "#a89870"),
)
CurveKey: TypeAlias = tuple[float, float, float, float, Easing]
Pixels: TypeAlias = NDArray[np.float64]


def curve(duration: float, *keys: CurveKey) -> Pixels:
    """Sample finite curves natively, shifting negative preroll into positive time."""
    shift = max(0.0, -min(k[0] for k in keys))
    animation = compile_animation(
        tuple(
            Keyframe(start=a + shift, end=b + shift, from_value=x, to_value=y, easing=e)
            for a, b, x, y, e in keys
        )
    )
    first = round(shift * FPS)
    return np.array(animation.sample_many(range(first, first + math.ceil(duration * FPS)), FPS))


def samples(values: Pixels) -> Samples:
    """Transfer one final sample sequence; NumPy intermediates remain shared views."""
    return Samples(values=tuple(map(float, values)), fps=FPS)


@dataclass(frozen=True)
class Photo:
    """One image, its sampled placement and optional developing-paper treatment."""

    source: Path
    size: tuple[float, float]
    position: tuple[float, float]
    x: Pixels
    y: Pixels
    scale: Pixels
    rotation: Pixels
    opacity: Pixels
    origin: tuple[float, float] = (0, 0)
    stroke: int = 24
    shadow: bool = False
    development: Pixels | None = None
    year: str = ""


@dataclass(frozen=True)
class Shot:
    """A source scene with its outgoing overlap and resolved media."""

    kind: Kind
    duration: float
    overlap: float
    photos: tuple[Photo, ...] = ()
    video: Path | None = None
    video_size: tuple[float, float] = (1920, 1080)


@dataclass(frozen=True)
class Bokeh:
    """A soft circle with shared global motion and a final heart coordinate."""

    x: Pixels
    y: Pixels
    radius: float
    opacity: float
    palette: int
    blur: float


@dataclass(frozen=True)
class Prepared:
    """Resolved scenes and local resources; no rendering-time file discovery."""

    duration: float
    assets: dict[str, Path]
    fonts: tuple[Path, ...]
    bokeh: tuple[Bokeh, ...]
    scenes: tuple[tuple[int, Shot], ...]
    intro_duration: float
    lines: tuple[str, ...]
    final_start: int
    final_duration: float
    final_path: str
    song: str


class Gallery:
    """Consume shuffled media without repetition; bound rejection sampling."""

    def __init__(self, assets: dict[str, Path], seed: int) -> None:
        """Use a private generator so rebuilding never depends on process-global state."""
        self.rng = Random(seed)  # noqa: S311 - Reproducible visual choreography, not secrets.
        images = sorted((p for p in assets.values() if p.suffix == ".jpg"), key=lambda p: p.name)
        videos = sorted((p for p in assets.values() if p.suffix == ".mp4"), key=lambda p: p.name)
        self.rng.shuffle(images)
        self.rng.shuffle(videos)
        self.images = deque(images)
        self.videos = deque(videos)
        self.fibonacci_count = 0

    @staticmethod
    @cache
    def info(path: Path) -> ImageInfo:
        """Read dimensions and EXIF only once for photos that are actually selected."""
        return probe_image(path)

    def choose(self, count: int = 1) -> tuple[Path, ...]:
        """Fail explicitly if the user-supplied collection cannot fill a scene."""
        if count > len(self.images):
            raise ValueError("not enough unused photos for the selected soundtrack")
        return tuple(self.images.popleft() for _ in range(count))

    def fit(self, path: Path, size: float) -> tuple[float, float]:
        """Retain source aspect ratio and the original floating placement dimensions."""
        info = self.info(path)
        ratio = info.width / info.height
        return (size, size / ratio) if ratio > 1 else (size * ratio, size)

    def floating(self, tempo: float) -> Shot:
        """Move one photograph into view, let it drift, then leave along one axis."""
        rng = self.rng
        (path,) = self.choose()
        width, height = self.fit(path, 950)
        horizontal = rng.random() < 0.5
        a, b, duration = tempo * 3, tempo * 7, tempo * 10
        start = (2120, 540) if horizontal else (960, 1280)
        end = (-950, 540) if horizontal else (960, -950)
        middle = (960 + rng.uniform(-30, 30), 540 + rng.uniform(-30, 30))
        scale = rng.uniform(1, 1.3)
        final_scale = rng.uniform(0.7, 0.9)
        transforms = tuple(
            curve(
                duration,
                (0, a, x, c, "ease_out"),
                (a, b, c, m, "ease_in_out"),
                (b, duration, m, e, "ease_in"),
            )
            for x, c, m, e in zip(
                (*start, 0.9), (960, 540, 1), (*middle, scale), (*end, final_scale), strict=True
            )
        )
        rotate = rng.uniform(-2, 2)
        rotation = curve(
            duration,
            (0, a, rng.uniform(-5, 5), 0, "ease_out"),
            (a, tempo * 5, 0, rotate, "ease_in_out"),
            (tempo * 5, b, rotate, 1, "ease_in_out"),
            (b, duration, 1, rng.uniform(-5, 5), "ease_in"),
        )
        x, y, scales = transforms
        x -= width / 2
        y -= height / 2
        return Shot(
            "float",
            duration,
            0.4,
            (
                Photo(
                    path,
                    (int(width), int(height)),
                    (0, 0),
                    x,
                    y,
                    scales,
                    rotation,
                    np.ones_like(x),
                    origin=(960, 540),
                    stroke=48,
                ),
            ),
        )

    def fibonacci(self, tempo: float) -> Shot:
        """Fade in, then follow the original golden-ratio spiral out of view."""
        (path,) = self.choose()
        rng = self.rng
        width, height = self.fit(path, rng.randrange(1200, 1400))
        direction = -1 if self.fibonacci_count % 2 == 0 else 1
        self.fibonacci_count += 1
        revolutions = rng.uniform(1, 3)
        spiral = tempo * revolutions * math.pi
        radius = rng.uniform(350, 650)
        duration = tempo * 3 + spiral
        t = np.arange(math.ceil(duration * FPS), dtype=np.float64) / FPS
        entry = np.clip(t / tempo, 0, 1)
        p = np.clip((t - tempo * 3) / spiral, 0, 1)
        theta = direction * p**0.6 * revolutions * math.tau
        b = math.log((1 + math.sqrt(5)) / 2) / math.tau
        r = radius * np.exp(b * np.abs(theta)) / math.exp(b * revolutions * math.tau) * p**0.8
        blend = p**0.3
        r *= blend
        r += 0.1 * (1 - blend)
        x = np.where(t < tempo * 3, 960, 960 + r * np.cos(theta))
        y = np.where(t < tempo * 3, 540, 540 + r * np.sin(theta))
        scale = np.where(t < tempo, 0.7 + 0.3 * entry, 1 - 0.9 * p)
        opacity = np.where(t < tempo, entry, 1 - p**0.7)
        return Shot(
            "fibonacci",
            duration,
            spiral * 0.3,
            (
                Photo(
                    path,
                    (int(width), int(height)),
                    (-width / 2, -height / 2),
                    x,
                    y,
                    scale,
                    direction * p * 25,
                    opacity,
                    shadow=True,
                ),
            ),
        )

    def spiral(self, tempo: float) -> Shot:
        """Stack six to ten photographs using spring entrances and an outward exit."""
        rng = self.rng
        paths = self.choose(rng.randint(6, 10))
        duration = len(paths) * tempo * 4 + rng.uniform(5, 8)
        photos = []
        phi = (1 + math.sqrt(5)) / 2
        for i, path in enumerate(paths):
            theta = i * math.pi / 2
            radius = 60 * phi ** (theta / math.pi)
            end_x = min(1370, max(550, 960 + radius * math.cos(theta)))
            end_y = min(530, max(550, 540 + radius * math.sin(theta)))
            side = i % 4
            start_x, start_y = (
                (rng.uniform(0, WIDTH), -200)
                if side == 0
                else (2120, rng.uniform(0, HEIGHT))
                if side == 1
                else (rng.uniform(0, WIDTH), 1280)
                if side == 2
                else (-200, rng.uniform(0, HEIGHT))
            )
            spring = Spring(
                stiffness=rng.uniform(30, 45), mass=rng.uniform(4, 5), damping=rng.uniform(20, 35)
            )
            middle = (
                end_x + rng.uniform(-10, 10),
                end_y + rng.uniform(-10, 10),
                1 + rng.uniform(0, 0.02),
            )
            end = (
                2000 if rng.random() < 0.5 else -2000,
                2000 if rng.random() < 0.5 else -2000,
                rng.uniform(0.1, 0.8),
            )
            a, b, c = i * tempo * 4, (i + 1) * tempo * 4, duration - 0.5
            x, y, scale = (
                curve(
                    duration,
                    (a, b, s, f, spring),
                    (b, c, f, m, "ease_in_out"),
                    (c, duration, m, e, "ease_in_out"),
                )
                for s, f, m, e in zip(
                    (start_x, start_y, 0.1), (end_x, end_y, 1), middle, end, strict=True
                )
            )
            initial, final = rng.uniform(-20, 20), rng.uniform(-5, 5)
            rotation = curve(
                duration,
                (a, b, initial, final, "ease_out"),
                (b, c, final, final + rng.uniform(-2, 2), "ease_in_out"),
                (c, duration, final + rng.uniform(-2, 2), final + rng.uniform(30, 60), "ease_in"),
            )
            opacity = curve(
                duration, (a, a + tempo * 0.8, 0, 1, "ease_out"), (c, duration, 1, 0, "ease_in")
            )
            w, h = self.fit(path, 1000)
            photos.append(
                Photo(
                    path,
                    (int(w), int(h)),
                    (-w / 2, -h / 2),
                    x,
                    y,
                    scale,
                    rotation,
                    opacity,
                    shadow=True,
                )
            )
        return Shot("spiral", duration, 0.5, tuple(photos))

    def parallax(self, tempo: float) -> Shot:
        """Scroll two photographic planes at their original relative speeds."""
        rng = self.rng
        main = self.choose(rng.randint(2, 4))
        background = self.choose(len(main) * 3)
        pause, enter = rng.uniform(0.2, 0.3), tempo * rng.uniform(1.5, 2.5)
        end = len(main) * tempo * 4 - pause + rng.uniform(0.3, 0.7)
        duration = end - 0.5
        main_y = -curve(
            duration,
            (0, enter - pause, -1080, 0, "ease_out"),
            *(
                (
                    i * tempo * 4 + pause + enter,
                    (i + 1) * tempo * 4 - pause,
                    i * 1080,
                    (i + 1) * 1080,
                    "ease_in_out",
                )
                for i in range(len(main))
            ),
        )
        bg_y = -curve(duration, (0, end, -1080, (len(background) + 2) * 400, "linear"))
        photos = []
        for paths, height, motion, stroke in ((background, 350, bg_y, 0), (main, 800, main_y, 48)):
            for i, path in enumerate(paths):
                info = self.info(path)
                width = info.width / info.height * height
                pos = (
                    ((1440 if i % 2 == 0 else 480), 400 // 3 if i == 0 else i * 400)
                    if not stroke
                    else (960, 1080 * i + 140)
                )
                constant = np.ones_like(motion)
                photos.append(
                    Photo(
                        path,
                        (width if not stroke else int(width), height),
                        pos,
                        constant * (-width / 2),
                        motion,
                        constant * (1.2 if not stroke else 1),
                        constant * 0,
                        constant * (0.85 if not stroke else 1),
                        origin=(960, 540) if not stroke else (0, 0),
                        stroke=stroke,
                    )
                )
        return Shot("parallax", duration, 0.3, tuple(photos))

    def polaroid(self, tempo: float) -> Shot:
        """Develop dated prints with bounded, gradually relaxed spacing constraints."""
        rng = self.rng
        paths = self.choose(rng.randint(4, 8))
        end = tempo * 4 * len(paths) + tempo * rng.uniform(1, 2)
        duration = end + 0.5
        active_w, active_h = WIDTH * rng.uniform(0.9, 1), HEIGHT * rng.uniform(0.9, 1)
        active_x, active_y = rng.uniform(0, WIDTH - active_w), rng.uniform(0, HEIGHT - active_h)
        layout_w = min(WIDTH * rng.uniform(0.52, 0.60), HEIGHT * rng.uniform(0.62, 0.72))
        layout_h = min(HEIGHT * rng.uniform(0.68, 0.8), layout_w * rng.uniform(1.12, 1.24))
        margin = max(max(layout_w, layout_h) * 0.15, 40)
        limits = []
        for origin, extent, size, canvas in (
            (active_x, active_w, layout_w, WIDTH),
            (active_y, active_h, layout_h, HEIGHT),
        ):
            safe = size / 2 + margin
            low, high = origin + safe, origin + extent - safe
            if low >= high:
                low, high = safe, canvas - safe
            limits.append((low, high) if low < high else (canvas * 0.25, canvas * 0.75))
        centers: list[tuple[float, float]] = []
        photos = []
        for i, path in enumerate(paths):
            distance = (0.4 * max(layout_w, layout_h)) ** 2
            for attempt in range(10000):
                cx, cy = rng.uniform(*limits[0]), rng.uniform(*limits[1])
                if all((cx - px) ** 2 + (cy - py) ** 2 >= distance for px, py in centers):
                    break
                if attempt % 49 == 48:
                    distance *= 0.85
            else:
                raise ValueError("photo placement failed to converge")
            centers.append((cx, cy))
            target = (cx - layout_w / 2, cy - layout_h / 2, rng.uniform(-4, 4))
            last = (
                target[0] + rng.uniform(-10, 10),
                target[1] + rng.uniform(-10, 10),
                target[2] + rng.uniform(-1, 1),
            )
            exit_to = (
                -2000 if i % 2 == 0 else 2000,
                -2000 if (i + i // 2) % 2 == 0 else 2000,
                last[2],
            )
            a = i * tempo * 3
            x, y, rotation = (
                curve(
                    duration,
                    (a - 0.5, a + 0.5, s, t, "ease_out"),
                    (a + 0.5, end, t, last_value, "ease_in_out"),
                    (end, duration, last_value, e, "ease_in"),
                )
                for s, t, last_value, e in zip(
                    (target[0], -layout_h, 0), target, last, exit_to, strict=True
                )
            )
            development = curve(duration, (a, a + tempo * 2, 0, 1, "ease_out"))
            opacity = curve(duration, (a - 0.5, a + 0.5, 0, 1, "ease_out"))
            info = self.info(path)
            ratio = info.width / info.height
            w, h = 1152.0, 1152 / ratio
            if h > 864:
                w, h = 864 * ratio, 864
            if w < 450 and w < h:
                w, h = 450, 450 / ratio
            elif h < 450 and h < w:
                w, h = 450 * ratio, 450
            year = next(
                (
                    field.value[:4]
                    for field in info.exif
                    if field.ifd == 0 and field.tag == "DateTimeOriginal"
                ),
                "",
            )
            overrides = {
                "055.jpg": "1996",
                "049.jpg": "2003",
                "024.jpg": "2003",
                "031.jpg": "2003",
                "030.jpg": "2018",
                "042.jpg": "2006",
                "058.jpg": "2001",
                "041.jpg": "",
                "060.jpg": "",
            }
            photos.append(
                Photo(
                    path,
                    (w, h),
                    (14, 14),
                    x,
                    y,
                    np.ones_like(x),
                    rotation,
                    opacity,
                    origin=((w + 28) / 2, (h + 74) / 2),
                    shadow=True,
                    development=development,
                    year=overrides.get(path.name, year),
                )
            )
        return Shot("polaroid", duration, 0.3, tuple(photos))

    def shot(self, kind: Kind, tempo: float) -> Shot | None:
        """Dispatch scene constructors explicitly, with no dynamic attribute lookups."""
        match kind:
            case "float":
                return self.floating(tempo)
            case "fibonacci":
                return self.fibonacci(tempo)
            case "spiral":
                return self.spiral(tempo)
            case "parallax":
                return self.parallax(tempo)
            case "polaroid":
                return self.polaroid(tempo)
            case "video":
                if not self.videos:
                    return None
                path = self.videos.popleft()
                info = probe_video(path)
                return Shot(
                    "video", info.duration, 0, video=path, video_size=(info.width, info.height)
                )


def bokeh(rng: Random, duration: float) -> tuple[Bokeh, ...]:
    """Reproduce the two drifting waves, scattered lights and final heart outline."""

    def deviation(times: tuple[float, ...]) -> Pixels:
        points = (0, 20, 0, -20, 0, 20, -20, 0, 20, 0, -20, 0, 20, 0)
        # Evaluate a loop at exact source seconds, independent of a fractional period.
        keys = tuple(
            Keyframe(start=a, end=b, from_value=points[i], to_value=points[i + 1])
            for i, (a, b) in enumerate(pairwise(times))
        )
        animation = compile_animation(keys)
        # Both periods (28.7 and 32) land on the 30 fps grid.
        one = np.asarray(animation.sample_many(range(round(times[-1] * FPS)), FPS))
        return np.resize(one, math.ceil(duration * FPS))

    drifts = (
        deviation((0, 2.8, 5.3, 7.9, 10.4, 13.1, 15.7, 18.2, 20.9, 23.5, 26.1, 28.7)),
        deviation((0, 2.3, 4.9, 7.2, 9.8, 12.1, 14.7, 17.3, 19.6, 22.2, 24.5, 27.1, 29.8, 32)),
    )
    count = rng.randrange(120, 140)
    main, secondary = count * 6 // 10, count * 3 // 10
    circles = []
    for i in range(count):
        if i < main:
            x = WIDTH * i / main
            sine = 250 * math.sin(x / WIDTH * math.tau * 1.3)
            dy = rng.uniform(-75, 75)
            x = min(1910, max(10, x + rng.uniform(-WIDTH / main * 0.3, WIDTH / main * 0.3)))
            y = min(1070, max(10, 540 + sine + dy))
            wave = abs(sine / 250)
            radius = (
                rng.uniform(20, 35)
                if wave < 0.3
                else rng.uniform(12, 25)
                if wave < 0.7
                else rng.uniform(5, 15)
            )
            opacity = (
                rng.uniform(0.5, 0.7)
                if radius > 25
                else rng.uniform(0.4, 0.6)
                if radius > 15
                else rng.uniform(0.3, 0.5)
            )
        elif i < main + secondary:
            x = WIDTH * (i - main) / secondary + WIDTH / (2 * secondary)
            y = min(
                1070,
                max(
                    10,
                    540 + 200 * math.sin(x / WIDTH * math.tau * 2 + 0.5) + rng.uniform(-150, 150),
                ),
            )
            x = min(
                1910, max(10, x + rng.uniform(-WIDTH / secondary * 0.4, WIDTH / secondary * 0.4))
            )
            radius, opacity = rng.uniform(3, 20), rng.uniform(0.2, 0.5)
        else:
            x, y, roll = rng.uniform(10, 1910), rng.uniform(10, 1070), rng.random()
            radius = (
                rng.uniform(20, 30)
                if roll > 0.9
                else rng.uniform(10, 20)
                if roll > 0.7
                else rng.uniform(3, 10)
            )
            opacity = rng.uniform(0.2, 0.5)
        palette = rng.randrange(3)
        factor = 1 - min(radius / 40, 0.7)
        ax, ay = rng.uniform(-1.5, 1.5) * factor, rng.uniform(-1.5, 1.5) * factor
        t = i / count * math.tau
        hx, hy = (
            960 + 16 * math.sin(t) ** 3 * 21.6,
            540
            - (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            * 21.6,
        )
        start = max(duration - 6, 0)
        px = curve(duration, (start, start + 3, x, hx, "ease_in_out"))
        py = curve(duration, (start, start + 3, y, hy, "ease_in_out"))
        px += drifts[i % 2] * ax
        py += drifts[i % 2] * ay
        circles.append(
            Bokeh(px, py, radius, opacity, palette, 8 if radius > 25 else 5 if radius > 15 else 2)
        )
    return tuple(circles)


def prepare(
    seed: int = 48,
    song: str = "revenge",
    scene: Kind | None = None,
    text: str = INTRO,
    family: str = "Indie Flower",
    fonts: tuple[Path, ...] = (),
) -> Prepared:
    """Select source scene algorithms deterministically, with all published music choices."""
    assets = files("pixel_memory")
    gallery = Gallery(assets, seed)
    duration, tempo = SONGS[song]
    circles = bokeh(gallery.rng, duration) if scene is None else ()
    scenes = []
    start_duration = tempo * gallery.rng.randint(4, 5) if scene is None else 0
    elapsed = start_duration - 3 if scene is None else 0
    current = math.floor(start_duration * FPS) - 3 * FPS if scene is None else 0
    for _ in range(1000):
        if scene is None and duration - elapsed <= 10:
            break
        chance = gallery.rng.randrange(50 if duration - elapsed > 20 else 20)
        kind = scene or (
            "float"
            if chance < 10
            else "fibonacci"
            if chance < 20
            else "polaroid"
            if chance < 25
            else "spiral"
            if chance < 30
            else "parallax"
            if chance < 40
            else "video"
        )
        shot = gallery.shot(kind, tempo)
        if shot is None:
            if scene is not None:
                raise ValueError("no video source is available")
            continue
        if scene is not None:
            scenes.append((0, shot))
            duration = shot.duration
            break
        contribution = shot.duration - shot.overlap
        if elapsed + contribution < duration - 3:
            scenes.append((current, shot))
            current += math.floor(shot.duration * FPS) - math.floor(shot.overlap * FPS)
            elapsed += contribution
    else:
        raise ValueError("scene selection failed to fit the soundtrack")
    fonts = (assets["pixel_spacegrotesk_medium_ttf"], *fonts)
    layout = TextLayout(fonts=fonts, load_system_fonts=True)
    if any(shot.kind == "polaroid" for _, shot in scenes):
        layout.width("2020", Font(family=family, size=44))
    lines = (
        layout.wrap(text, Font(family="Space Grotesk", size=124), 1600) if start_duration else ()
    )
    artwork = assets["pixel_final_scene_rs"].read_text(encoding="utf-8")
    path = re.search(r'\bd="([^"]+)"', artwork)
    if path is None:
        raise ValueError("the pinned final scene has no signature path")
    return Prepared(
        duration,
        assets,
        fonts,
        circles or bokeh(gallery.rng, duration),
        tuple(scenes),
        start_duration,
        lines,
        current if scene is None else math.ceil(duration * FPS),
        duration - elapsed,
        path[1],
        song,
    )


class Arguments(argparse.Namespace):
    """Select a repeatable slideshow or inspect one original scene algorithm."""

    seed: int
    song: str
    scene: Kind | None
    text: str
    family: str
    font: list[Path]


def arguments() -> Arguments:
    """Use the same flags in both implementations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=48)
    parser.add_argument("--song", choices=tuple(SONGS), default="revenge")
    parser.add_argument("--scene", choices=KINDS)
    parser.add_argument("--text", default=INTRO)
    parser.add_argument("--family", default="Indie Flower")
    parser.add_argument("--font", type=Path, action="append", default=[])
    return parser.parse_args(namespace=Arguments())
