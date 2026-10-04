from pathlib import Path

import pytest
from pydantic import ValidationError

import fframes
from fframes import compose
from fframes.models import Backend
from tests.test_media_bindings import colored_clip


def native(shader: fframes.Shader, *, backend: Backend = "skia") -> fframes.SvgVideo:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">'
        '<image href="shader:effect" width="16" height="16"/></svg>'
    )
    return fframes.compile_video(
        fframes.VideoConfig(width=16, height=16, fps=10, backend=backend),
        (svg,) * 20,
        shaders=(fframes.ShaderBinding(name="effect", shader=shader),),
    )


def composed(shader: fframes.Shader, *, backend: Backend = "skia") -> compose.CompiledVideo:
    return compose.Video(
        resolution=(16, 16),
        fps=10,
        backend=backend,
        load_system_fonts=False,
        composition=compose.Composition(
            duration=2, children=(compose.ShaderLayer(shader=shader, size=(16, 16)),)
        ),
    ).compile()


def test_shader_uniforms_match_between_apis_and_hold_animated_endpoints() -> None:
    shader = fframes.Shader(
        source="""
            uniform half4 tint;
            uniform float strength;
            uniform float2 offset;
            uniform float3 factors;
            uniform float4 bias;
            uniform int enabled;
            half4 main(float2 p) {
                float3 rgb = (tint.rgb * strength * factors + bias.rgb) * float(enabled) + offset.x;
                return half4(rgb, 1);
            }
        """,
        uniforms=(
            fframes.ColorUniform(
                name="tint",
                value=fframes.ColorTween(
                    from_value="#ff0000",
                    to_value="#0000ff",
                    duration=1,
                    start_at=0.2,
                ),
            ),
            fframes.FloatUniform(
                name="strength",
                value=fframes.Tween(
                    from_value=0,
                    to_value=1,
                    duration=0.5,
                ),
            ),
            fframes.VectorUniform(name="offset", value=(0, 0)),
            fframes.VectorUniform(name="factors", value=(1, 1, 1)),
            fframes.VectorUniform(name="bias", value=(0, 0, 0, 0)),
            fframes.IntUniform(name="enabled", value=1),
        ),
    )
    a, b = native(shader), composed(shader)
    for index, expected in ((19, (0, 0, 255, 255)), (7, (127, 0, 127, 255)), (0, (0, 0, 0, 255))):
        assert a.rgba(index) == b.rgba(index)
        assert tuple(a.rgba(index)[:4]) == pytest.approx(expected, abs=1)


def test_shadertoy_builtins_use_layer_resolution_and_local_clock() -> None:
    shader = fframes.Shader(
        language="shadertoy",
        source="""
            void mainImage(out vec4 c, in vec2 p) {
                c = vec4(iTime, float(iFrame) * iTimeDelta, iResolution.x / 16.0, 1.0);
            }
        """,
    )
    video = compose.Video(
        resolution=(32, 16),
        fps=10,
        backend="skia",
        load_system_fonts=False,
        composition=compose.Composition(
            duration=2,
            children=(compose.ShaderLayer(shader=shader, size=(16, 16)).at(0.5, duration=1),),
        ),
    ).compile()
    reference = native(shader)
    assert not any(video.rgba(4))
    assert not any(video.rgba(15))
    for index in (14, 5, 10):
        pixels = video.rgba(index)
        assert pixels[:4] == reference.rgba(index - 5)[:4]
        assert tuple(pixels[:4]) == pytest.approx(
            ((index - 5) * 25.5, (index - 5) * 25.5, 255, 255), abs=1
        )
        assert pixels[31 * 4 : 32 * 4] == bytes(4)


def test_image_uniform_owns_pixels_after_compilation(tmp_path: Path) -> None:
    path = tmp_path / "image.png"
    compose.Video(
        resolution=(16, 16),
        load_system_fonts=False,
        composition=compose.Composition(
            duration=1, children=(compose.Rectangle(size=(16, 16), fill="#00ff00"),)
        ),
    ).save_png(path)
    shader = fframes.Shader(
        source="uniform shader image; half4 main(float2 p) { return image.eval(p); }",
        uniforms=(fframes.ImageUniform(name="image", source=path),),
    )
    a, b = native(shader), composed(shader)
    path.unlink()
    assert a.rgba(0) == b.rgba(0) == b"\x00\xff\x00\xff" * 256


def test_shader_errors_are_raised_before_rendering() -> None:
    with pytest.raises(ValueError, match="error"):
        composed(fframes.Shader(source="invalid shader"))
    shader = fframes.Shader(source="half4 main(float2 p) { return half4(1); }")
    with pytest.raises(ValueError, match="Skia"):
        native(shader, backend="cpu")
    with pytest.raises(ValueError, match="Skia"):
        composed(shader, backend="cpu")
    with pytest.raises(ValueError, match="absent or has a different type"):
        composed(
            fframes.Shader(
                source="uniform float2 value; half4 main(float2 p) { return half4(value, 0, 1); }",
                uniforms=(fframes.FloatUniform(name="value", value=1),),
            )
        )
    with pytest.raises(ValueError, match="duplicate shader binding"):
        fframes.compile_video(
            fframes.VideoConfig(backend="skia"),
            ("<svg/>",),
            shaders=(fframes.ShaderBinding(name="same", shader=shader),) * 2,
        )


