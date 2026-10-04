from pathlib import Path

import pytest

import fframes
from examples import teej_podcast as interview
from examples.compose.teej_podcast import build as compose
from examples.native.teej_podcast import build as native
from tests.test_composition_audio import write_audio


def test_interview_ports_keep_panel_clipping_and_chapter_transition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio = write_audio(tmp_path / "voice.wav", (1500,) * 144000)
    picture = tmp_path / "still.png"
    frames = tuple(
        f'<svg width="32" height="18"><rect width="32" height="18" fill="{color}"/></svg>'
        for color in ("red", "blue", "lime")
    )
    source = fframes.Video(
        config=fframes.VideoConfig(width=32, height=18, fps=1),
        frames=frames,
        audio=(fframes.AudioTrack(source=audio),),
    )
    source.native.save_png(0, picture)
    movie = source.render(tmp_path / "source.mp4", options=fframes.RenderOptions(concurrency=1))
    assets = {"sofia": Path(__file__).parent / "assets/Tuffy.ttf"}
    for side in ("left", "right"):
        assets[f"teej_{side}"] = movie
        assets[f"teej_{side}_still"] = picture
    monkeypatch.setattr(interview, "files", lambda _name: assets)
    monkeypatch.setattr(interview, "CHAPTER_FONT", fframes.Font(family="Tuffy", size=26))
    chapters = (
        interview.Chapter(start=0, title="First"),
        interview.Chapter(start=1, title="Second"),
        interview.Chapter(start=2, title="Last"),
    )
    a, b = native("Tuffy", chapters=chapters), compose("Tuffy", chapters=chapters).compile()
    assert len(a) == len(b) == 72
    for index, expected in (
        (0, (255, 0, 0)),
        (24, (0, 0, 255)),
        # Upstream selects the first source timestamp at or after the target.
        (47, (0, 255, 0)),
        (71, (0, 255, 0)),
    ):
        for video in (a, b):
            pixels = video.rgba(index)
            assert pixels[:4] == bytes.fromhex("1a191bff")
            for x in (100, 900):
                offset = (500 * 1920 + x) * 4
                assert pixels[offset : offset + 3] == pytest.approx(expected, abs=3)
            assert pixels[(500 * 1920 + 700) * 4 :][:4] == bytes.fromhex("1a191bff")
            # The highlight moves after a boundary, then settles under that chapter.
            y = 235 if index == 47 else 160 if index in (0, 24) else 310
            assert pixels[(y * 1920 + 1405) * 4 :][:4] == bytes.fromhex("ff6900ff")
    assert a.audio_samples() == b.audio_samples()
    with pytest.raises(ValueError, match="chapters"):
        interview.prepare("Tuffy", (), (chapters[1], chapters[0]))
