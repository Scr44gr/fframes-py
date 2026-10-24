from collections.abc import Callable

import pytest
from pydantic import ValidationError

from fframes import Tween
from fframes import three_d as d
from fframes.models import Model

TRIANGLE = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))


@pytest.mark.parametrize(
    ("build", "message"),
    [
        (lambda: d.Sphere(theta=(1, 3)), "theta start"),
        (lambda: d.Cylinder(top=0, bottom=0), "radius must be positive"),
        (lambda: d.Ring(inner=2, outer=1), "inner must be smaller"),
        (lambda: d.Lathe(points=((-1, 0), (1, 1))), "radii must be nonnegative"),
        (lambda: d.Lathe(points=((1, 1), (1, 1))), "distinct profile points"),
        (lambda: d.PixelTexture(size=(2, 2), pixels=(255,) * 4), "width \\* height \\* 4"),
        (lambda: d.EnvironmentPixels(size=(2, 2), pixels=((1, 1, 1),)), "width \\* height"),
        (lambda: d.LinearFog(color="#ffffff", near=2, far=1), "far must be greater"),
        (lambda: d.Group(quaternion=(0, 0, 0, 0)), "quaternion must have nonzero"),
        (lambda: d.Focus(), "exactly one"),
        (lambda: d.Focus(distance=1, point=(0, 0, 0)), "exactly one"),
        (lambda: d.Camera(fov=0.0001), "0.001 and 179.999"),
        (lambda: d.Camera(fov=180), "0.001 and 179.999"),
        (lambda: d.Group(position=(1e8, 0, 0)), "3D coordinates"),
        (lambda: d.Material(emissive_intensity=-1), "between 0 and 10000000"),
        (lambda: d.Orbit(distance=0), "strictly positive"),
        (lambda: d.Material(opacity=Tween(from_value=0, to_value=2, duration=1)), "0 and 1"),
        (lambda: d.DirectionalLight(direction=(0, 0, 0)), "direction must be nonzero"),
        (lambda: d.Reflector(normal=(0, 0, 0)), "direction must be nonzero"),
        (lambda: d.Box(transform=(1,) * 16), "affine, column-major"),
        (
            lambda: d.SkinWeights(joints=((0, 0, 0, 0),), weights=((0.5, 0, 0, 0),)),
            "weights must sum to 1",
        ),
        (
            lambda: d.MeshGeometry(positions=TRIANGLE, indices=(0, 1, 2), uvs=((0, 0),)),
            "uvs must be empty or have one value per vertex",
        ),
        (
            lambda: d.MeshGeometry(
                positions=TRIANGLE,
                indices=(0, 1, 2),
                skin=d.SkinWeights(joints=((0, 0, 0, 0),), weights=((1, 0, 0, 0),)),
            ),
            "skin joints and weights must have one entry per vertex",
        ),
        (
            lambda: d.MeshGeometry(
                positions=TRIANGLE,
                indices=(0, 1, 2),
                morph_targets=(d.MorphTarget(positions=((0, 0, 0),)),),
            ),
            "morph target deltas must match",
        ),
    ],
)
def test_invalid_3d_inputs_fail_before_rendering_with_specific_correction(
    build: Callable[[], Model], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        build()


def test_duplicate_channels_cannot_silently_replace_a_node_property() -> None:
    channel = d.Translation(node="pivot", times=(0,), values=((0, 0, 0),))
    with pytest.raises(ValidationError, match="one channel per node and property"):
        d.Animation(name="duplicate", duration=1, channels=(channel, channel))


def test_vertex_weights_require_a_skin_with_named_joints() -> None:
    geometry = d.MeshGeometry(
        positions=TRIANGLE,
        indices=(0, 1, 2),
        skin=d.SkinWeights(joints=((0, 0, 0, 0),) * 3, weights=((1, 0, 0, 0),) * 3),
    )
    renderer = d.Renderer(scene=d.Scene(nodes=(d.Mesh(geometry=geometry),)))
    with pytest.raises(ValueError, match=r"geometry.skin.*Mesh\(skin=Skin"):
        renderer.rgba()
