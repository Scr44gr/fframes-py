from math import sqrt

import pytest
from pydantic import ValidationError

from fframes import Tween
from fframes import three_d as d
from fframes.three_d.types import IDENTITY
from tests.test_three_d import renderer


def test_keyframe_interpolation_quaternion_blending_and_random_access() -> None:
    clip = d.Animation(
        name="move",
        duration=1,
        loop=False,
        weight=0.5,
        channels=(
            d.Translation(node="linear", times=(0, 1), values=((0, 0, 0), (2, 0, 0))),
            d.Translation(
                node="step", times=(0, 1), values=((0, 0, 0), (2, 0, 0)), interpolation="step"
            ),
            d.Translation(
                node="cubic",
                times=(0, 1),
                interpolation="cubic_spline",
                values=(
                    (0, 0, 0),
                    (0, 0, 0),
                    (2, 0, 0),
                    (2, 0, 0),
                    (2, 0, 0),
                    (0, 0, 0),
                ),
            ),
            d.Rotation(node="rotate", times=(0, 1), values=((0, 0, 0, 1), (0, 0, 1, 0))),
        ),
    )
    scene = renderer(
        d.Scene(
            nodes=tuple(
                d.Group(name=name)
                for name in (
                    "linear",
                    "step",
                    "cubic",
                    "rotate",
                )
            ),
            animations=(clip,),
        )
    )
    for time in (1.0, 0.5, 0.25, 0.0):
        assert scene.world_position("linear", time=time) == pytest.approx((time, 0, 0))
        assert scene.world_position("cubic", time=time) == pytest.approx((time, 0, 0))
        assert scene.world_position("step", time=time) == pytest.approx((float(time == 1), 0, 0))
    point = scene.local_to_world("rotate", (1, 0, 0), time=0.5)
    assert point == pytest.approx((sqrt(0.5), sqrt(0.5), 0), abs=1e-6)
    assert scene.world_matrix("linear", time=0.5)[12:15] == pytest.approx((0.5, 0, 0))
    assert scene.bounds("linear") is None


def test_skin_and_morph_deformation_change_pixels_without_changing_base_geometry() -> None:
    points = ((-0.7, -0.7, 0), (0.7, -0.7, 0), (0, 0.7, 0))
    material = d.Material(shading="unlit")
    motion = Tween(from_value=0, to_value=1, duration=1)
    skinned = renderer(
        d.Scene(
            nodes=(
                d.Group(name="joint", position=(motion, 0, 0)),
                d.Mesh(
                    name="mesh",
                    geometry=d.MeshGeometry(
                        positions=points,
                        indices=(0, 1, 2),
                        skin=d.SkinWeights(joints=((0, 0, 0, 0),) * 3, weights=((1, 0, 0, 0),) * 3),
                    ),
                    skin=d.Skin(joints=("joint",), inverse_bind_matrices=(IDENTITY,)),
                    material=material,
                ),
            )
        )
    )
    morphed = renderer(
        d.Scene(
            nodes=(
                d.Mesh(
                    name="mesh",
                    material=material,
                    geometry=d.MeshGeometry(
                        positions=points,
                        indices=(0, 1, 2),
                        morph_targets=(d.MorphTarget(positions=((1, 0, 0),) * 3),),
                    ),
                ),
            ),
            animations=(
                d.Animation(
                    name="morph",
                    duration=1,
                    loop=False,
                    channels=(d.MorphWeights(node="mesh", times=(0, 1), values=((0,), (1,))),),
                ),
            ),
        )
    )
    for time in (0.0, 0.5, 1.0):
        assert skinned.rgba(time) == morphed.rgba(time)
    assert skinned.rgba(0) != skinned.rgba(1)
    assert skinned.bounds("mesh", time=0) == skinned.bounds("mesh", time=1)


def test_instance_colors_animate_and_negative_node_scale_mirrors() -> None:
    from fframes import ColorTween

    mesh = d.Mesh(
        geometry=d.Plane(size=(2, 2)),
        material=d.Material(shading="unlit"),
        scale=(-1, 1, 1),
        instances=d.Instances(
            transforms=(IDENTITY,),
            colors=(ColorTween(from_value="#ff0000", to_value="#0000ff", duration=1),),
        ),
    )
    scene = renderer(d.Scene(nodes=(mesh,)))
    start, end = scene.rgba(), scene.rgba(1)
    assert max(start[0::4]) == 255
    assert max(start[2::4]) == 0
    assert max(end[2::4]) == 255
    assert max(end[0::4]) == 0


def test_camera_orbit_projection_and_runtime_degenerate_pose() -> None:
    scene = d.Renderer(
        scene=d.Scene(),
        size=(64, 64),
        settings=d.RenderSettings(device="cpu"),
        camera=d.Camera(
            orbit=d.Orbit(distance=5, azimuth=Tween(from_value=0, to_value=90, duration=1))
        ),
    )
    point = scene.project((0, 0, 0), time=1)
    assert point is not None
    assert point[:2] == pytest.approx((32, 32))
    assert scene.pixel_size((0, 0, 0), 1, time=1) == pytest.approx(64 / (10 * 0.41421356))
    singular = d.Renderer(
        scene=d.Scene(),
        settings=d.RenderSettings(device="cpu"),
        camera=d.Camera(position=(0, 0, Tween(from_value=1, to_value=-1, duration=1))),
    )
    with pytest.raises(ValueError, match=r"camera at 0\.5s"):
        singular.rgba(0.5)
    with pytest.raises(ValidationError, match="position and target"):
        d.Camera(position=(0, 0, 0))
    with pytest.raises(ValidationError, match="orbit or position"):
        d.Camera(position=(1, 0, 0), orbit=d.Orbit(distance=5))


def test_3d_validation_explains_invalid_channels_and_buffers() -> None:
    with pytest.raises(ValidationError, match="strictly increasing"):
        d.Translation(node="node", times=(1, 0), values=((0, 0, 0),) * 2)
    with pytest.raises(ValidationError, match="requires 6 values"):
        d.Translation(
            node="node", times=(0, 1), values=((0, 0, 0),) * 2, interpolation="cubic_spline"
        )
    with pytest.raises(ValidationError, match="nonzero quaternions"):
        d.Rotation(node="node", times=(0,), values=((0, 0, 0, 0),))
    with pytest.raises(ValidationError, match="target count"):
        d.MorphWeights(node="node", times=(0, 1), values=((1,), (0, 1)))
    with pytest.raises(ValidationError, match="last keyframe"):
        d.Animation(
            name="cut",
            duration=0.5,
            channels=(d.Scaling(node="node", times=(0, 1), values=((1, 1, 1),) * 2),),
        )
    with pytest.raises(ValidationError, match="nonzero"):
        d.Scaling(node="node", times=(0,), values=((0, 1, 1),))
    with pytest.raises(ValidationError, match="time replaces"):
        d.Playback(name="move", time=0, speed=2)
    with pytest.raises(ValidationError, match="invertible"):
        d.Box(transform=(0,) * 15 + (1,))
    with pytest.raises(ValidationError, match="alpha"):
        d.Material(color="#ffffff00")
    with pytest.raises(ValidationError, match="one matrix per joint"):
        d.Skin(joints=("joint",), inverse_bind_matrices=())
    with pytest.raises(ValidationError, match="one color per instance"):
        d.Instances(transforms=(IDENTITY,), colors=("#ffffff",) * 2)
    with pytest.raises(ValidationError, match="skin or morph_weights"):
        d.Mesh(geometry=d.Box(), instances=d.Instances(transforms=(IDENTITY,)), morph_weights=(1,))
