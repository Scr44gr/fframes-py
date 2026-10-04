"""Timing and original scene data shared by the beta announcement ports."""

from dataclasses import dataclass
from math import floor
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from examples.assets import files
from examples.shared.marketing import Prepared as Marketing
from examples.shared.marketing import prepare as marketing
from fframes import AudioData, Keyframe, Samples, Spring, compile_animation

WIDTH, HEIGHT, FPS = 1920, 1080, 60
SCENES = ((0, 180), (180, 380), (380, 520), (520, 1000), (982, 1282), (1282, 1782), (1782, 1902))
TITLES = (
    '"Hello world" video',
    "Marketing Pitch Video",
    "Podcast Visualization",
    "TikTok-like video",
)
MESSAGES = (
    (370, "john", "John Doe", "Hey, How I can export the .webm video?"),
    (450, "dmitriy", "Dmitriy Kovalenko", "Just change out file extension to .webm"),
    (530, "torvalds", "Linus Torvalds", "https://github.com/torvalds"),
    (620, "me", "Me", "https://github.com/theawesome"),
)
BRACKETS = (
    "M832 439V415C832 402.297 842.297 392 855 392H882",
    "M1086 392H1110C1122.7 392 1133 402.297 1133 415V442",
    "M1133 650V674C1133 686.703 1122.7 697 1110 697H1083",
    "M879 697H855C842.297 697 832 686.703 832 674V647",
)
GITHUB = (
    "M12 2C6.477 2 2 6.477 2 12c0 4.419 2.865 8.166 6.839 9.489.5.09.682-.218.682-.484 "
    "0-.236-.009-.866-.014-1.699-2.782.602-3.369-1.34-3.369-1.34-.455-1.157-1.11-1.465-1.11-1.465"
    "-.909-.62.069-.608.069-.608 1.004.071 1.532 1.03 1.532 1.03.891 1.529 2.341 1.089 2.91.833"
    ".091-.647.349-1.086.635-1.337-2.22-.251-4.555-1.111-4.555-4.943 0-1.091.39-1.984 1.03-2.682"
    "-.103-.254-.447-1.27.097-2.646 0 0 .84-.269 2.75 1.025A9.548 9.548 0 0112 6.836c.85.004 "
    "1.705.114 2.504.336 1.909-1.294 2.748-1.025 2.748-1.025.546 1.376.202 2.394.1 2.646.64.699 "
    "1.026 1.591 1.026 2.682 0 3.841-2.337 4.687-4.565 4.935.359.307.679.917.679 1.852 0 1.335"
    "-.012 2.415-.012 2.741 0 .269.18.579.688.481A9.997 9.997 0 0022 12c0-5.523-4.477-10-10-10z"
)


def key(start: float, end: float, a: float, b: float, spring: Spring | None = None) -> Keyframe:
    """Describe a finite source interval, retaining the upstream spring parameters."""
    return Keyframe(start=start, end=end, from_value=a, to_value=b, easing=spring or "linear")


def sample(*keys: Keyframe, count: int = 500) -> Samples:
    """Evaluate curves once in Rust; both authors use the same samples."""
    return Samples(values=tuple(compile_animation(keys).sample_many(range(count), FPS)), fps=FPS)


@dataclass(frozen=True)
class Prepared:
    """Pinned resources, local scene curves and one writable phone spectrum buffer."""

    assets: dict[str, Path]
    fonts: tuple[Path, ...]
    frames: int
    motion: dict[str, Samples]
    heights: NDArray[np.float32]
    counters: tuple[str, ...]
    ferris: Marketing


