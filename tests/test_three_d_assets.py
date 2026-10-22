import os
import shutil
import struct
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import pytest

import fframes
from fframes import three_d as d
from fframes.three_d.scene import TextureSource
from tests.test_media_bindings import colored_clip
from tests.test_three_d import pixel, renderer

if TYPE_CHECKING:
    from fframes.three_d.geometry import GeometryType


@pytest.fixture
def model(tmp_path: Path) -> Path:
    data = struct.pack(
        "<9f4H8f", -0.7, -0.7, 0, 0.7, -0.7, 0, 0, 0.7, 0, 0, 1, 2, 0, 0, 1, 0, 0, 0, 1, 0, 0
    )
    (tmp_path / "mesh.bin").write_bytes(data)
    source = tmp_path / "triangle.gltf"
    source.write_text(
        """{
      "asset":{"version":"2.0"}, "scene":0, "scenes":[{"nodes":[0]}],
      "nodes":[{"name":"triangle", "mesh":0}],
      "buffers":[{"uri":"mesh.bin","byteLength":76}],
      "bufferViews":[{"buffer":0,"byteOffset":0,"byteLength":36},
        {"buffer":0,"byteOffset":36,"byteLength":6},
        {"buffer":0,"byteOffset":44,"byteLength":8},
        {"buffer":0,"byteOffset":52,"byteLength":24}],
      "accessors":[{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3",
        "min":[-0.7,-0.7,0],"max":[0.7,0.7,0]},
        {"bufferView":1,"componentType":5123,"count":3,"type":"SCALAR"},
        {"bufferView":2,"componentType":5126,"count":2,"type":"SCALAR","min":[0],"max":[1]},
        {"bufferView":3,"componentType":5126,"count":2,"type":"VEC3"}],
      "meshes":[{"primitives":[{"attributes":{"POSITION":0},"indices":1,"material":0}]}],
      "extensionsUsed":["KHR_materials_unlit"],
      "materials":[{"extensions":{"KHR_materials_unlit":{}}}],
      "animations":[{"name":"move","samplers":[{"input":2,"output":3}],
        "channels":[{"sampler":0,"target":{"node":0,"path":"translation"}}]}]
    }""",
        encoding="utf-8",
    )
    return source


def test_gltf_metadata_playback_and_pose_overrides(model: Path) -> None:
    info = d.probe_model(model)
    assert info.nodes == ("triangle",)
    assert info.meshes == 1
    assert [(clip.name, clip.duration, clip.channels) for clip in info.animations] == [
        ("move", 1, 1)
    ]
    scene = renderer(
        d.Scene(
            nodes=(
                d.Model3D(
                    name="asset", source=model, animations=(d.Playback(name="move", loop=False),)
                ),
            )
        )
    )
    assert scene.world_position("asset/triangle", time=0.5) == pytest.approx((0.5, 0, 0))
    assert scene.rgba() != scene.rgba(1)
    overridden = renderer(
        d.Scene(
            nodes=(
                d.Model3D(
                    name="asset",
                    source=model,
                    animations=(d.Playback(name="move"),),
                    poses=(d.Pose(name="triangle", position=(2, 0, 0)),),
                ),
            )
        )
    )
    assert overridden.world_position("asset/triangle", time=0.5) == (2, 0, 0)
    with pytest.raises(ValueError, match="no animation"):
        renderer(
            d.Scene(nodes=(d.Model3D(source=model, animations=(d.Playback(name="missing"),)),))
        ).rgba()
    model.with_name("mesh.bin").unlink()
    with pytest.raises((RuntimeError, ValueError), match=r"mesh\.bin"):
        d.probe_model(model)


