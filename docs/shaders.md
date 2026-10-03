# Shaders

[Index](index.md)

Both APIs share `Shader` and its typed uniforms. Choose a
[Skia backend](rendering.md#backends); the default `cpu` renderer cannot run shaders.

```python
from fframes import ColorUniform, Shader
from fframes.compose import Composition, ShaderLayer, Video

program = Shader(
    source="uniform half4 tint; half4 main(float2 p) { return tint; }",
    uniforms=(ColorUniform(name="tint", value="#3776AB"),),
)
video = Video(
    backend="skia",
    resolution=(640, 360),
    composition=Composition(
        duration=2,
        children=(ShaderLayer(shader=program, size=(640, 360)),),
    ),
)
compiled = video.compile()
```

`language="sksl"` is the default. Use `language="shadertoy"` for a GLSL program
with `mainImage(out vec4 color, in vec2 position)`; fframes performs the conversion.
Shader syntax and supplied uniform types are checked at video compilation.

| Uniform | Value |
| --- | --- |
| `FloatUniform` | Float or `Tween`. |
| `ColorUniform` | Hex RGBA color or `ColorTween`, delivered as float4 in 0–1. |
| `VectorUniform` | Tuple of 2, 3 or 4 floats. |
| `IntUniform` | Signed 32-bit integer. |
| `ImageUniform` | `source` pointing to a local raster file; binds `uniform shader`. |

Each uniform has a unique `name` matching its declaration. The renderer supplies
`iResolution` (float3, element size), `iTime` (float seconds), `iTimeDelta` (float,
1/fps) and `iFrame` (int). These names cannot be overridden. Unset uniforms stay
zero; missing image children are transparent, following upstream behavior.

In compose, `ShaderLayer` uses its first visible frame as local frame zero. Timed
occurrences restart that clock. Its coordinates begin at the element's top-left,
and `size` controls `iResolution`. Position, opacity, transforms, masks and filters
work as for other graphics. Numeric and color uniforms animate in Rust. Image
uniforms load once and share their owned pixels throughout the compiled video.

## SVG binding

Use the same `program` with the low-level API:

```python
import fframes

svg = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360">'
    '<image href="shader:background" width="640" height="360"/></svg>'
)
native = fframes.compile_video(
    fframes.VideoConfig(width=640, height=360, backend="skia"),
    (svg,) * 60,
    shaders=(fframes.ShaderBinding(name="background", shader=program),),
)
```

Bindings use the video's global frame clock. The `shader:` name is a local lookup,
not a URL. Ordinary remote image references are still skipped. See the paired
[upstream examples](examples.md) for complete SkSL and Shadertoy scenes.