def prepare(family: str, fonts: tuple[Path, ...]) -> Prepared:
    """Preserve scene overlap and soundtrack tail; make the random FPS readout repeatable."""
    assets = files("beta")
    audio = AudioData(source=assets["beta_audio"])
    frames = max(1902, floor(audio.duration * FPS))
    spectrum = audio.spectrum(frames=480, fps=FPS, sample_size=16, smooth=3)
    values = np.frombuffer(spectrum.data, dtype="<f4").reshape(480, 8)[:, 1:7]
    heights = np.empty_like(values)
    np.multiply(values, 500, out=heights)
    np.maximum(heights, np.finfo(np.float32).tiny, out=heights)
    np.log10(heights, out=heights)
    np.multiply(heights, 10, out=heights)
    np.clip(heights, 4, 18, out=heights)
    spring = Spring(mass=1, stiffness=100, damping=16)
    title = Spring(mass=0.6, stiffness=300, damping=26)
    island = Spring(mass=1.6, stiffness=300, damping=26)
    scroll = Spring(mass=1, stiffness=140, damping=16)
    motion = {
        "welcome": sample(key(0, 10, -400, 260, spring)),
        "of": sample(key(0, 10, 1000, 660, spring)),
        "tilt": sample(key(0.3, 3.3, -0.4, 1.2)),
        "code_x": sample(key(0.2, 0.5, -500, 50), key(0.5, 3.8, 50, 65)),
        "code_alpha": sample(key(0.3, 0.8, 0, 1)),
        "ferris_x": sample(key(0, 3.8, 2444, 1245, Spring(mass=1.45, stiffness=130, damping=20))),
        "eye_right": sample(
            key(1.4, 1.54, 0, 50),
            key(1.7, 1.84, 50, 0),
            key(1.9, 2.04, 0, 50),
            key(2.1, 2.24, 50, 0),
        ),
        "eye_left": sample(
            key(1.4, 1.7, 0, 50), key(1.7, 1.9, 50, 0), key(1.9, 2.1, 0, 50), key(2.1, 2.3, 50, 0)
        ),
        "power_x": sample(key(0, 0.3, -400, 260, title), key(0.3, 2.2, 260, 310)),
        "render_x": sample(key(0, 0.3, 1900, 460, title), key(0.3, 2.2, 460, 410)),
        "progress": sample(key(0, 0.8, 900, 1000), key(1.1, 2.1, 1000, 1350)),
        "scan_alpha": sample(key(1.1, 1.4, 0, 1)),
        "button_scale": sample(key(2.5, 2.7, 1, 1.04)),
        "discord_y": sample(key(3, 13, 1800, 0, Spring(mass=0.4, stiffness=70, damping=16))),
        "message_y": sample(key(4.8, 14.8, 200, 0, Spring(mass=1, stiffness=240, damping=26))),
        "message_scale": sample(key(4.8, 14.8, 0.4, 1, Spring(mass=1, stiffness=220, damping=26))),
        "message_alpha": sample(key(4.8, 5, 0, 1)),
        "island_w": sample(
            key(0, 6.2, 120, 180, Spring(mass=1.6, stiffness=400, damping=26)),
            key(6.2, 16.2, 180, 348, island),
        ),
        "island_h": sample(key(6.2, 16.2, 40, 80, island)),
        "github_x": sample(key(0, 10, 1920, 0, Spring(mass=0.3, stiffness=90, damping=26))),
        "github_y": sample(key(0.8, 6.3, 0, -1700)),
        "examples_x": sample(key(0, 10, 200, 960, spring)),
        "hello_x": sample(key(0, 10, 1700, 960, spring)),
        "title_y": sample(
            key(2.6, 4.8, 0, -180, scroll),
            key(4.8, 6.8, -180, -380, scroll),
            key(6.8, 16.8, -380, -580, scroll),
        ),
        "logo_alpha": sample(key(0.1, 0.2, 0, 1)),
        "beta_alpha": sample(key(0.6, 0.8, 0, 1)),
        "beta_angle": sample(key(0.6, 0.8, -60, -25)),
    }
    jitter = np.random.default_rng(0).random(140, dtype=np.float32)
    base = sample(key(1.1, 1.9, 60, 100)).values
    counters = tuple(f"Rendering fps: {int(base[i] + float(jitter[i] * 4))}" for i in range(140))
    return Prepared(
        assets,
        (
            assets["dm_sans"],
            assets["jetbrains_mono"],
            assets["bubble"],
            assets["inter_regular"],
            *fonts,
        ),
        frames,
        motion,
        heights,
        counters,
        marketing(family, fonts),
    )
