import hashlib
from pathlib import Path

import pytest

from examples import assets
from examples.compose import hello_world as compose_hello
from examples.compose import neon_triangle as compose_neon
from examples.compose import scenes as compose_scenes
from examples.compose import shaders as compose_shaders
from examples.native import hello_world as native_hello
from examples.native import neon_triangle as native_neon
from examples.native import scenes as native_scenes
from examples.native import shaders as native_shaders


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
    sources = {
        "aurora": "uniform half4 uColorA; uniform half4 uColorB; uniform float uSpeed; "
        "half4 main(float2 p) { return mix(uColorA, uColorB, uSpeed); }",
        "torus": "void mainImage(out vec4 c, in vec2 p) { c = vec4(0.1, 0.3, 0.5, 1); }",
        "triangle": "uniform float uYaw; uniform float uRoll; uniform half4 uColor; "
        "half4 main(float2 p) { return half4(uYaw / 10, uRoll / 10, uColor.b, 1); }",
    }
    files = {"dm_sans": font, "jetbrains_mono": font}
    for name, shader_source in sources.items():
        payload = shader_source.encode()
        (folder / name).write_bytes(payload)
        files[name] = assets.File(path=name, sha256=hashlib.sha256(payload).hexdigest())
    source = assets.Manifest(
        repository="owner/repo",
        revision=revision,
        files=files,
        examples={
            "hello_world": ("dm_sans", "jetbrains_mono"),
            "shaders": ("dm_sans", "aurora", "torus"),
            "neon_triangle": ("dm_sans", "jetbrains_mono", "triangle"),
        },
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


@pytest.mark.usefixtures("example_fonts")
def test_shader_ports_preserve_card_fade_mask_and_program_bindings() -> None:
    native, composed = native_shaders.build("skia"), compose_shaders.build("skia").compile()
    assert len(native) == len(composed) == 240
    center = (540 * 1920 + 1420) * 4
    corner = (162 * 1920 + 1042) * 4
    for index in (0, 9, 15, 90, 239):
        a, b = native.rgba(index), composed.rgba(index)
        assert a[:4] == b[:4]
        assert a[center : center + 4] == b[center : center + 4]
        assert a[corner : corner + 4] == b[corner : corner + 4]
        if index >= 90:
            assert tuple(a[center : center + 4]) == pytest.approx((26, 76, 128, 255), abs=1)
            assert a[corner : corner + 4] != a[center : center + 4]


@pytest.mark.usefixtures("example_fonts")
def test_neon_ports_keep_sixty_fps_and_angular_velocity() -> None:
    native, composed = native_neon.build("skia"), compose_neon.build("skia").compile()
    assert len(native) == len(composed) == 360
    center = (300 * 1920 + 1300) * 4
    colors = []
    for index in (0, 120, 359):
        a, b = native.rgba(index), composed.rgba(index)
        assert a[center : center + 4] == b[center : center + 4]
        assert a[:4] == b[:4] == b"\x00\x00\x00\xff"
        colors.append(a[center])
    assert colors[0] < colors[1] < colors[2]
