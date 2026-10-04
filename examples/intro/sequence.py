"""Original beat timeline, sound mix, camera accents and shared command-line options."""

import argparse
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import numpy as np

from examples.intro import agents, benchmark, closing, media, opening
from examples.intro.drawing import (
    BEAT,
    BONE,
    DOWNBEAT,
    FPS,
    FRAMES,
    HEIGHT,
    ORANGE,
    WIDTH,
    N,
    Painter,
    Window,
    beat_frame,
    noise,
    prog,
    pulse,
    timecode,
)
from examples.intro.effects import effect
from fframes import AudioTrack
from fframes.models import Backend

SCENES = (
    ("prompt", None),
    ("origin", 0),
    ("code", 32),
    ("gpu", 48),
    ("text", 56),
    ("image", 62),
    ("video", 66),
    ("shader", 72),
    ("scale", 80),
    ("benchmark", 96),
    ("preview", 128),
    ("agents", 160),
    ("render", 208),
    ("recap", 224),
    ("done", 236),
    ("fframes", 240),
)
CUTS = (32, 56, 62, 66, 72, 80, 128, 144, 224)


def soundtrack(assets: dict[str, Path]) -> tuple[AudioTrack, ...]:
    """Place each original sound at the beat minus its attack time."""
    sounds = [
        ("typing", 0.02, -15),
        ("enter", DOWNBEAT - BEAT - 0.067, -9),
        ("impact", DOWNBEAT + 48 * BEAT, -10),
        ("shutter", DOWNBEAT + 62 * BEAT - 0.02, -2),
        ("glitch", DOWNBEAT + 70 * BEAT - 0.2, -8),
        ("impact", DOWNBEAT + 96 * BEAT, -10),
        ("impact", DOWNBEAT + 144 * BEAT, -12),
        ("impact", DOWNBEAT + 208 * BEAT, -11),
        ("typing", DOWNBEAT + 236.2 * BEAT, -18),
        ("impact", DOWNBEAT + 240 * BEAT, -7),
        ("braam", DOWNBEAT + 240 * BEAT, -9),
    ]
    sounds.extend(
        ("whoosh", DOWNBEAT + b * BEAT - 0.18, -15) for b in (56, 62, 66, 72, 80, 128, 160, 224)
    )
    sounds.extend(("blip", DOWNBEAT + b * BEAT, -9) for b in agents.CARD_BEATS)
    return (
        AudioTrack(source=assets["intro_music_wav"], fade_out=1.5),
        *(
            AudioTrack(source=assets[f"intro_sfx_{name}_mp3"], start_at=max(0, time), gain_db=gain)
            for name, time, gain in sounds
        ),
    )


def windows(first: int, end: int) -> Iterator[tuple[int, Window]]:
    """Intersect the requested range with the original frame-rounded scene boundaries."""
    if not 0 <= first < end <= FRAMES:
        raise ValueError(f"Expected a nonempty frame range within 0..{FRAMES}")
    for i, (_, beat) in enumerate(SCENES):
        start = 0 if beat is None else beat_frame(beat)
        stop = beat_frame(SCENES[i + 1][1] or 0) if i + 1 < len(SCENES) else FRAMES
        if max(first, start) < min(end, stop):
            yield i, Window(max(first, start), min(end, stop), start, beat or 0)


def pieces(
    factory: Callable[[Window], Painter[N]], first: int, end: int
) -> Iterator[tuple[Window, N]]:
    """Reuse full scenes; duplicate only the three sampled frames of each six-band glitch."""
    renderers: tuple[Callable[[Painter[N]], N], ...] = (
        opening.prompt,
        opening.origin,
        opening.code,
        opening.gpu,
        media.typography,
        media.image,
        media.video,
        media.shader,
        benchmark.scale,
        benchmark.benchmark,
        media.preview,
        agents.agents,
        closing.render,
        closing.recap,
        closing.done,
        closing.outro,
    )
    for index, window in windows(first, end):
        p = factory(window)
        global_beat = p.b + window.beat
        visible = np.ones_like(p.b)
        glitches = []
        for cut in CUTS:
            since = (global_beat - cut) * BEAT * FPS
            selected = np.flatnonzero((since >= 0) & (since < 3))
            if selected.size:
                a, b = int(selected[0]), int(selected[-1]) + 1
                visible[a:b] = 0
                glitches.append(
                    (
                        Window(window.first + a, window.first + b, window.scene_first, window.beat),
                        since[a:b],
                    )
                )
        yield window, pump(p, p.group((renderers[index](p),), alpha=visible))
        for glitch, since in glitches:
            g = factory(glitch)
            body = renderers[index](g)
            bands = tuple(
                g.group(
                    (body,),
                    mask=(0, i * 180, 1920, 180),
                    x=(noise(i * 13 + np.floor(since) * 7) - 0.5) * 140 * (1 - since / 3),
                )
                for i in range(6)
            )
            yield glitch, pump(g, g.group(bands))


