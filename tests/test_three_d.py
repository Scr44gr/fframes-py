from math import pi

import pytest
from pydantic import ValidationError

import fframes
from fframes import compose
from fframes import three_d as d
from fframes.models import Backend
from fframes.three_d.geometry import GeometryType


def pixel(rgba: bytes, x: int = 32, y: int = 32) -> tuple[int, ...]:
    return tuple(rgba[(y * 64 + x) * 4 : (y * 64 + x + 1) * 4])


def renderer(scene: d.Scene, *, antialias: bool = True) -> d.Renderer:
    return d.Renderer(
        scene=scene,
        size=(64, 64),
        fps=10,
        settings=d.RenderSettings(device="cpu", tone_mapping="linear", antialias=antialias),
    )


@pytest.mark.parametrize("backend", ["cpu", "skia"])
def test_3d_layers_share_pixels_and_local_timing_between_apis(backend: Backend) -> None:
    scene = renderer(
        d.Scene(
            nodes=(
                d.Mesh(
                    geometry=d.Box(),
                    material=d.Material(shading="unlit", color="#ee4422"),
                    position=(fframes.Tween(from_value=-1, to_value=1, duration=0.3), 0, 0),
                    rotation=(0, fframes.Tween(from_value=0, to_value=pi, duration=0.3), 0),
                ),
            )
        )
    )
    svg = '<svg width="64" height="64"><image href="scene:demo" width="64" height="64"/></svg>'
    native = fframes.Video(
        config=fframes.VideoConfig(width=64, height=64, fps=10, backend=backend),
        frames=(svg,) * 10,
        scenes=(d.SceneBinding(name="demo", renderer=scene, start_at=0.2, duration=0.4),),
    )
    composed = compose.Video(
        resolution=(64, 64),
        fps=10,
        backend=backend,
        composition=compose.Composition(
            duration=1, children=(compose.Scene3D(renderer=scene).at(0.2, duration=0.4),)
        ),
    ).compile()
    for frame in (5, 2, 4, 3):
        assert native.rgba(frame) == composed.rgba(frame)
        assert any(native.rgba(frame))
    assert native.rgba(2) != native.rgba(5)
    assert native.rgba(2) == native.rgba(2)
    for frame in (0, 1, 6, 9):
        assert not any(native.rgba(frame))
        assert not any(composed.rgba(frame))


def test_hierarchy_projection_and_depth_use_world_coordinates() -> None:
    scene = renderer(
        d.Scene(
            nodes=(
                d.Group(
                    position=(1, 0, 0),
                    rotation=(0, 0, pi / 2),
                    children=(d.Mesh(name="child", geometry=d.Box(), position=(1, 0, 0)),),
                ),
                d.Mesh(
                    geometry=d.Plane(size=(2, 2)),
                    material=d.Material(shading="unlit", color="#ff0000"),
                    position=(0, 0, 1),
                ),
                d.Mesh(
                    geometry=d.Plane(size=(3, 3)),
                    material=d.Material(shading="unlit", color="#0000ff"),
                ),
            )
        )
    )
    assert scene.world_position("child") == pytest.approx((1, 1, 0), abs=1e-6)
    projected = scene.project((0, 0, 0))
    assert projected is not None
    assert projected[:2] == pytest.approx((32, 32))
    assert scene.project((0, 0, 10)) is None
    assert pixel(scene.rgba()) == (255, 0, 0, 255)
    with pytest.raises(ValueError, match="no 3D node named"):
        scene.world_position("missing")


@pytest.mark.parametrize(
    "geometry",
    [
        d.Box(radius=0.1),
        d.Sphere(theta=(0, pi / 2)),
        d.Cylinder(top=0),
        d.Cylinder(open=True),
        d.Capsule(),
        d.Torus(arc=pi),
        d.Ring(inner=0.2),
        d.Lathe(points=((0.5, -1), (1, 0), (0.5, 1))),
        d.Extrude(shape=d.Shape(outer=((-1, -1), (1, -1), (1, 1), (-1, 1)))),
        d.Icosahedron(detail=1),
        d.Tube(path=((-1, -1, 0), (0, 1, 0), (1, -1, 0))),
        d.Merged(parts=(d.Box(), d.Sphere(radius=0.7))),
        d.MeshGeometry(positions=((-1, -1, 0), (1, -1, 0), (0, 1, 0)), indices=(0, 1, 2)),
    ],
)
def test_geometry_recipes_produce_visible_lit_surfaces(geometry: GeometryType) -> None:
    scene = renderer(d.Scene(nodes=(d.Mesh(geometry=geometry),), environment=d.Studio()))
    pixels = scene.rgba()
    assert sum(pixels[3::4]) > 255 * 20
    assert max(pixels[0::4]) > 20
    assert 0 in pixels[3::4]


def test_nested_svg_and_scene_textures_preserve_color_and_alpha() -> None:
    nested = renderer(d.Scene(background="#33cc66"))
    svg = '<svg width="64" height="64"><image href="scene:inner" width="64" height="64"/></svg>'
    texture = d.Texture(
        source=d.SvgTexture(
            frames=(svg,),
            size=(64, 64),
            scenes=(d.SceneBinding(name="inner", renderer=nested),),
        )
    )
    scene = renderer(
        d.Scene(
            nodes=(
                d.Mesh(
                    geometry=d.Plane(size=(3, 3)),
                    material=d.Material(shading="unlit", map=texture),
                ),
            )
        )
    )
    assert pixel(scene.rgba()) == pytest.approx((51, 204, 102, 255), abs=1)
    assert pixel(scene.rgba(), 0, 0) == (0, 0, 0, 0)
    direct = renderer(
        d.Scene(
            nodes=(
                d.Mesh(
                    geometry=d.Plane(size=(3, 3)),
                    material=d.Material(
                        shading="unlit", map=d.Texture(source=d.SceneTexture(renderer=nested))
                    ),
                ),
            )
        )
    )
    assert scene.rgba() == direct.rgba()


def test_msaa_produces_partial_coverage_on_diagonal_edges() -> None:
    scene = d.Scene(
        nodes=(
            d.Mesh(
                geometry=d.Plane(size=(2, 2)),
                rotation=(0, 0, 0.3),
                material=d.Material(shading="unlit"),
            ),
        )
    )
    smooth = renderer(scene).rgba()[3::4]
    jagged = renderer(scene, antialias=False).rgba()[3::4]
    assert any(0 < alpha < 255 for alpha in smooth)
    assert set(jagged) <= {0, 255}


def test_3d_validation_rejects_incoherent_geometry_and_camera() -> None:
    with pytest.raises(ValidationError, match="radius"):
        d.Box(size=(1, 2, 3), radius=0.6)
    with pytest.raises(ValidationError, match="complete triangles"):
        d.MeshGeometry(positions=((0, 0, 0), (1, 0, 0), (0, 1, 0)), indices=(0, 1, 3))
    with pytest.raises(ValidationError, match="nonzero"):
        d.Mesh(geometry=d.Box(), scale=(fframes.Tween(from_value=0, to_value=1, duration=1), 1, 1))
    with pytest.raises(ValidationError, match="near"):
        d.Camera(near=10, far=1)
    with pytest.raises(ValidationError, match="rotation or quaternion"):
        d.Group(rotation=(1, 0, 0), quaternion=(0, 0, 0, 1))
