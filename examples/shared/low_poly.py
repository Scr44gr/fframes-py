"""Read the four pinned polygon artworks and prepare the owl's sampled effects."""

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

import numpy as np
from numpy.typing import NDArray

from examples.assets import files
from fframes import AudioData

Bird: TypeAlias = Literal["owl", "pelican", "popuga", "spektacled_owl"]
BIRDS: tuple[Bird, ...] = ("owl", "pelican", "popuga", "spektacled_owl")
WIDTH, HEIGHT, FPS = 1920, 1080, 60


@dataclass(frozen=True)
class Polygon:
    """One original closed polygon, stored without SVG element wrappers."""

    points: str
    fill: str


@dataclass(frozen=True)
class Prepared:
    """Static artwork and one owned spectrum output; the source spectrum stays borrowed."""

    assets: dict[str, Path]
    polygons: tuple[Polygon, ...]
    heights: NDArray[np.float32] | None
    noise_x: tuple[int, ...]
    noise_y: tuple[int, ...]
    duration: int


def noise(frame: int, seed: int) -> int:
    """Match upstream's deterministic wrapping u64 arithmetic."""
    x = ((frame ^ seed) * 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    x ^= x >> 29
    x = (x * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    x ^= x >> 32
    return x % 60 - 30


def prepare(bird: Bird) -> Prepared:
    """Extract data from the verified source file without executing its Rust code."""
    assets = files("low_poly")
    source = assets[f"art_{bird}"].read_text(encoding="utf-8")
    matches = re.findall(
        r'<polygon\s+points="([^"]+)"\s+(?:style="fill:|fill=")rgb\((\d+),(\d+),(\d+)\)"\s*/>',
        source,
    )
    if len(matches) != source.count("<polygon") or not matches:
        raise ValueError("unexpected pinned polygon syntax")
    polygons = tuple(
        Polygon(points, f"#{int(r):02x}{int(g):02x}{int(b):02x}") for points, r, g, b in matches
    )
    if bird != "owl":
        return Prepared(assets, polygons, None, (), (), 15)
    spectrum = AudioData(source=assets["owl_audio"]).spectrum(
        frames=600, fps=FPS, sample_size=64, smooth=4, window="hamming_legacy", center=True
    )
    values = np.frombuffer(spectrum.data, dtype="<f4").reshape(600, 32)[:, 2:]
    heights = np.empty_like(values)
    np.clip(values, 20, 100, out=heights)
    return Prepared(
        assets,
        polygons,
        heights,
        tuple(noise(i, 0x5EED0001) for i in range(600)),
        tuple(noise(i, 0x5EED0002) for i in range(600)),
        10,
    )


class Arguments(argparse.Namespace):
    """Select the same artwork in either authoring API."""

    bird: Bird


def arguments() -> Arguments:
    """Default to the animated eagle owl, as the upstream executable does."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bird", choices=BIRDS, default="owl")
    return parser.parse_args(namespace=Arguments())
