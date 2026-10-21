"""Shared nested-scene data, inspired by upstream v1.3.0's svg-in-3d example."""

from math import tau
from pathlib import Path

import fframes
from fframes import three_d as d
from fframes.compose import CompiledVideo

DURATION = 3
FPS = 30
SETTINGS = d.RenderSettings(device="cpu")


def cube(size: tuple[int, int], settings: d.RenderSettings) -> d.Renderer:
    """Light an animated rounded cube for the monitor's display."""
    return d.Renderer(
        size=size,
        settings=settings,
        scene=d.Scene(
            environment=d.Studio(),
            nodes=(
                d.Mesh(
                    geometry=d.Box(radius=0.08),
                    material=d.Material(color="#3288ff", metalness=0.65, roughness=0.22),
                    rotation=(
                        0.25,
                        fframes.Tween(from_value=0, to_value=tau, duration=DURATION),
                        0,
                    ),
                ),
            ),
        ),
        camera=d.Camera(position=(0, 0, 3.6)),
    )


def monitor(screen: d.Texture, size: tuple[int, int], settings: d.RenderSettings) -> d.Renderer:
    """Put the animated 2D display inside a lit 3D monitor above a reflective floor."""
    housing = d.Material(color="#28303a", metalness=0.8, roughness=0.28)
    return d.Renderer(
        size=size,
        settings=settings,
        camera=d.Camera(
            target=(0, 0.5, 0),
            orbit=d.Orbit(
                distance=5,
                azimuth=fframes.Tween(from_value=-22, to_value=22, duration=DURATION),
                elevation=12,
            ),
        ),
        scene=d.Scene(
            background="#10151e",
            environment=d.Studio(),
            reflector=d.Reflector(scale=0.5),
            nodes=(
                d.Mesh(
                    geometry=d.Box(size=(2.3, 1.4, 0.16), radius=0.07),
                    position=(0, 0.9, 0),
                    material=housing,
                ),
                d.Mesh(
                    geometry=d.Plane(size=(2.16, 1.215)),
                    position=(0, 0.9, 0.081),
                    material=d.Material(shading="unlit", map=screen),
                ),
                d.Mesh(
                    geometry=d.Box(size=(0.14, 0.32, 0.12)),
                    position=(0, 0.16, 0),
                    material=housing,
                ),
                d.Mesh(
                    geometry=d.Box(size=(0.85, 0.06, 0.4), radius=0.025),
                    position=(0, 0.03, 0),
                    material=housing,
                ),
                d.Mesh(
                    geometry=d.Plane(axis="xz", size=(12, 12)),
                    material=d.Material(color="#151e2c", reflection=0.35),
                ),
                d.Light(
                    light=d.DirectionalLight(
                        direction=(-1, -2, -1), intensity=2, shadow=d.Shadow(map_size=256)
                    )
                ),
            ),
        ),
    )


def export(video: fframes.SvgVideo | CompiledVideo, api: str) -> None:
    """Write previews and an MP4 under the ignored output directory."""
    folder = Path("output") / api
    folder.mkdir(parents=True, exist_ok=True)
    native = video if isinstance(video, fframes.SvgVideo) else video.native
    fframes.contact_sheet(native, folder / "three_d.png", frames=(0, 30, 60, 89), columns=2)
    options = fframes.RenderOptions(concurrency=2)
    if isinstance(video, fframes.SvgVideo):
        fframes.render(video, folder / "three_d.mp4", options=options)
    else:
        video.render(folder / "three_d.mp4", options=options)
