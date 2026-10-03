import math
import struct
import wave
from pathlib import Path

import pytest

from fframes.compose import Audio, Composition, Rectangle, RenderOptions, Video

RATE = 48_000


def write_audio(path: Path, samples: tuple[int, ...], *, channels: int = 1) -> Path:
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(channels)
        stream.setsampwidth(2)
        stream.setframerate(RATE)
        stream.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return path


def make_video(composition: Composition) -> Video:
    return Video(composition=composition, resolution=(16, 16), fps=10, load_system_fonts=False)


def sample(data: bytes, time: float) -> tuple[float, float]:
    return struct.unpack_from("<ff", data, round(time * RATE) * 8)


def test_audio_placement_uses_samples_and_natural_duration(tmp_path: Path) -> None:
    source = write_audio(tmp_path / "tone.wav", (2000,) * 2400)
    compiled = make_video(
        Composition(duration=0.2, children=(Audio(source=source).at(0.05002),))
    ).compile()
    data = compiled.audio_samples()
    assert len(data) == round(0.2 * RATE) * 8
    assert sample(data, 0.05) == (0, 0)
    assert sample(data, 2401 / RATE) == pytest.approx((2000 / 32768,) * 2, abs=1e-6)
    assert sample(data, 0.09) == pytest.approx((2000 / 32768,) * 2, abs=1e-6)
    assert sample(data, 0.11) == (0, 0)


def test_stereo_sources_sum_with_gain_without_collapsing_channels(tmp_path: Path) -> None:
    source = write_audio(tmp_path / "stereo.wav", (2000, 1000) * 4800, channels=2)
    scene = make_video(
        Composition(
            duration=0.1,
            children=(Audio(source=source), Audio(source=source, gain_db=-6.020599913)),
        )
    ).compile()
    source.unlink()
    assert sample(scene.audio_samples(), 0.05) == pytest.approx((3000 / 32768, 1500 / 32768))


def test_loop_uses_source_offset_and_fades_at_the_final_end(tmp_path: Path) -> None:
    source = write_audio(tmp_path / "loop.wav", (0,) * 240 + (2000,) * 240)
    scene = make_video(
        Composition(
            duration=0.1,
            children=(
                Audio(source=source, offset=0.005, loop=True, fade_out=0.02).at(
                    0.015, duration=0.06
                ),
            ),
        )
    ).compile()
    data = scene.audio_samples()
    assert sample(data, 0.01) == (0, 0)
    # The sample immediately after a loop boundary keeps its level.
    assert sample(data, 0.035) == pytest.approx((2000 / 32768,) * 2, abs=1e-6)
    assert sample(data, 0.065) == pytest.approx((2000 / 32768 / math.sqrt(2),) * 2, abs=2e-4)
    assert sample(data, 0.08) == (0, 0)


def test_nested_audio_is_clipped_and_pan_affects_the_correct_channel(tmp_path: Path) -> None:
    source = write_audio(tmp_path / "pan.wav", (2000,) * RATE)
    group = Composition(duration=0.05, children=(Audio(source=source, pan=1).at(0.02),))
    data = (
        make_video(Composition(duration=0.2, children=(group.at(0.05),))).compile().audio_samples()
    )
    assert sample(data, 0.06) == (0, 0)
    assert sample(data, 0.08) == pytest.approx((0, 2000 / 32768), abs=1e-6)
    assert sample(data, 0.11) == (0, 0)


def test_fade_in_uses_local_audio_time(tmp_path: Path) -> None:
    source = write_audio(tmp_path / "fade.wav", (2000,) * RATE)
    data = (
        make_video(
            Composition(duration=0.2, children=(Audio(source=source, fade_in=0.04).at(0.03),))
        )
        .compile()
        .audio_samples()
    )
    assert sample(data, 0.05) == pytest.approx((2000 / 32768 / math.sqrt(2),) * 2, abs=2e-4)


def test_audio_offset_past_eof_is_an_error(tmp_path: Path) -> None:
    source = write_audio(tmp_path / "short.wav", (0,) * 240)
    with pytest.raises(ValueError, match="offset"):
        make_video(Composition(duration=1, children=(Audio(source=source, offset=1),))).compile()


def test_rendered_mp4_contains_audible_audio_at_the_requested_time(tmp_path: Path) -> None:
    tone = tuple(round(8192 * math.sin(2 * math.pi * 440 * i / RATE)) for i in range(RATE // 2))
    source = write_audio(tmp_path / "sine.wav", tone)
    movie = tmp_path / "mixed.mp4"
    make_video(
        Composition(
            duration=0.5,
            children=(
                Rectangle(size=(16, 16), fill="#FF0000"),
                Audio(source=source).at(0.1, duration=0.3),
            ),
        )
    ).render(movie, options=RenderOptions(concurrency=2))
    encoded = movie.read_bytes()
    assert b"vide" in encoded
    assert b"soun" in encoded
    # Decode the actual AAC stream through the same native media decoder used by clients.
    decoded = (
        make_video(Composition(duration=0.5, children=(Audio(source=movie),)))
        .compile()
        .audio_samples()
    )

    def rms(start: float, end: float) -> float:
        values = [
            sample(decoded, i / RATE)[0] for i in range(round(start * RATE), round(end * RATE))
        ]
        return math.sqrt(sum(value * value for value in values) / len(values))

    assert rms(0.02, 0.06) < 0.005
    assert rms(0.18, 0.22) == pytest.approx(0.25 / math.sqrt(2), abs=0.015)
    assert rms(0.44, 0.48) < 0.005
    assert not list(tmp_path.glob("fframes-py-*"))
