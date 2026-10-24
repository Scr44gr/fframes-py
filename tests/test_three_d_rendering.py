import os
import sys
from math import pi
from typing import TYPE_CHECKING

import pytest

import fframes
from fframes import compose
from fframes import three_d as d
from fframes.three_d.scene import LightType
from tests.test_three_d import pixel, renderer

if TYPE_CHECKING:
    from fframes.models import Backend


@pytest.mark.parametrize(
    "light",
    [
        d.AmbientLight(),
        d.HemisphereLight(),
        d.DirectionalLight(direction=(0, 0, -1)),
        d.PointLight(),
        d.SpotLight(direction=(0, 0, -1)),
    ],
)
def test_light_families_illuminate_pbr_surfaces(light: LightType) -> None:
    plane = d.Mesh(geometry=d.Plane(size=(2, 2)))
    dark = renderer(d.Scene(nodes=(plane,))).rgba()
    lit = renderer(d.Scene(nodes=(plane, d.Light(light=light, position=(0, 0, 2))))).rgba()
    assert pixel(lit)[0] > pixel(dark)[0] + 25
    assert pixel(lit)[3] == 255


@pytest.mark.parametrize(
    "fog",
    [d.LinearFog(color="#0000ff", near=1, far=2), d.ExponentialFog(color="#0000ff", density=1)],
)
def test_hdr_environment_and_fog_obey_material_opt_out(fog: d.LinearFog | d.ExponentialFog) -> None:
    environment = d.EnvironmentMap(source=d.EnvironmentPixels(size=(2, 1), pixels=((2, 0, 0),) * 2))
    scene = renderer(d.Scene(environment=environment, background=d.EnvironmentBackground()))
    assert pixel(scene.rgba()) == (255, 0, 0, 255)

    def picture(*, enabled: bool) -> bytes:
        return renderer(
            d.Scene(
                fog=fog,
                nodes=(
                    d.Mesh(
                        geometry=d.Plane(size=(2, 2)),
                        material=d.Material(shading="unlit", color="#ff0000", fog=enabled),
                    ),
                ),
            )
        ).rgba()

    assert pixel(picture(enabled=True)) == (0, 0, 255, 255)
    assert pixel(picture(enabled=False)) == (255, 0, 0, 255)


def test_native_motion_blur_focus_and_bloom_change_the_expected_regions() -> None:
    scene = d.Scene(
        nodes=(
            d.Mesh(
                geometry=d.Box(size=(0.5, 0.5, 0.5)),
                position=(fframes.Tween(from_value=-1, to_value=1, duration=0.1), 0, 0),
                material=d.Material(shading="unlit", color=(4, 4, 4)),
            ),
        )
    )
    crisp = renderer(scene).rgba(0.05)
    blurred = d.Renderer(
        scene=scene,
        size=(64, 64),
        fps=10,
        settings=d.RenderSettings(device="cpu", tone_mapping="linear", motion_samples=8, shutter=1),
    ).rgba(0.05)
    assert sum(alpha > 0 for alpha in blurred[3::4]) > sum(alpha > 0 for alpha in crisp[3::4])
    glowing = d.Renderer(
        scene=scene,
        size=(64, 64),
        settings=d.RenderSettings(
            device="cpu",
            tone_mapping="linear",
            bloom=d.Bloom(threshold=1, radius=0.8, strength=1),
        ),
    ).rgba(0.05)
    assert sum(glowing[0::4]) > sum(crisp[0::4])

    def focus(distance: float) -> bytes:
        return d.Renderer(
            scene=scene,
            size=(64, 64),
            camera=d.Camera(focus=d.Focus(distance=distance, blur=60)),
            settings=d.RenderSettings(device="cpu", tone_mapping="linear"),
        ).rgba(0.05)

    assert focus(5) != focus(1)
    point_focus = d.Renderer(
        scene=scene,
        size=(64, 64),
        camera=d.Camera(
            focus=d.Focus(point=(0, 0, 0), blur=60),
        ),
        settings=d.RenderSettings(device="cpu", tone_mapping="linear"),
    ).rgba(0.05)
    assert point_focus == focus(5)