def test_font_outlines_preserve_holes_and_extruded_glyph_pixels() -> None:
    font = Path(__file__).parent / "assets" / "Tuffy.ttf"
    glyphs = d.text_shapes(font, "B A", size=2, letter_spacing=0.1)
    assert [glyph.character for glyph in glyphs] == ["B", " ", "A"]
    assert glyphs[1].shapes == ()
    assert glyphs[2].origin[0] > glyphs[0].advance
    assert any(shape.holes for shape in glyphs[0].shapes)
    recipes: tuple[GeometryType, ...] = (
        d.TextGeometry(font=font, text="B", height=2),
        d.Merged(parts=tuple(d.Extrude(shape=shape, depth=0.1) for shape in glyphs[0].shapes)),
    )
    pictures = tuple(
        renderer(
            d.Scene(nodes=(d.Mesh(geometry=recipe, material=d.Material(shading="unlit")),))
        ).rgba()
        for recipe in recipes
    )
    assert any(pictures[0])
    assert pictures[0] == pictures[1]
    with pytest.raises(RuntimeError, match="glyph"):
        d.text_shapes(font, "\U0010ffff")


def test_stl_and_pixel_textures_use_actual_buffers(tmp_path: Path) -> None:
    source = tmp_path / "mesh.stl"
    source.write_text(
        """solid triangle
    facet normal 0 0 1
    outer loop
    vertex -1 -1 0
    vertex 1 -1 0
    vertex 0 1 0
    endloop
    endfacet
    endsolid triangle
    """,
        encoding="ascii",
    )
    texture = d.PixelTexture(size=(1, 1), pixels=(51, 204, 102, 255))
    assert pixel(textured(texture).rgba()) == pytest.approx((51, 204, 102, 255), abs=1)
    mesh = d.Mesh(
        geometry=d.STL(source=source, normals="smooth"),
        material=d.Material(shading="unlit", color="#33cc66"),
    )
    assert pixel(renderer(d.Scene(nodes=(mesh,))).rgba()) == pytest.approx(
        (51, 204, 102, 255), abs=1
    )


def test_svg_shader_texture_uses_local_clock_after_svg_eof() -> None:
    shader = fframes.Shader(
        source="uniform float t; half4 main(float2 p) { return half4(1-t,0,t,1); }",
        uniforms=(
            fframes.FloatUniform(
                name="t", value=fframes.Tween(from_value=0, to_value=1, duration=1)
            ),
        ),
    )
    texture = d.SvgTexture(
        size=(64, 64),
        frames=(
            '<svg width="64" height="64"><image href="shader:color" width="64" height="64"/></svg>',
        ),
        shaders=(fframes.ShaderBinding(name="color", shader=shader),),
    )
    scene = textured(texture)
    assert pixel(scene.rgba()) == (255, 0, 0, 255)
    assert pixel(scene.rgba(1)) == (0, 0, 255, 255)


def textured(source: TextureSource) -> d.Renderer:
    return renderer(
        d.Scene(
            nodes=(
                d.Mesh(
                    geometry=d.Plane(size=(3, 3)),
                    material=d.Material(
                        shading="unlit",
                        map=d.Texture(source=source),
                    ),
                ),
            )
        )
    )


def test_video_texture_resizes_seeks_loops_and_keeps_svg_bindings_alive(tmp_path: Path) -> None:
    source = colored_clip(tmp_path / "clip.mp4", ("red", "lime", "blue", "yellow"))
    path = tmp_path / "clip.mkv"
    ffmpeg = shutil.which("ffmpeg")
    assert ffmpeg is not None
    subprocess.run(  # noqa: S603 -- Remux a known fixture with explicit stream timing.
        [ffmpeg, "-v", "error", "-i", str(source), "-c", "copy", str(path)],
        check=True,
    )
    assert fframes.probe_video(path).duration == pytest.approx(1)

    direct = textured(d.VideoTexture(source=path, offset=0.25, loop=True, size=(8, 8)))
    wrapped = textured(
        d.SvgTexture(
            size=(64, 64),
            fps=10,
            frames=(
                '<svg width="64" height="64">'
                '<image href="video:clip" width="64" height="64"/></svg>',
            ),
            clips=(fframes.VideoBinding(name="clip", source=path, offset=0.25, loop=True),),
        )
    )
    for time, expected in (
        (0.3, (0, 0, 255, 255)),
        (0.0, (0, 255, 0, 255)),
        (0.75, (0, 255, 0, 255)),
    ):
        assert pixel(direct.rgba(time)) == pytest.approx(expected, abs=5)
        assert pixel(wrapped.rgba(time)) == pytest.approx(expected, abs=5)


