"""Pinned bird illustrations, avatars and optional independent speaker spectra."""

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from examples.assets import files
from fframes import AudioData

WIDTH, HEIGHT, FPS, DURATION = 1920, 1080, 60, 60
YELLOW = "#e7d850"
SPEAKERS = ("goose", "guest", "duck")


@dataclass(frozen=True)
class Prepared:
    """Static source artwork and a writable height buffer per supplied voice."""

    assets: dict[str, Path]
    markup: str
    paths: tuple[str, ...]
    heights: dict[str, NDArray[np.float32]]


def prepare(voices: tuple[Path | None, Path | None, Path | None]) -> Prepared:
    """Read only the pinned illustration section; never evaluate upstream source."""
    assets = files("podcast")
    source = assets["podcast_art"].read_text(encoding="utf-8")
    markup = source.split("// Background sections", 1)[1].split("// Avatar circles", 1)[0]
    markup = re.sub(r"//[^\n]*", "", markup)
    paths = tuple(re.findall(r'<path\s+d="([^"]+)"', markup))
    if len(paths) != 10:
        raise ValueError("pinned podcast artwork must contain ten paths")
    heights = {}
    for name, voice in zip(SPEAKERS, voices, strict=True):
        if voice is not None:
            spectrum = AudioData(source=voice).spectrum(
                frames=DURATION * FPS, fps=FPS, sample_size=32, smooth=2
            )
            values = np.frombuffer(spectrum.data, dtype="<f4").reshape(DURATION * FPS, 16)
            result = np.empty_like(values)
            np.multiply(values, 200, out=result)
            np.clip(result, 10, 40, out=result)
            heights[name] = result
    return Prepared(assets, markup, paths, heights)


class Arguments(argparse.Namespace):
    """Separate voice tracks drive bars; the pinned mix remains the soundtrack."""

    goose_audio: Path | None
    guest_audio: Path | None
    duck_audio: Path | None


def arguments() -> Arguments:
    """Accept optional per-speaker recordings just like the upstream example."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in SPEAKERS:
        parser.add_argument(f"--{name}-audio", type=Path)
    return parser.parse_args(namespace=Arguments())
