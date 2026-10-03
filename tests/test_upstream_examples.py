import hashlib
from pathlib import Path

import pytest

from examples import assets
from examples.compose import hello_world as compose_hello
from examples.compose import scenes as compose_scenes
from examples.native import hello_world as native_hello
from examples.native import scenes as native_scenes


@pytest.fixture
def example_fonts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # CI checks scene behavior offline with a redistributable test font. Visual
    # comparisons with the pinned upstream fonts are a separate render check.
    payload = (Path(__file__).parent / "assets/Tuffy.ttf").read_bytes()
    revision = "f" * 40
    folder = tmp_path / revision
    folder.mkdir()
    (folder / "font.ttf").write_bytes(payload)
    font = assets.File(path="font.ttf", sha256=hashlib.sha256(payload).hexdigest())
    source = assets.Manifest(
        repository="owner/repo",
        revision=revision,
        files={"dm_sans": font, "jetbrains_mono": font},
        examples={"hello_world": ("dm_sans", "jetbrains_mono")},
    )
    monkeypatch.setenv("FFRAMES_EXAMPLE_CACHE", str(tmp_path))
    monkeypatch.setattr(assets, "manifest", lambda: source)


@pytest.mark.usefixtures("example_fonts")
def test_hello_world_ports_retain_timing_color_and_square_trajectory() -> None:
    native = native_hello.build()
    composed = compose_hello.build().compile()
    assert len(native) == len(composed) == 900
    for index, x, y, background in (
        (0, 500, 500, b"\xff\xff\xff\xff"),
        (60, 700, 980, b"\xfc\xfd\xfd\xff"),
        (180, 1250, 100, b"\xf9\xf9\xf9\xff"),
        (899, 1810, 980, b"\xf9\xf5\xfe\xff"),
    ):
        offset = (y * 1920 + x) * 4
        for video in (native, composed):
            pixels = video.rgba(index)
            assert pixels[:4] == background
            assert pixels[offset : offset + 4] == b"\x00\x00\xff\xff"


@pytest.mark.usefixtures("example_fonts")
def test_scene_ports_switch_at_fifteen_seconds_and_share_the_global_background() -> None:
    native = native_scenes.build()
    composed = compose_scenes.build().compile()
    assert len(native) == len(composed) == 900
    inside_square = (60 * 1920 + 60) * 4
    for index in (449, 450, 456, 899, 0):
        a, b = native.rgba(index), composed.rgba(index)
        assert a[-4:] == b[-4:]
        expected = b"\x00\x80\x00\xff" if index < 450 else a[-4:]
        assert a[inside_square : inside_square + 4] == expected
        assert b[inside_square : inside_square + 4] == expected
