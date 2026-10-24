# 3D scenes

Use `from fframes import three_d as d`. Construct immutable `d.Scene` nodes,
then a `d.Renderer(scene=..., camera=..., size=...)`. Place it with
`compose.Scene3D(renderer=...)`, or `d.SceneBinding(name=..., renderer=...)`
and `<image href="scene:name" .../>` in an SVG video.

```python
from fframes import Tween, compose, three_d as d

renderer = d.Renderer(
    size=(640, 360),
    scene=d.Scene(
        environment=d.Studio(),
        nodes=(
            d.Mesh(
                geometry=d.Box(radius=0.08),
                material=d.Material(color="#3288ff", metalness=0.6, roughness=0.25),
                rotation=(0.2, Tween(from_value=0, to_value=3.14, duration=2), 0),
            ),
        ),
    ),
    camera=d.Camera(orbit=d.Orbit(distance=4, elevation=15)),
)
video = compose.Video(
    resolution=(640, 360),
    composition=compose.Composition(
        duration=2,
        children=(compose.Scene3D(renderer=renderer),),
    ),
)
```

## Coordinates and motion

- World units, Y up; default camera `(0, 0, 5)` looks toward the origin.
  Euler XYZ rotations and roll use radians; FOV and orbit angles use degrees.
  FOV range: 0.001–179.999. Quaternions are `(x, y, z, w)`; matrices column-major.
- Group nodes establish pivots. Names are unique; query `world_position`,
  `world_matrix`, `local_to_world` or `project` for screen-aligned overlays.
  `bounds` describes undeformed geometry, not skinned/morphed extents.
- Node transforms and material scalars accept `Tween` or `Samples`. Zero scale
  is singular: use `VisibilityFrames` or opacity to hide geometry.
- `renderer.rgba(time)` takes seconds. A video's `rgba(index)` takes frames.
  Placed scenes start at local time zero; output fps controls embedded motion blur
  and clip decoding. Explicit sample fps is independent.

## Geometry and appearance

Use primitives (`Box`, `Sphere`, `Cylinder`, `Capsule`, `Torus`, `Plane`, `Ring`,
`Lathe`, `Tube`, `Icosahedron`), `Extrude(Shape(...))`, `TextGeometry`, `STL` or
indexed `MeshGeometry`. `Cylinder(top=0)` is a cone; `Plane(axis="xz")` a floor.
Use `text_shapes(font, text)` and glyph origins for independently animated letters.

PBR needs light: start with `Studio`, then add `Light(light=DirectionalLight(...))`.
Directional lights support `Shadow`; point/spot lights do not cast shadows.
Hex colors are sRGB; RGB tuples are linear HDR intensities. Use `opacity` for alpha.
`Bloom` needs bright highlights; `Focus(point=..., blur=...)`
can track a subject. A `Reflector` needs participating materials' `reflection`.

Use `Instances` for rigid copies and `Particles` for emissive sprites. Instancing
cannot deform through skinning/morphs. Custom vertex buffers are copied once into
native ownership; these typed tuples are not zero-copy NumPy inputs.

## Models and textures

Inspect `d.probe_model(path)` before choosing node or animation names. `Model3D`
loads glTF/GLB; external files stay inside its directory. Play a clip with
`Playback(name="Walk", loop=True)`; imported names are `model_name/node_name`.
`Pose` replaces the complete named transform after clips; omitted fields reset
to defaults. Authored `Animation` channels support step, linear and glTF cubic
splines (in tangent, value, out tangent). Skins need joint names, inverse bind
matrices and normalized four-weight vertex data.

`Texture(source=...)` accepts `ImageTexture`, `PixelTexture`, `VideoTexture`,
`SvgTexture`, `LottieTexture` or `SceneTexture`. `compose.Video.texture()` gives a
native animated texture without SVG strings; put audio on the outer timeline.
Composition textures hold their final frame. SVG frames hold too, but their media
bindings continue on the texture clock. Video assets must remain available.

Use `srgb=False` for image data maps and supply UVs. STL has no UV coordinates.
glTF import omits cameras, extra UV sets, texture-transform/advanced material
extensions; alpha masks blend rather than apply a cutoff. Do not promise exact
reproduction of those unsupported source features.

## Device choice

`RenderSettings(device="auto" | "cpu" | "gpu")` controls 3D independently of
the SVG backend. `uses_gpu` reports actual selection; forced GPU fails if absent.
GPU limits: 16 direct lights, 2 shadow lights, 8 softboxes; auto falls back to CPU.
Use smaller texture/renderer sizes for previews, retaining the final placement.
Vulkan can share nested GPU textures; Metal composition reads 3D pixels back.
`rgba()` always copies to owned Python bytes; NumPy can view those bytes.


`Model3D(materials=(MaterialOverride(node=..., material=...),))` replaces named
mesh materials, including animated properties; invalid targets fail. For topology
or hierarchy changes, pass `SceneFrames(frames=(Scene(...), ...), fps=...)` as
`Renderer.scene`. States compile once, hold the last state and use their own fps.
Animations inside them keep the renderer clock. Geometry/model data is shared;
prefer animated properties for continuous motion to avoid storing full scenes.
Named-node queries resolve against the selected state. No Python frame callbacks
or mutation of validated inputs is needed.
