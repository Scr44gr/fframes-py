import hashlib
from pathlib import Path

import pytest

import fframes
from examples import assets
from examples.compose import hello_world as compose_hello
from examples.compose import neon_triangle as compose_neon
from examples.compose import scenes as compose_scenes
from examples.compose import shaders as compose_shaders
from examples.compose import signal_lab as compose_signal
from examples.compose import tiktok as compose_tiktok
from examples.native import hello_world as native_hello
from examples.native import neon_triangle as native_neon
from examples.native import scenes as native_scenes
from examples.native import shaders as native_shaders
from examples.native import signal_lab as native_signal
from examples.native import tiktok as native_tiktok
from examples.shared import tiktok as portrait
from fframes import Font, TextLayout
from tests.test_composition_audio import write_audio


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
    pulse = write_audio(folder / "pulse.wav", (2000,) * 48000)
    files["pulse"] = assets.File(
        path="pulse.wav", sha256=hashlib.sha256(pulse.read_bytes()).hexdigest()
    )
    picture = folder / "goose.png"
    fframes.compile_video(
        fframes.VideoConfig(width=16, height=8),
        ('<svg width="16" height="8"><rect width="16" height="8" fill="#00ff00"/></svg>',),
    ).save_png(0, picture)
    files["goose"] = assets.File(
        path="goose.png", sha256=hashlib.sha256(picture.read_bytes()).hexdigest()
    )
    files["thought"] = files["pulse"]
    sources["thought_captions"] = "WEBVTT\n\n00:00.100 --> 00:00.400\nCaption\n"
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
            "signal_lab": ("dm_sans", "pulse"),
            "tiktok": ("jetbrains_mono", "thought", "thought_captions", "goose"),
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


@pytest.mark.usefixtures("example_fonts")
def test_signal_studies_keep_scene_clocks_progress_and_continuous_audio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Measure headings with the installed fixture font; production uses DM Sans.
    def fit_heading(layout: TextLayout, text: str) -> str:
        return layout.fit(text, Font(family="Tuffy", size=108, weight=500), width=1536)

    monkeypatch.setattr(native_signal, "heading", fit_heading)
    monkeypatch.setattr(compose_signal, "heading", fit_heading)
    native, composed = native_signal.build(), compose_signal.build().compile()
    assert len(native) == len(composed) == 720
    paper, green, ink = (
        bytes.fromhex("eeeae2ff"),
        bytes.fromhex("709542ff"),
        bytes.fromhex("152c2bff"),
    )
    for index, x, y, expected in (
        (0, 1100, 280, paper),  # release panel starts 56 px below its target
        (90, 1100, 280, ink),
        (180, 1050, 750, paper),  # data bars restart on the new local clock
        (270, 1050, 750, bytes.fromhex("b4bdb1ff")),
        (360, 220, 500, paper),  # process cards start transparent
        (450, 220, 500, ink),
        (540, 220, 760, paper),
        (630, 220, 760, ink),
    ):
        offset = (y * 1920 + x) * 4
        for video in (native, composed):
            pixels = video.rgba(index)
            assert pixels[offset : offset + 4] == expected
            progress = (946 * 1920 + 300) * 4
            if index >= 180:
                assert pixels[progress : progress + 4] == green
    a, b = native.audio_samples(), composed.audio_samples()
    assert a == b
    assert any(a[: 48000 * 8])
    assert not any(a[48000 * 8 :])


@pytest.mark.usefixtures("example_fonts")
def test_portrait_ports_keep_spectrum_glows_caption_intervals_and_image_aspect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(portrait, "CAPTION_FONT", Font(family="Tuffy", size=100))
    native, composed = native_tiktok.build(), compose_tiktok.build().compile()
    assert len(native) == len(composed) == 60
    for index in (0, 6, 25, 59):
        a, b = native.rgba(index), composed.rgba(index)
        for x, y in ((440, 300), (800, 1300), (800, 1600), (300, 1700), (500, 1000)):
            offset = (y * 1080 + x) * 4
            assert a[offset : offset + 4] == b[offset : offset + 4]
        assert a[(1600 * 1080 + 800) * 4 :][:4] == bytes.fromhex("00ff00ff")
        # The 2:1 fixture has transparent margins in the square image viewport.
        assert a[(1000 * 1080 + 500) * 4 :][:4] != bytes.fromhex("00ff00ff")
    assert native.audio_samples() == composed.audio_samples()
