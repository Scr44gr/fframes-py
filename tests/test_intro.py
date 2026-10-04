import hashlib
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest

import fframes
from examples import assets
from examples.compose.intro import build as composed
from examples.native.intro import Bindings, Native
from examples.native.intro import build as native
from examples.shared.intro.drawing import FRAMES, Window, beat_frame
from examples.shared.intro.sequence import windows


def test_intro_intervals_cover_every_frame_and_preserve_scene_origin_when_sliced() -> None:
    intervals = tuple(window for _, window in windows(0, FRAMES))
    assert len(intervals) == 16
    assert intervals[0].first == 0
    assert intervals[-1].end == 7650
    assert sum(window.end - window.first for window in intervals) == 7650
    for before, after in pairwise(intervals):
        assert before.end == after.first
        sliced = tuple(windows(before.end - 1, before.end + 1))
        assert [window.scene_first for _, window in sliced] == [before.first, after.first]
        assert [window.end - window.first for _, window in sliced] == [1, 1]
    assert intervals[1].first == 129
    assert intervals[3].first == 1438
    with pytest.raises(ValueError, match="range"):
        tuple(windows(7650, 7651))


def test_native_intro_reuses_clipping_definition_across_glitch_copies() -> None:
    painter = Native(Window(0, 1, 0, 0), {}, fframes.TextLayout())
    painter.bindings = Bindings()
    tile = painter.group((painter.rect((0, 0, 8, 8), "#ff0000"),), mask=(0, 0, 4, 4))
    body = painter.group((tile, painter.group((tile,), x=4))).frame(0)
    assert body.count('id="mask0"') == 1
    video = fframes.Video(
        config=fframes.VideoConfig(width=8, height=8),
        frames=(f'<svg width="8" height="8">{body}</svg>',),
    )
    assert video.rgba() == b"\xff\x00\x00\xff" * 32 + bytes(128)


def test_intro_recap_glitch_and_preview_share_palette_and_global_shader_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A tiny transparent grain replacement isolates geometry and clocks offline.
    # Its red channel reveals a restarted global clock immediately.
    font = Path(__file__).parent / "assets/Tuffy.ttf"
    grain = (
        "uniform float iTime; uniform float uGrain; uniform float uVignette; "
        "half4 main(float2 p) { return half4(iTime < 100 ? 1 : 0, 0, 0, 0.01); }"
    )
    folder = tmp_path / ("a" * 40)
    folder.mkdir()
    payloads = {"font.ttf": font.read_bytes(), "grain.sksl": grain.encode()}
    for name, payload in payloads.items():
        (folder / name).write_bytes(payload)
    source = assets.Manifest(
        repository="owner/repo",
        revision="a" * 40,
        examples={"intro": ("font", "intro_grain_sksl")},
        files={
            key: assets.File(path=name, sha256=hashlib.sha256(payloads[name]).hexdigest())
            for key, name in (("font", "font.ttf"), ("intro_grain_sksl", "grain.sksl"))
        },
    )
    monkeypatch.setenv("FFRAMES_EXAMPLE_CACHE", str(tmp_path))
    monkeypatch.setattr(assets, "manifest", lambda: source)
    for frame in (beat_frame(224) + 1, beat_frame(225.5), beat_frame(226.5)):
        raw = native("skia", frame=frame)
        scene = composed("skia", frame=frame).compile()
        a = np.frombuffer(raw.rgba(), dtype=np.uint8).astype(np.int16)
        b = np.frombuffer(scene.rgba(), dtype=np.uint8).astype(np.int16)
        assert np.abs(a - b).mean() < 0.01
        # Away from the HUD/type, the first three beats are orange, dark, then paper.
        rgb = a.reshape(1080, 1920, 4)[180, 960, :3]
        expected = (
            (248, 105, 34)
            if frame < beat_frame(225)
            else ((11, 11, 11) if frame < beat_frame(226) else (230, 226, 217))
        )
        assert rgb == pytest.approx(expected, abs=1)
