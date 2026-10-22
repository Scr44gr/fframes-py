import struct
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

import fframes as f
from fframes import compose as c
from fframes import three_d as d
from tests.test_shaders import composed, native


def test_pcm_slices_share_bytes_and_preserve_rate_channels_and_offset() -> None:
    samples = np.empty((24000, 2), dtype="<f4")
    samples[:, 0] = 0.25
    samples[:, 1] = -0.125
    source = f.Pcm(data=samples.tobytes(), sample_rate=24000)
    view = source.slice(6000, 18000).slice(3000, 9000)
    assert view.data is source.data
    assert (view.start, view.end, view.frames) == (9000, 15000, 6000)
    scene = c.Video(
        resolution=(16, 16),
        fps=4,
        composition=c.Composition(
            duration=0.5,
            children=(c.Audio(source=view).at(0.25),),
        ),
    ).compile()
    data = np.frombuffer(
        scene.audio_samples(mix=f.AudioMixOptions(limiter=None, declick=False)), dtype="<f4"
    ).reshape(-1, 2)
    assert not data[:12000].any()
    assert tuple(data[18000]) == pytest.approx((0.25, -0.125))
    analysis = f.AudioData(source=source)
    assert analysis.sample_rate == 24000
    assert analysis.duration == 1
    spectrum = analysis.spectrum(frames=1, fps=1, sample_size=64, smooth=0)
    assert np.frombuffer(spectrum.data, dtype="<f4")[0] == pytest.approx(4)
    with pytest.raises(ValueError, match="slice"):
        view.slice(0, view.frames + 1)


@pytest.mark.parametrize("data", [b"", b"abc", struct.pack("<f", float("nan"))])
def test_pcm_rejects_incomplete_or_nonfinite_samples(data: bytes) -> None:
    with pytest.raises((ValidationError, ValueError), match=r"(PCM|bytes|length|finite)"):
        _ = f.AudioData(source=f.Pcm(data=data, channels=1)).native


def test_image_buffers_keep_alpha_and_match_encoded_images(tmp_path: Path) -> None:
    pixels = bytes((255, 64, 0, 128)) * 16 * 16
    source = f.ImageBuffer(data=pixels, size=(16, 16))
    scene = c.Video(
        resolution=(16, 16),
        composition=c.Composition(
            duration=1,
            children=(c.Image(source=source, size=(16, 16)),),
        ),
    ).compile()
    raw = f.Video(
        config=f.VideoConfig(width=16, height=16),
        frames=(
            '<svg width="16" height="16"><image href="image:icon" width="16" height="16"/></svg>',
        ),
        images=(f.ImageBinding(name="icon", source=source),),
    )
    assert raw.rgba() == scene.rgba()
    assert tuple(scene.rgba()[:4]) == pytest.approx((255, 64, 0, 128), abs=1)
    path = scene.save_png(tmp_path / "image.png")
    encoded = f.ImageBuffer(data=path.read_bytes())
    path.unlink()
    decoded = c.Video(
        resolution=(16, 16),
        composition=c.Composition(
            duration=1,
            children=(c.Image(source=encoded, size=(16, 16)),),
        ),
    )
    assert decoded.rgba() == scene.rgba()
    with pytest.raises(ValidationError, match="RGBA8"):
        f.ImageBuffer(data=pixels[:-1], size=(16, 16))


def test_video_frames_support_random_access_source_clock_loop_and_eof() -> None:
    colors = (bytes((255, 0, 0, 255)), bytes((0, 255, 0, 255)), bytes((0, 0, 255, 255)))
    source = f.VideoFrames(data=b"".join(color * 16 * 16 for color in colors), size=(16, 16), fps=2)
    scene = c.Video(
        resolution=(16, 16),
        fps=4,
        composition=c.Composition(
            duration=2,
            children=(c.VideoClip(source=source, size=(16, 16)),),
        ),
    ).compile()
    raw = f.Video(
        config=f.VideoConfig(width=16, height=16, fps=4),
        frames=(
            '<svg width="16" height="16"><image href="video:clip" width="16" height="16"/></svg>',
        )
        * 8,
        clips=(f.VideoBinding(name="clip", source=source),),
    )
    for frame, expected in (
        (5, colors[2]),
        (0, colors[0]),
        (1, colors[1]),
        (2, colors[1]),
        (6, bytes(4)),
    ):
        assert scene.rgba(frame) == raw.rgba(frame)
        assert scene.rgba(frame)[:4] == expected
    loop = c.Video(
        resolution=(16, 16),
        fps=4,
        composition=c.Composition(
            duration=2,
            children=(c.VideoClip(source=source, size=(16, 16), offset=0.5, loop=True),),
        ),
    ).compile()
    assert loop.rgba(4)[:4] == colors[1]
    with pytest.raises(ValidationError, match="multiple"):
        f.VideoFrames(data=source.data[:-1], size=(16, 16))


def test_buffer_uniforms_and_nested_compose_texture_use_the_same_payload_path() -> None:
    source = f.ImageBuffer(data=bytes((128, 64, 255, 255)) * 4, size=(2, 2))
    shader = f.Shader(
        source="uniform shader picture; half4 main(float2 p) { return picture.eval(p); }",
        uniforms=(f.ImageUniform(name="picture", source=source),),
    )
    assert composed(shader).rgba() == native(shader).rgba(0)
    inner = c.Video(
        resolution=(16, 16),
        composition=c.Composition(
            duration=1,
            children=(c.Image(source=source, size=(16, 16)),),
        ),
    )

    assert (
        texture_renderer(inner.texture()).rgba()
        == texture_renderer(d.Texture(source=d.ImageTexture(source=source))).rgba()
    )


def test_buffer_video_uniform_and_resized_texture_preserve_frames() -> None:
    source = f.VideoFrames(
        data=bytes((255, 0, 0, 255, 0, 0, 255, 255)) * 2
        + bytes((0, 255, 0, 255, 255, 255, 255, 255)) * 2,
        size=(2, 2),
        fps=2,
    )
    shader = f.Shader(
        source="uniform shader picture; half4 main(float2 p) { return picture.eval(p); }",
        uniforms=(f.VideoUniform(name="picture", source=source, loop=True),),
    )
    low, high = native(shader), composed(shader)
    assert low.rgba(0) != low.rgba(5)
    for index in (5, 0, 10):
        assert low.rgba(index) == high.rgba(index)
    assert low.rgba(0) == low.rgba(10)

    resized = texture_renderer(d.Texture(source=d.VideoTexture(source=source, size=(1, 1))))
    for time, color in ((0.5, (128, 255, 128, 255)), (0, (128, 0, 128, 255))):
        expected = texture_renderer(
            d.Texture(source=d.ImageTexture(source=f.ImageBuffer(data=bytes(color), size=(1, 1))))
        )
        assert resized.rgba(time) == expected.rgba()


def texture_renderer(texture: d.Texture) -> d.Renderer:
    return d.Renderer(
        size=(32, 32),
        settings=d.RenderSettings(device="cpu", tone_mapping="linear"),
        scene=d.Scene(
            nodes=(
                d.Mesh(
                    geometry=d.Plane(),
                    material=d.Material(shading="unlit", map=texture, side="double"),
                ),
            ),
        ),
    )
