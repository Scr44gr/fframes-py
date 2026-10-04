"""Chapter timing and measured labels shared by the two interview ports."""

import argparse
from dataclasses import dataclass
from itertools import pairwise
from math import floor
from pathlib import Path

from examples.assets import files
from fframes import AudioData, Font, Keyframe, Spring, TextLayout, compile_animation, probe_video
from fframes.models import Model, Seconds

WIDTH, HEIGHT, FPS = 1920, 1080, 24
CHAPTER_FONT = Font(family="Sofia Sans Semi Condensed", size=26)


class Chapter(Model):
    """An absolute start and a title; the timestamp label is derived."""

    start: Seconds
    title: str

    @property
    def label(self) -> str:
        """Format whole seconds in the original mm:ss style."""
        return f"{int(self.start) // 60:02}:{int(self.start) % 60:02}"


CHAPTERS = tuple(
    Chapter(start=start, title=title)
    for start, title in (
        (0, "Introduction to Lunch Bites Podcast"),
        (111, "Tech Sponsorships and Streaming Quality"),
        (153, "Flexing in LA: The Casa Bonita Experience"),
        (180, "Viral Moments: The Post-It Note Debate"),
        (291, "Zuckerberg's Rebranding and Tech Culture"),
        (895, "The Intersection of Geek Culture and Popularity"),
        (1008, "Psychedelic Fantasy Baseball and AI"),
        (1072, "The Rise of Meme Coins"),
        (1153, "Trump Coin and the Crypto Circus"),
        (1310, "Fart Coin: The AI Millionaire"),
        (1546, "OpenAI and the Future of AI Models"),
        (1810, "Influencers and the Coding Landscape"),
    )
)


@dataclass(frozen=True)
class Prepared:
    """Decoded durations, source dimensions and one batch of chapter animation."""

    assets: dict[str, Path]
    fonts: tuple[Path, ...]
    frames: int
    heights: tuple[float, ...]
    labels: tuple[str, ...]
    highlight: tuple[float, ...]


def prepare(family: str, fonts: tuple[Path, ...], chapters: tuple[Chapter, ...]) -> Prepared:
    """Fit immutable labels once and keep source video pixels in Rust."""
    if (
        not chapters
        or chapters[0].start != 0
        or any(b.start - a.start < 1 for a, b in pairwise(chapters))
    ):
        raise ValueError("chapters must start at zero and be at least one second apart")
    assets = files("teej_podcast")
    fonts = (assets["sofia"], *fonts)
    layout = TextLayout(fonts=fonts, load_system_fonts=True)
    layout.width("2D: Rust", Font(family=family, size=75))
    labels = tuple(
        chapter.label
        + "  "
        + layout.fit(
            chapter.title,
            CHAPTER_FONT,
            max(1, 470 - layout.width(chapter.label + "  ", CHAPTER_FONT)),
        )
        for chapter in chapters
    )
    sources = (assets["teej_left"], assets["teej_right"])
    frames = max(1, floor(max(AudioData(source=p).duration for p in sources) * FPS))
    heights = tuple(1920 * info.height / info.width for info in map(probe_video, sources))
    animation = compile_animation(
        tuple(
            Keyframe(
                start=c.start,
                end=c.start + 1,
                from_value=max(0, i - 1) * 75,
                to_value=i * 75,
                easing=Spring(mass=0.45, stiffness=130, damping=20),
            )
            for i, c in enumerate(chapters)
        )
    )
    return Prepared(
        assets, fonts, frames, heights, labels, tuple(animation.sample_many(range(frames), FPS))
    )


class Arguments(argparse.Namespace):
    """Explicit replacement for the unbundled title font."""

    family: str
    font: list[Path]


def arguments() -> Arguments:
    """Keep the original family unless the caller chooses a replacement."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", default="Berkeley Mono")
    parser.add_argument("--font", type=Path, action="append", default=[])
    return parser.parse_args(namespace=Arguments())
