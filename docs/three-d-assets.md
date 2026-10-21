# 3D assets and animation

[3D scenes](three-d.md)

## Models

```python
from fframes import three_d as d

info = d.probe_model("robot.glb")
print(info.nodes, info.animations)
robot = d.Model3D(
    name="robot",
    source="robot.glb",
    animations=(d.Playback(name="Walk", loop=True, speed=1.2),),
)
```

glTF/GLB imports meshes, PBR materials, textures, hierarchy, skinning, morph targets
and animation clips. External buffers/images must remain within the model's
directory. Missing resources fail compilation; URLs are not fetched implicitly.
Imported names are addressed as `robot/node_name`; ambiguous names fail.

Playback uses `time * speed + offset`, or an explicit animated `time` value.
`weight` blends clips in their declared order. `poses=(Pose(name=..., ...),)`
replaces a model node's complete transform after animation; unspecified pose
fields use their defaults.

For authored rigs, use `Animation` with `Translation`, `Rotation`, `Scaling` or
`MorphWeights` channels. Times increase strictly; `linear` rotations use slerp.
`step` holds values; `cubic_spline` requires **in tangent, value, out tangent**
for every keyframe, following glTF. Clip duration includes its final keyframe.
`Skin` references scene joints and inverse bind matrices; `SkinWeights` provides
four joint indices/normalized weights per vertex. Morph deltas match vertex count.
Instancing is rigid: do not combine it with skinning or morphing.

Upstream import does not reproduce glTF cameras, nonzero UV sets, texture
transform extensions or every advanced material extension. Its alpha-mask import
uses blending rather than alpha-cutoff testing. Set the camera and supported
materials explicitly when those distinctions matter.

## Text and geometry

`TextGeometry` extrudes a whole string. `text_shapes(font, text, size=...)` returns
glyph-local polygons, holes, baseline origins and advances. Extrude those shapes
individually to animate letters. Font size is one em in scene units; upstream
outline extraction does not apply kerning. Whitespace has an advance but no shapes.

`MeshGeometry` takes indexed triangles and optional normals, UVs, colors, skin
weights and morph targets. Every supplied attribute must match vertex count.
Recipes are copied into owned native buffers during compilation; these tuples
are not NumPy views. Use `normals="flat"` or `"smooth"` to reconstruct normals.
`Plane(axis="xy")` maps the full image with normalized UVs and a top-left origin;
`axis="xz"` retains upstream floor UVs, repeating textures once per world unit.

## Textures

Wrap sources in `Texture(source=..., repeat=(1, 1), offset=(0, 0))`:

| Source | Behavior |
| --- | --- |
| `ImageTexture` | Decode once; `srgb=False` for normal/metalness/roughness data. |
| `PixelTexture` | Owned straight RGBA8 values, exactly `width * height * 4`. |
| `VideoTexture` | Synchronized file playback; `size` resizes before upload. |
| `SvgTexture` | SVG frames plus image, clip, shader, scene and Lottie bindings. |
| `LottieTexture` | A Lottie animation at an explicit texture resolution. |
| `SceneTexture` | A nested 3D renderer. |

Compose visuals can also become a texture:

```python
from fframes import compose, three_d as d

screen = compose.Video(
    resolution=(256, 256),
    composition=compose.Composition(duration=2, children=(
        compose.Circle(radius=80, fill="#3288ff"),
    )),
).texture()
panel = d.Mesh(geometry=d.Plane(size=(2, 2)), material=d.Material(shading="unlit", map=screen))
```

A composition texture holds its last frame after EOF. Its audio is rejected;
place sound on the outer timeline. SVG frames also hold their last image, while
their bindings continue on the texture clock. Texture shaders use the active
Skia renderer, with Skia CPU fallback when the enclosing SVG rasterizer is CPU.
Video files must remain available during rendering. Texture resolution controls
sharpness and memory independently of the outer video resolution.

`EnvironmentMap` accepts an HDR/image file or `EnvironmentPixels`: linear RGB
panorama values, exactly one per texel. Upstream prefilters environment panoramas
and reduces widths above 1024; ordinary material textures use mipmaps.