def test_particles_follow_occlusion_and_visibility_frames() -> None:
    scene = renderer(
        d.Scene(
            nodes=(
                d.Particles(
                    items=(
                        d.Particle(position=(0, 0, 0), size=0.5, color="#0000ff"),
                        d.Particle(position=(1.2, 0, 0), size=0.3, color="#00ff00"),
                    )
                ),
                d.Mesh(
                    geometry=d.Plane(size=(1, 1)),
                    position=(0, 0, 1),
                    visible=d.VisibilityFrames(values=(True, False), fps=10),
                    material=d.Material(shading="unlit", color="#ff0000"),
                ),
            )
        )
    )
    assert pixel(scene.rgba()) == (255, 0, 0, 255)
    assert pixel(scene.rgba(0.1))[2] > 200
    assert max(scene.rgba()[1::4]) > 200


def test_reflector_and_shadow_maps_affect_receiver_pixels() -> None:
    def picture(*, shadows: bool, reflection: bool) -> bytes:
        scene = d.Scene(
            environment=d.Studio(intensity=0.3),
            reflector=d.Reflector() if reflection else None,
            nodes=(
                d.Mesh(
                    geometry=d.Box(), position=(0, 0.6, 0), material=d.Material(color="#ff4400")
                ),
                d.Mesh(
                    geometry=d.Plane(axis="xz", size=(6, 6)),
                    material=d.Material(reflection=0.7 if reflection else 0),
                ),
                d.Light(
                    light=d.DirectionalLight(
                        direction=(1, -1, -1), shadow=d.Shadow(map_size=64) if shadows else None
                    )
                ),
            ),
        )
        return d.Renderer(
            scene=scene,
            camera=d.Camera(position=(2, 3, 5)),
            size=(64, 64),
            settings=d.RenderSettings(device="cpu"),
        ).rgba()

    baseline = picture(shadows=False, reflection=False)
    assert picture(shadows=True, reflection=False) != baseline
    assert picture(shadows=False, reflection=True) != baseline


def test_gpu_limits_fall_back_explicitly_in_auto_mode() -> None:
    scene = d.Scene(nodes=tuple(d.Light(light=d.PointLight()) for _ in range(17)))
    assert not d.Renderer(scene=scene, size=(16, 16)).uses_gpu
    if os.environ.get("FFRAMES_TEST_3D_GPU"):
        with pytest.raises(ValueError, match="17/16 direct lights"):
            _ = d.Renderer(scene=scene, settings=d.RenderSettings(device="gpu")).uses_gpu


@pytest.mark.skipif(
    not os.environ.get("FFRAMES_TEST_3D_GPU"), reason="Set FFRAMES_TEST_3D_GPU for real GPU parity"
)
def test_gpu_layer_matches_cpu_and_survives_vulkan_context_changes() -> None:
    scene = d.Scene(
        nodes=(
            d.Mesh(
                geometry=d.Box(),
                rotation=(0, pi / 6, 0),
                material=d.Material(shading="unlit", color="#33cc66"),
            ),
        )
    )
    cpu = renderer(scene).rgba()
    gpu = d.Renderer(
        scene=scene, size=(64, 64), settings=d.RenderSettings(device="gpu", tone_mapping="linear")
    )
    assert gpu.uses_gpu
    standalone = gpu.rgba()
    assert pixel(standalone) == pytest.approx(pixel(cpu), abs=2)
    backend: Backend = "metal" if sys.platform == "darwin" else "vulkan"
    composed = compose.Video(
        resolution=(64, 64),
        fps=10,
        backend=backend,
        composition=compose.Composition(duration=0.2, children=(compose.Scene3D(renderer=gpu),)),
    ).compile()
    assert pixel(composed.rgba(0)) == pytest.approx(pixel(cpu), abs=2)
    # The retained program must remain usable after the SVG device and its GPU layers are dropped.
    assert pixel(gpu.rgba()) == pytest.approx(pixel(cpu), abs=2)