@pytest.mark.parametrize("name", ["iTime", "iResolution", "iTimeDelta", "iFrame", "duplicate"])
def test_shader_uniform_names_cannot_collide(name: str) -> None:
    uniform = fframes.FloatUniform(name=name, value=1)
    with pytest.raises(ValidationError, match="unique"):
        fframes.Shader(source="anything", uniforms=(uniform, uniform))


@pytest.mark.parametrize("backend", ["cpu", "skia"])
def test_masks_clip_groups_in_local_coordinates(backend: Backend) -> None:
    video = compose.Video(
        resolution=(16, 16),
        backend=backend,
        load_system_fonts=False,
        composition=compose.Composition(
            duration=1,
            children=(
                compose.Composition(
                    position=compose.Position(x=4, y=4),
                    size=(8, 8),
                    mask=compose.Mask(size=(8, 8), radius=3),
                    children=(compose.Rectangle(size=(16, 16), fill="#ff0000"),),
                ),
            ),
        ),
    ).compile()
    reference = fframes.compile_video(
        fframes.VideoConfig(width=16, height=16, backend=backend),
        (
            '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">'
            '<defs><clipPath id="mask"><rect width="8" height="8" rx="3"/></clipPath></defs>'
            '<g transform="translate(4 4)"><g clip-path="url(#mask)">'
            '<rect width="16" height="16" fill="red"/></g></g></svg>',
        ),
    )
    assert video.rgba(0) == reference.rgba(0)
    assert video.rgba(0)[:4] == video.rgba(0)[-4:] == bytes(4)


def test_skia_encode_uses_real_shader_frames(tmp_path: Path) -> None:
    shader = fframes.Shader(source="half4 main(float2 p) { return half4(1, 0, 0, 1); }")
    path = tmp_path / "shader.mp4"
    composed(shader).render(path, options=fframes.RenderOptions(concurrency=2))
    assert path.stat().st_size > 1000
    assert not list(tmp_path.glob("fframes-py-*"))


def test_video_uniforms_follow_binding_time_loop_offset_and_eof(tmp_path: Path) -> None:
    source = colored_clip(tmp_path / "source.mp4", ("red", "lime", "blue", "yellow"))
    for looping in (False, True):
        shader = fframes.Shader(
            source="uniform shader image; half4 main(float2 p) { return image.eval(p); }",
            uniforms=(
                fframes.VideoUniform(name="image", source=source, offset=0.25, loop=looping),
            ),
        )
        raw = fframes.Video(
            config=fframes.VideoConfig(width=16, height=16, fps=4, backend="skia"),
            frames=(
                '<svg width="16" height="16"><image href="shader:s" width="16" height="16"/></svg>',
            )
            * 8,
            shaders=(fframes.ShaderBinding(name="s", shader=shader, start_at=0.25, duration=1.5),),
        )
        component = compose.Video(
            resolution=(16, 16),
            fps=4,
            backend="skia",
            load_system_fonts=False,
            composition=compose.Composition(
                duration=2,
                children=(
                    compose.ShaderLayer(shader=shader, size=(16, 16)).at(0.25, duration=1.5),
                ),
            ),
        ).compile()
        for i in (0, 3, 1, 4, 6, 7):
            a, b = raw.rgba(i), component.rgba(i)
            assert a == b
            if i in (0, 7) or (not looping and i >= 4):
                assert not any(a)
            else:
                expected = (255, 255, 0) if i in (3, 6) else (0, 255, 0)
                assert a[:3] == pytest.approx(expected, abs=3)
        component.render(
            tmp_path / f"shader-{looping}.mp4", options=fframes.RenderOptions(concurrency=2)
        )


def test_vector_uniforms_animate_each_coordinate_without_cross_frame_state() -> None:
    shader = fframes.Shader(
        source="uniform float3 rgb; half4 main(float2 p) { return half4(rgb, 1); }",
        uniforms=(
            fframes.VectorUniform(
                name="rgb",
                value=(
                    fframes.Tween(from_value=0, to_value=1, duration=1),
                    fframes.Samples(values=(0, 0.5, 1), fps=2),
                    0.25,
                ),
            ),
        ),
    )
    a, b = native(shader), composed(shader)
    for index, expected in ((19, (255, 255, 64)), (0, (0, 0, 64)), (5, (128, 128, 64))):
        assert a.rgba(index) == b.rgba(index)
        assert a.rgba(index)[:3] == pytest.approx(expected, abs=1)


def test_shader_resolution_animates_and_time_offset_applies_to_uniforms() -> None:
    program = fframes.Shader(
        source="uniform float3 iResolution; uniform float iTime; uniform float level; "
        "half4 main(float2 p) { "
        "return half4(iResolution.x/32, iTime, level, 1); }",
        time_offset=0.5,
        uniforms=(
            fframes.FloatUniform(
                name="level", value=fframes.Tween(from_value=0, to_value=1, duration=1)
            ),
        ),
    )
    video = compose.Video(
        resolution=(32, 16),
        fps=2,
        backend="skia",
        load_system_fonts=False,
        composition=compose.Composition(
            duration=1,
            children=(
                compose.ShaderLayer(
                    shader=program, size=(fframes.Samples(values=(16, 32), fps=2), 16)
                ),
            ),
        ),
    ).compile()
    for i, expected in ((1, (255, 255, 255, 255)), (0, (128, 128, 128, 255))):
        assert video.rgba(i)[:4] == pytest.approx(expected, abs=1)
        assert video.rgba(i)[31 * 4 + 3] == (255 if i else 0)
    with pytest.raises(ValidationError, match="size"):
        compose.ShaderLayer(shader=program, size=(0, 16))