def test_composition_texture_keeps_native_animation_and_rejects_hidden_audio() -> None:
    from fframes import compose

    video = compose.Video(
        resolution=(64, 64),
        fps=10,
        composition=compose.Composition(
            duration=1,
            children=(
                compose.Rectangle(
                    size=(64, 64),
                    fill=fframes.ColorTween(
                        from_value="#ff0000",
                        to_value="#0000ff",
                        duration=0.9,
                    ),
                ),
            ),
        ),
    )
    scene = renderer(
        d.Scene(
            nodes=(
                d.Mesh(
                    geometry=d.Plane(size=(3, 3)),
                    material=d.Material(shading="unlit", map=video.texture()),
                ),
            )
        )
    )
    assert pixel(scene.rgba()) == (255, 0, 0, 255)
    assert pixel(scene.rgba(0.9)) == (0, 0, 255, 255)
    assert scene.rgba(0.9) == scene.rgba(2)
    assert scene.rgba(0) == scene.rgba(0)
    with pytest.raises(ValueError, match="outer composition"):
        compose.Video(
            composition=compose.Composition(
                duration=1, children=(compose.Audio(source="unused.wav"),)
            )
        ).texture()


@pytest.mark.parametrize("segments", [(1, 1), (3, 2)])
@pytest.mark.parametrize(
    "device",
    [
        "cpu",
        pytest.param(
            "gpu",
            marks=pytest.mark.skipif(
                not os.environ.get("FFRAMES_TEST_3D_GPU"),
                reason="Set FFRAMES_TEST_3D_GPU for real GPU parity",
            ),
        ),
    ],
)
def test_xy_plane_maps_the_whole_texture_once_in_top_left_order(
    segments: tuple[int, int],
    device: Literal["cpu", "gpu"],
) -> None:
    image = d.Texture(
        source=d.SvgTexture(
            size=(64, 64),
            frames=(
                '<svg width="64" height="64">'
                '<rect width="32" height="32" fill="red"/>'
                '<rect x="32" width="32" height="32" fill="lime"/>'
                '<rect y="32" width="32" height="32" fill="blue"/>'
                '<rect x="32" y="32" width="32" height="32" fill="yellow"/></svg>',
            ),
        )
    )
    scene = d.Renderer(
        scene=d.Scene(
            nodes=(
                d.Mesh(
                    geometry=d.Plane(size=(2, 2), segments=segments),
                    material=d.Material(shading="unlit", map=image),
                ),
            )
        ),
        size=(64, 64),
        camera=d.Camera(ortho_height=2),
        settings=d.RenderSettings(device=device, tone_mapping="linear"),
    ).rgba()
    assert pixel(scene, 16, 16) == (255, 0, 0, 255)
    assert pixel(scene, 48, 16) == (0, 255, 0, 255)
    assert pixel(scene, 16, 48) == (0, 0, 255, 255)
    assert pixel(scene, 48, 48) == (255, 255, 0, 255)


def test_imported_mesh_material_override_preserves_animation_and_rejects_unknown_targets(
    model: Path,
) -> None:
    scene = renderer(
        d.Scene(
            nodes=(
                d.Model3D(
                    source=model,
                    name="asset",
                    animations=(d.Playback(name="move", loop=False),),
                    materials=(
                        d.MaterialOverride(
                            node="triangle", material=d.Material(shading="unlit", color="#ff0000")
                        ),
                    ),
                ),
            )
        )
    )
    assert pixel(scene.rgba()) == (255, 0, 0, 255)
    assert scene.world_position("asset/triangle", time=0.5) == pytest.approx((0.5, 0, 0))
    missing = renderer(
        d.Scene(
            nodes=(
                d.Model3D(
                    source=model,
                    materials=(d.MaterialOverride(node="missing", material=d.Material()),),
                ),
            )
        )
    )
    with pytest.raises(ValueError, match="unique model mesh"):
        missing.rgba()
