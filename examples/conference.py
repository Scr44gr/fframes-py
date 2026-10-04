"""Pinned conference talks, native text wrapping and shared scene timing."""

import argparse
import re
from dataclasses import dataclass
from math import floor, radians, tan
from pathlib import Path

from pydantic import Field, TypeAdapter

from examples.assets import files
from examples.shaders import keyframe
from fframes import AudioData, Font, Keyframe, Samples, Spring, TextLayout, Tween, compile_animation
from fframes.models import Model

WIDTH, HEIGHT, FPS, CUT = 1920, 1080, 24, 91
TITLE_SPRING = Spring(mass=4, stiffness=30, damping=25)
MOTION = {
    "location_y": Tween(
        from_value=129.6, to_value=329.6, start_at=0.4, duration=10, easing=TITLE_SPRING
    ),
    "title_x": Tween(from_value=960, to_value=1280, start_at=0.4, duration=10, easing=TITLE_SPRING),
    "title_y": Tween(from_value=540, to_value=190, start_at=0.4, duration=10, easing=TITLE_SPRING),
    "location_opacity": Tween(from_value=0, to_value=1, start_at=2, duration=0.2),
    "camel_opacity": Tween(from_value=0, to_value=1, start_at=1, duration=1.5),
    "sponsors_opacity": Tween(from_value=0, to_value=1, start_at=1.2, duration=0.2),
    "sponsors_y": Tween(
        from_value=1270,
        to_value=670,
        start_at=1.2,
        duration=10,
        easing=Spring(mass=0.8, stiffness=100, damping=16),
    ),
    "dash": Tween(
        from_value=300, to_value=0, duration=10, easing=Spring(mass=4, stiffness=80, damping=55)
    ),
}
CORNERS = (
    "M0 2H134.8C136.567 2 138 3.43269 138 5.2V134",
    "M137.2 132H5.19999C3.43268 132 2 130.567 2 128.8V0",
)


class Talk(Model):
    """One upstream sessions.json record."""

    description: str = Field(alias="abstract")
    proposal_title: str
    speaker_name: str
    social_links: str | None
    avatar: str | None


@dataclass(frozen=True)
class Prepared:
    """Layout is resolved once; native sampling handles every rendered frame."""

    assets: dict[str, Path]
    fonts: tuple[Path, ...]
    talk: Talk
    title: tuple[str, ...]
    title_size: int
    abstract: tuple[str, ...]
    abstract_size: int
    abstract_y: int
    corner_y: int
    speaker_width: int
    camel: str
    frames: int
    skew_x: Samples
    skew_y: Samples


def prepare(query: str) -> Prepared:
    """Select by zero-based index or case-insensitive speaker-name fragment."""
    assets = files("conference")
    talks = TypeAdapter(tuple[Talk, ...]).validate_json(assets["sessions"].read_bytes())
    if query.isdecimal():
        index = int(query)
        if index >= len(talks):
            raise ValueError(f"talk index must be less than {len(talks)}")
        talk = talks[index]
    else:
        matches = [t for t in talks if query.casefold() in t.speaker_name.casefold()]
        if not matches:
            raise ValueError(f"no speaker matches {query!r}")
        talk = matches[0]
    fonts = tuple(
        assets[name]
        for name in ("inter_title", "inter_bold", "inter_regular", "montserrat", "jetbrains_mono")
    )
    layout = TextLayout(fonts=fonts)
    # Rust String::len counts UTF-8 bytes, including accented names and punctuation.
    title_size = (
        70
        if len(talk.proposal_title.encode()) < 50 or len(talk.description.encode()) <= 300
        else 56
    )
    abstract_size = (
        32
        if len(talk.description.encode()) > 600
        else 36
        if len(talk.description.encode()) > 300
        else 48
    )
    title = layout.wrap(
        talk.proposal_title, Font(family="Inter 18pt", size=title_size, weight=800), 970
    )
    abstract = layout.wrap(talk.description, Font(family="Inter 24pt", size=abstract_size), 1000)
    abstract_y = 350 + len(title) * int(title_size * 1.2)
    speaker_width = (
        layout.width(talk.speaker_name, Font(family="Inter 24pt", size=54, weight=700)) + 32
    )
    camel = re.findall(r'd="([^"]+)"', assets["camel"].read_text(encoding="utf-8"))[-1]
    frames = floor(AudioData(source=assets["conference_audio"]).duration * FPS)
    tilt = compile_animation(
        (
            Keyframe(start=0.3, end=2.3, from_value=0.4, to_value=1.2),
            Keyframe(start=2.3, end=4.1, from_value=1.2, to_value=0.8),
        )
    ).sample_many(range(frames - CUT), FPS)
    return Prepared(
        assets,
        fonts,
        talk,
        title,
        title_size,
        abstract,
        abstract_size,
        abstract_y,
        abstract_y + len(abstract) * int(abstract_size * 1.2) - 110,
        speaker_width,
        camel,
        frames,
        Samples(values=tuple(tan(radians(t)) for t in tilt), fps=FPS),
        Samples(values=tuple(tan(radians(-t + 0.4)) for t in tilt), fps=FPS),
    )


def samples(frames: int) -> dict[str, tuple[float, ...]]:
    """Batch the original animations for the SVG port."""
    return {
        name: tuple(compile_animation((keyframe(value),)).sample_many(range(frames), FPS))
        for name, value in MOTION.items()
    }


class Arguments(argparse.Namespace):
    """Shared talk selector."""

    talk: str


def arguments() -> Arguments:
    """Choose any of the pinned conference sessions."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--talk", default="0")
    return parser.parse_args(namespace=Arguments())
