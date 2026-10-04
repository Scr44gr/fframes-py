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
| `FloatUniform` | Float, `Tween` or `Samples`. |
| `ColorUniform` | Hex RGBA, `ColorTween` or `ColorSamples`, delivered as float4 in 0–1. |
| `VectorUniform` | Tuple of 2–4 floats, tweens or sample sequences. |
| `IntUniform` | Signed 32-bit integer. |
| `ImageUniform` | `source` pointing to a local raster file; binds `uniform shader`. |
| `VideoUniform` | Local video `source`, optional `offset` and `loop`; binds `uniform shader`. |

Each uniform has a unique `name` matching its declaration. The renderer supplies
`iResolution` (float3, element size), `iTime` (float seconds), `iTimeDelta` (float,
1/fps) and `iFrame` (int). These names cannot be overridden. Unset uniforms stay
zero; missing image children are transparent, following upstream behavior.

In compose, `ShaderLayer` uses its first visible frame as local frame zero. Timed
occurrences restart that clock. Its coordinates begin at the element's top-left,
and animated `size` controls `iResolution`. Position, opacity, transforms, masks and filters
work as for other graphics. `Shader.time_offset=0` advances its entire local clock,
including built-ins, animated uniforms and video children; it rounds down to the
output frame grid. Numeric and color uniforms animate in Rust. Image
uniforms load once and share their owned pixels throughout the compiled video.
Video uniforms share the clip decoder cache and follow the shader's local clock.
At EOF they supply a transparent image; `loop=True` repeats from `offset`.
Pixels stay in Rust; audio remains an explicit `Audio` or `AudioTrack`.

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

Bindings accept `start_at` and `duration`; the interval is half-open and its first
frame starts the shader clock at zero. Defaults cover the whole video.
The `shader:` name is a local lookup,
not a URL. Ordinary remote image references are still skipped. See the paired
[upstream examples](examples.md) for complete SkSL and Shadertoy scenes.
