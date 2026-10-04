from pathlib import Path

import pytest

import fframes
from examples import podcast
from examples.compose.podcast import build as compose
from examples.native.podcast import build as native
from tests.test_composition_audio import write_audio


def test_guest_stem_controls_its_own_panel_without_a_goose_stem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    voice = write_audio(tmp_path / "voice.wav", (1500,) * 48000)
    portrait = tmp_path / "portrait.png"
    fframes.Video(
        config=fframes.VideoConfig(width=16, height=16, fps=1),
        frames=('<svg width="16" height="16"><rect width="16" height="16" fill="lime"/></svg>',),
    ).native.save_png(0, portrait)
    art = tmp_path / "art.rs"
    art.write_text(
        '// Background sections <rect width="1920" height="1080" fill="white"/>\n'
        + '<path d="M0 0L1 0L1 1Z"/>' * 10
        + "// Avatar circles",
        encoding="utf-8",
    )
    assets = {f"podcast_{name}": portrait for name in podcast.SPEAKERS}
    assets.update(podcast_audio=voice, podcast_art=art)
    monkeypatch.setattr(podcast, "files", lambda _name: assets)
    a, b = native(guest=voice), compose(guest=voice).compile()
    assert len(a) == len(b) == 3600
    for video in (a, b):
        pixels = video.rgba(0)
        for x, y, expected in (
            (800, 920, "000000ff"),  # Wide guest backing exists without a goose track.
            (803, 950, "e7d850ff"),  # Guest's first spectrum bar.
            (960, 680, "00ff00ff"),  # Portrait survives circular clipping.
        ):
            offset = (y * 1920 + x) * 4
            assert pixels[offset : offset + 4] == bytes.fromhex(expected)
    assert a.audio_samples() == b.audio_samples()