def pump(p: Painter[N], body: N) -> N:
    """Pulse the camera only while the source's full beat is playing."""
    b = p.b + p.window.beat
    active = np.zeros(len(b), dtype=np.bool_)
    for start, end in ((48, 80), (96, 160), (208, 236), (240, 268)):
        active |= (b >= start) & (b < end)
    return p.group((body,), scale=1 + np.where(active, pulse(b, 9) * 0.008, 0), origin=(960, 540))


def overlay(p: Painter[N]) -> N:
    """Composite the drop flash, unmodified grain program and source HUD."""
    b = p.b
    flash = np.zeros_like(b)
    for drop in (48, 96, 144, 208):
        np.maximum(flash, np.where(b >= drop, np.exp(-np.maximum(b - drop, 0) * 7), 0), out=flash)
    bars = np.where(b < 0, 0, np.floor(b / 4) + 1).astype(np.int64)
    beats = np.where(b < 0, 0, np.floor(np.mod(b, 4)) + 1).astype(np.int64)
    titles = tuple(f"{i:02} / {name.upper()}" for i, (name, _) in enumerate(SCENES))
    starts = np.array([-99, *(v or 0 for _, v in SCENES[1:])])
    selected = np.searchsorted(starts, b, side="right") - 1
    hud = p.group(
        (
            p.corners(36, 36, 1848, 1008, 26, "#d8d4cc", 2),
            p.label(66, 78, "FFRAMES — INTRO", "#d8d4cc", 17),
            p.label(
                1854,
                78,
                tuple(
                    f"132 BPM   BAR {bar:03}.{beat}" for bar, beat in zip(bars, beats, strict=True)
                ),
                "#d8d4cc",
                17,
                "end",
            ),
            p.rect((1840, 92, 14, 14), ORANGE, alpha=0.25 + np.where(b < 0, 0, pulse(b, 7)) * 0.75),
            p.label(66, 1018, timecode(p.seconds), "#d8d4cc", 17),
            p.label(290, 1018, tuple(f"F {int(f):05}" for f in p.frames), "#77736d", 17),
            p.label(1854, 1018, tuple(titles[int(i)] for i in selected), "#d8d4cc", 17, "end"),
            p.rect((66, 1034, 1788, 1), "#d8d4cc", alpha=0.25),
            p.rect((66, 1033, np.maximum(p.seconds / (FRAMES / FPS) * 1788, 0.5), 3), "#d8d4cc"),
        ),
        alpha=prog(p.seconds, 0.1, 0.5) * 0.9 * ((b < 236) | (b >= 244)),
        blend="difference",
    )
    return p.group(
        (
            p.rect((0, 0, WIDTH, HEIGHT), BONE, alpha=flash * 0.55),
            effect(p, "grain", {"uGrain": 0.07, "uVignette": 0.55}, {}),
            hud,
        )
    )


class Arguments(argparse.Namespace):
    """Typed CLI values shared by both entry points."""

    backend: Backend
    frame: int | None


def arguments() -> Arguments:
    """Render the full HD intro or inspect an original global frame without exporting video."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend",
        choices=("skia", "vulkan", "metal"),
        default="metal" if sys.platform == "darwin" else "vulkan",
    )
    parser.add_argument("--frame", type=int, choices=range(FRAMES), metavar=f"0..{FRAMES - 1}")
    return parser.parse_args(namespace=Arguments())
