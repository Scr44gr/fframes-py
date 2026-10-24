import os
from typing import Literal

import pytest

import fframes as f
from fframes import compose as c
from fframes import three_d as d


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
def test_scene_states_change_geometry_material_and_hierarchy_with_random_access(
    device: Literal["cpu", "gpu"],
) -> None:
    first = d.Scene(
        nodes=(
            d.Mesh(
                name="subject",
                geometry=d.Box(),
                material=d.Material(shading="unlit", color="#ff0000"),
            ),
        )
    )
    second = d.Scene(
        nodes=(
            d.Group(
                position=(0.5, 0, 0),
                children=(
                    d.Mesh(
                        name="subject",
                        geometry=d.Sphere(radius=0.7),
                        material=d.Material(shading="unlit", color="#0000ff"),
                    ),
                ),
            ),
        )
    )
    last = d.Scene()
    frames = d.SceneFrames(frames=(first, second, last), fps=2)
    renderer = d.Renderer(
        scene=frames, size=(32, 32), settings=d.RenderSettings(device=device, tone_mapping="linear")
    )
    assert renderer.world_position("subject", time=0) == (0, 0, 0)
    assert renderer.world_position("subject", time=0.5) == (0.5, 0, 0)
    assert renderer.bounds("subject", time=0) != renderer.bounds("subject", time=0.5)
    assert not any(renderer.rgba(2))
    with pytest.raises(ValueError, match="no 3D node"):
        renderer.world_position("subject", time=1)
    video = c.Video(
        resolution=(32, 32),
        fps=4,
        composition=c.Composition(duration=2, children=(c.Scene3D(renderer=renderer),)),
    ).compile()
    raw = f.Video(
        config=f.VideoConfig(width=32, height=32, fps=4),
        frames=(
            '<svg width="32" height="32"><image href="scene:states" width="32" height="32"/></svg>',
        )
        * 8,
        scenes=(d.SceneBinding(name="states", renderer=renderer),),
    )
    for index in (3, 0, 4, 2, 1, 7):
        assert video.rgba(index) == raw.rgba(index)
        assert video.rgba(index) == renderer.rgba(index / 4)
    assert renderer.rgba(0) != renderer.rgba(0.5)
