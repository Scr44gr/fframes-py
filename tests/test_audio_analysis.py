import math
import struct
from pathlib import Path

import numpy as np
import pytest

from fframes import AudioData, Cue, Spectrum, Subtitles
from tests.test_composition_audio import RATE, write_audio


def values(spectrum: Spectrum) -> tuple[float, ...]:
    return struct.unpack(f"<{spectrum.frames * spectrum.bins}f", spectrum.data)


def test_spectrum_preserves_frequency_bins_owned_audio_and_silence_at_eof(tmp_path: Path) -> None:
    source = write_audio(
        tmp_path / "tone.wav",
        tuple(round(16000 * math.sin(2 * math.pi * 3 * i / 32)) for i in range(48000)),
    )
    audio = AudioData(source=source)
    assert (audio.sample_rate, audio.duration) == (RATE, 1)
    source.unlink()
    spectrum = audio.spectrum(frames=31, fps=30, sample_size=32, smooth=0)
    data = values(spectrum)
    assert (spectrum.frames, spectrum.bins, spectrum.fps) == (31, 16, 30)
    assert data[3] == pytest.approx(16000 / 32768 * 16, abs=0.001)
    assert max(data[:3] + data[4:16]) < 0.001
    assert data[-16:] == (0,) * 16
    view = np.frombuffer(spectrum.data, dtype=np.dtype(np.float32).newbyteorder("<"))
    owner: object = view.base
    assert owner is spectrum.data
    assert not view.flags.writeable
    centered = values(audio.spectrum(frames=1, fps=30, sample_size=32, smooth=0, center=True))
    assert centered == tuple(
        data[i] for i in (14, 12, 10, 8, 6, 4, 2, 0, 1, 3, 5, 7, 9, 11, 13, 15)
    )
    assert len(values(audio.spectrum(frames=2, fps=30, sample_size=2, center=True))) == 2


def test_smoothing_uses_upstream_window_and_hamming_is_explicit(tmp_path: Path) -> None:
    source = write_audio(tmp_path / "steps.wav", tuple(i // 1600 * 100 for i in range(48000)))
    audio = AudioData(source=source)
    plain = values(audio.spectrum(frames=12, fps=30, sample_size=32, smooth=0))
    smooth = values(audio.spectrum(frames=10, fps=30, sample_size=32, smooth=2))
    assert smooth[:80] == plain[:80]  # first five frames remain unsmoothed
    assert smooth[5 * 16] == pytest.approx(sum(plain[i * 16] for i in range(3, 7)) / 4)
    constant = AudioData(source=write_audio(tmp_path / "constant.wav", (10000,) * 48000))
    expected = sum(0.54 - 0.46 * math.cos(2 * math.pi * i / 31) for i in range(32)) * 10000 / 32768
    hamming = values(constant.spectrum(frames=1, fps=30, sample_size=32, window="hamming"))
    assert hamming[0] == pytest.approx(expected, rel=1e-6)
    hann = values(constant.spectrum(frames=1, fps=30, sample_size=32, window="hann"))
    assert hann[0] == pytest.approx(16 * 10000 / 32768)
    legacy = values(constant.spectrum(frames=1, fps=30, sample_size=32, window="hamming_legacy"))
    assert legacy[0] > hamming[0] * 10
    with pytest.raises(ValueError, match="smooth"):
        audio.spectrum(frames=1, fps=30, smooth=-1)
    with pytest.raises(ValueError, match="length"):
        Spectrum(data=b"", frames=1, bins=16, fps=30)


def test_webvtt_retains_overlap_unicode_multiline_and_cue_settings() -> None:
    track = Subtitles.parse(
        "WEBVTT\nKind: captions\nLanguage: en\n\n"
        "first\n00:01.250 --> 00:03.500 line:25% position:40% size:80% align:end\n"
        "<i>Hello</i>\nPython \u2192 Rust\n\n"
        "00:02.000 --> 00:04.000 vertical:rl\nOverlap\n\n"
        "NOTE preserved comment\n\n"
        "STYLE\n::cue { color: white; }\n\n"
        "01:02:03.125 --> 01:02:04.500\nLater\n"
    )
    assert track.description == "Kind: captions\nLanguage: en\n"
    assert track.notes == ("preserved comment",)
    assert track.styles == ("::cue { color: white; }\n",)
    a, b, c = track.cues
    assert (c.start, c.end) == (3723.125, 3724.5)
    assert (a.start, a.end, a.name, a.text) == (
        1.25,
        3.5,
        "first",
        "<i>Hello</i>\nPython \u2192 Rust",
    )
    assert a.settings is not None
    assert (a.settings.line, a.settings.position, a.settings.size, a.settings.align) == (
        "25%",
        40,
        80,
        "end",
    )
    assert b.settings is not None
    assert b.settings.vertical == "rl"
    assert (b.start, b.end) == (2, 4)
    with pytest.raises(ValueError, match="WEBVTT"):
        Subtitles.parse("not WebVTT")
    with pytest.raises(ValueError, match="precede"):
        Cue(start=2, end=1, text="invalid")


def test_caption_intervals_restore_prior_cues_and_include_the_last_millisecond() -> None:
    from examples.shared.subtitles import captions
    from fframes import Font, TextLayout

    track = Subtitles(
        cues=(
            Cue(start=0, end=2, text="Base"),
            Cue(start=0.5, end=1, text="Overlay"),
            Cue(start=3, end=3.2, text="Later"),
        )
    )
    spans = captions(
        track,
        TextLayout(fonts=(Path(__file__).parent / "assets/Tuffy.ttf",)),
        Font(family="Tuffy", size=16),
        100,
        35,
        10,
    )
    assert [(s.start, s.end, s.lines[0][0]) for s in spans] == [
        (0, 5, "Base"),
        (5, 11, "Overlay"),
        (11, 21, "Base"),
        (30, 33, "Later"),
    ]


@pytest.mark.parametrize("ending", ["", "\n", "\r\n"])
def test_final_webvtt_cue_can_end_at_eof(ending: str) -> None:
    track = Subtitles.parse("WEBVTT\n\n00:00.000 --> 00:01.000\nFinal cue" + ending)
    assert track.cues == (Cue(start=0, end=1, text="Final cue"),)
