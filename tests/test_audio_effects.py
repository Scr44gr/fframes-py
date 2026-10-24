import math
import struct
from pathlib import Path

import pytest

import fframes
from fframes import compose
from fframes.audio import Ducking
from fframes.effects import (
    Compressor,
    Effect,
    Highpass,
    HighShelf,
    Lowpass,
    LowShelf,
    NormalizeLufs,
    Peak,
    StereoWidth,
)
from tests.test_composition_audio import RATE, sample, write_audio


def soundtrack(track: fframes.AudioTrack) -> bytes:
    return fframes.Video(
        config=fframes.VideoConfig(width=16, height=16, fps=10),
        frames=('<svg width="16" height="16"/>',) * 10,
        audio=(track,),
    ).audio_samples()


def amplitude(data: bytes, hz: int) -> float:
    # Steady-state Fourier component; ignore startup/filter transients.
    samples = tuple(struct.iter_unpack("<ff", data))[RATE // 2 :]
    sine = sum(left * math.sin(2 * math.pi * hz * i / RATE) for i, (left, _) in enumerate(samples))
    cosine = sum(
        left * math.cos(2 * math.pi * hz * i / RATE) for i, (left, _) in enumerate(samples)
    )
    return 2 * math.hypot(sine, cosine) / len(samples)


@pytest.mark.parametrize(
    ("effect", "attenuated", "preserved"),
    [
        (Lowpass(hz=500), 8000, 100),
        (Highpass(hz=1000), 100, 8000),
        (LowShelf(hz=1000, db=-12), 100, 8000),
        (HighShelf(hz=2000, db=-12), 8000, 100),
        (Peak(hz=100, db=-12, q=2), 100, 8000),
    ],
)
def test_eq_changes_only_the_intended_frequency_band(
    effect: Effect,
    attenuated: int,
    preserved: int,
    tmp_path: Path,
) -> None:
    source = write_audio(
        tmp_path / "tones.wav",
        tuple(
            round(
                5000
                * (math.sin(2 * math.pi * 100 * i / RATE) + math.sin(2 * math.pi * 8000 * i / RATE))
            )
            for i in range(RATE)
        ),
    )
    original = soundtrack(fframes.AudioTrack(source=source))
    filtered = soundtrack(fframes.AudioTrack(source=source, effects=(effect,)))
    assert amplitude(filtered, attenuated) < amplitude(original, attenuated) * 0.3
    assert amplitude(filtered, preserved) == pytest.approx(amplitude(original, preserved), rel=0.05)


def test_effect_order_and_stereo_processing_match_both_apis(tmp_path: Path) -> None:
    source = write_audio(
        tmp_path / "stereo.wav",
        tuple(
            value
            for i in range(RATE)
            for value in (
                round(16000 * math.sin(2 * math.pi * 440 * i / RATE)),
                round(8000 * math.sin(2 * math.pi * 880 * i / RATE)),
            )
        ),
        channels=2,
    )
    effects = (NormalizeLufs(lufs=-10), Compressor(threshold_db=-25, ratio=8), StereoWidth(width=0))
    track = fframes.AudioTrack(source=source, effects=effects)
    actual = soundtrack(track)
    composed = (
        compose.Video(
            resolution=(16, 16),
            fps=10,
            composition=compose.Composition(
                duration=1,
                children=(compose.Audio(source=source, effects=effects),),
            ),
        )
        .compile()
        .audio_samples()
    )
    assert actual == composed
    assert all(left == right for left, right in struct.iter_unpack("<ff", actual))
    reversed_order = soundtrack(fframes.AudioTrack(source=source, effects=effects[::-1]))
    assert amplitude(actual, 440) < amplitude(reversed_order, 440) * 0.5


def test_rate_changes_pitch_and_eof_without_wrapping_tail(tmp_path: Path) -> None:
    source = write_audio(
        tmp_path / "tone.wav",
        tuple(round(5000 * math.sin(2 * math.pi * 440 * i / RATE)) for i in range(RATE)),
    )
    fast = soundtrack(fframes.AudioTrack(source=source, rate=2, offset=0.25))
    assert max(abs(v) for pair in struct.iter_unpack("<ff", fast[: RATE * 2]) for v in pair) > 0.1
    assert not any(fast[round(0.375 * RATE) * 8 :])
    looped = soundtrack(fframes.AudioTrack(source=source, rate=2, offset=0.25, loop=True))
    assert amplitude(looped, 880) > 0.14
    assert amplitude(looped, 440) < 0.001


def test_ducking_uses_voice_interval_and_fade_curve_is_explicit(tmp_path: Path) -> None:
    source = write_audio(tmp_path / "bed.wav", (5000,) * RATE)
    silence = write_audio(tmp_path / "voice.wav", (0,) * (RATE // 5))
    audio = (
        fframes.AudioTrack(
            source=source,
            duck=Ducking(
                depth_db=-12,
                attack=0,
                release=0,
                hold=0,
                merge_gap=0,
            ),
        ),
        fframes.AudioTrack(source=silence, start_at=0.4, voice=True),
    )
    video = fframes.Video(
        config=fframes.VideoConfig(width=16, height=16, fps=10),
        frames=('<svg width="16" height="16"/>',) * 10,
        audio=audio,
    )
    data = video.audio_samples()
    assert sample(data, 0.5)[0] == pytest.approx(sample(data, 0.2)[0] * 10 ** (-12 / 20), rel=0.01)
    assert sample(data, 0.8) == sample(data, 0.2)
    linear = soundtrack(fframes.AudioTrack(source=source, fade_in=1, fade_curve="linear"))
    power = soundtrack(fframes.AudioTrack(source=source, fade_in=1, fade_curve="equal_power"))
    assert sample(linear, 0.5)[0] == pytest.approx(5000 / 32768 / 2, rel=0.01)
    assert sample(power, 0.5)[0] > sample(linear, 0.5)[0]
