# 3D scenes

[Index](index.md) · [Assets and animation](three-d-assets.md)

`fframes.three_d` describes geometry, materials, lights and cameras. The same
native renderer works in SVG bindings and `compose.Scene3D`.

```python
from math import tau
from fframes import Tween, compose, three_d as d

scene = d.Renderer(
    size=(640, 360),
    scene=d.Scene(
        environment=d.Studio(),
        nodes=(
            d.Mesh(
                name="cube",
                geometry=d.Box(radius=0.08),
                material=d.Material(color="#3288ff", metalness=0.6, roughness=0.25),
                rotation=(0.2, Tween(from_value=0, to_value=tau, duration=3), 0),
            ),
        ),
    ),
    camera=d.Camera(orbit=d.Orbit(distance=4, elevation=15)),
)
video = compose.Video(
    resolution=(640, 360),
    composition=compose.Composition(duration=3, children=(compose.Scene3D(renderer=scene),)),
)
video.render("cube.mp4")
```

For SVG, reuse `scene` with a named binding:

```python
import fframes

video = fframes.Video(
    config=fframes.VideoConfig(width=640, height=360, fps=30),
    frames=(
        '<svg width="640" height="360"><image href="scene:cube" width="640" height="360"/></svg>',
    )
    * 90,
    scenes=(d.SceneBinding(name="cube", renderer=scene),),
)
```

## Coordinates and timing

- Y points up; the default camera looks from `(0, 0, 5)` toward the origin.
  Geometry dimensions and positions use world units, not pixels.
- Euler XYZ rotations and camera roll use **radians**. Camera `fov` and
  `Orbit.azimuth/elevation` use **degrees**. Matrices are column-major, affine
  and invertible; quaternions use `(x, y, z, w)`.
  `fov` stays within 0.001–179.999 degrees to avoid a singular projection.
- Groups provide pivots and inherited visibility. Node names must be unique.
  `VisibilityFrames` animates visibility without Python callbacks.
- A `Scene3D.at(...)` or `SceneBinding(start_at=...)` starts a local scene clock.
  Embedded 3D inherits the output fps for video decoding and motion blur;
  `Renderer.fps` controls standalone previews. Explicit `Samples.fps` stays its own clock.
- `renderer.rgba(time)` takes **seconds**. `video.rgba(index)` takes **frames**.
  `world_position`, `world_matrix`, `local_to_world`, `project`, `bounds` and
  `pixel_size` evaluate the requested pose. Bounds use undeformed geometry;
  projection returns `None` behind the camera.

## Build the scene

| Need | Types/settings |
| --- | --- |
| Solids | `Box`, `Sphere`, `Cylinder`, `Capsule`, `Torus`, `Icosahedron` |
| Surfaces and paths | `Plane`, `Ring`, `Lathe`, `Tube`, `Extrude(Shape(...))` |
| Imported/custom geometry | `TextGeometry`, `STL`, `MeshGeometry`, `Merged` |
| Surface appearance | `Material`: standard PBR, unlit, normals or shadow catcher |
| Lighting | `AmbientLight`, `HemisphereLight`, `DirectionalLight`, `PointLight`, `SpotLight` inside `Light` nodes |
| Environment | `Studio` softboxes or `EnvironmentMap`; `EnvironmentBackground` displays it |
| Atmosphere/reflection | `LinearFog`, `ExponentialFog`, one `Reflector` per scene |
| Repetition/effects | `Instances` sharing geometry, `Particles`, `Bloom`, camera `Focus` |

Hex colors are sRGB. RGB tuples are linear intensities and may exceed 1 for HDR.
Use `Material.opacity` for alpha. Material maps cover color, emission, normal,
metalness/roughness and ambient occlusion; the geometry needs UV coordinates.
STL has no UVs. `normal_scale`, clearcoat, side, additive blending, depth writes,
fog participation and shadow participation are explicit material/mesh settings.

Directional lights accept `Shadow`; point and spot shadows are unavailable upstream.
`Focus(distance=...)` uses camera depth; `Focus(point=...)` follows a world point
and uses upstream's minimum focus depth of 0.05 units. `RenderSettings` controls
exposure, ACES/neutral/linear tone mapping, bloom, 4× MSAA and motion sampling.
`motion_samples > 1` samples a centered shutter interval; `shutter` is a fraction
of one output frame. More samples repeat scene rendering.

## Devices and ownership

`RenderSettings.device` is `"auto"`, `"cpu"` or `"gpu"`, independently of the
outer SVG backend. `renderer.uses_gpu` reports the actual selection. Forced GPU
fails if unavailable or if the scene exceeds upstream's GPU limits: 16 direct
lights, 2 directional shadow lights and 8 studio softboxes. `auto` uses CPU for
these oversized scenes.

Both paths support the scene features above. They can differ at edge pixels;
use tolerances for image comparisons. CPU tests run on every wheel platform;
GPU parity requires the relevant driver. See the [upstream audit](upstream.md).

Compilation transfers owned descriptions. Identical geometry recipes share native
allocations; frames reuse geometry and image buffers. Python is not called during
scene evaluation. `rgba()` returns an owned copy; NumPy can view it with
`frombuffer`. Vulkan can keep nested render textures on the shared GPU device.
CPU SVG and Metal composition read 3D pixels back; GPU rendering alone does not
establish zero-copy encoding.
