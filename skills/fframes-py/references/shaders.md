# Shaders and effects

Set `Video(backend="skia")` for Skia CPU, `"vulkan"` on Windows/Linux or `"metal"`
on macOS. The default `"cpu"` backend cannot draw shaders. GPU rendering requires a
working driver; GPU readback and encoding are not automatically zero-copy.

Use `fframes.Shader(source=..., language="sksl", uniforms=(...))`. Shadertoy GLSL
with `mainImage` uses `language="shadertoy"`. Compilation checks source and bindings.
Do not infer that arbitrary GLSL or every SVG feature is supported.

| Binding from `fframes` | Value |
| --- | --- |
| `FloatUniform(name=..., value=...)` | Float, `Tween` or `Samples`. |
| `ColorUniform(name=..., value=...)` | Hex RGBA, `ColorTween` or `ColorSamples`. |
| `VectorUniform(name=..., value=(...))` | 2–4 scalar values, including animations. |
| `IntUniform(name=..., value=...)` | int32. |
| `ImageUniform(name=..., source=path)` | Local raster; binds `uniform shader`. |
| `VideoUniform(name=..., source=path, offset=0, loop=False)` | Local clip on the shader clock; no implicit audio. |

Names must match declarations. Declare any built-ins used by SkSL (`iTime`,
`iTimeDelta`, `iFrame`, `iResolution`) in the source; the renderer supplies their
values, so do not add uniform bindings for them. Missing values follow
upstream zero/transparent defaults. Source files are read at authoring time;
image uniforms are decoded once when compiling the video.

For compose, use `ShaderLayer(shader=program, size=(w, h))` with ordinary visual
placement. Its clock restarts at the first visible frame of each occurrence.
For SVG, bind `ShaderBinding(name="effect", shader=program)` through the `shaders`
argument of `compile_video` or `Video`, and reference `href="shader:effect"`.
Bindings accept `start_at` and `duration`; their first visible frame starts the
local clock. `Shader.time_offset` advances built-ins, animated uniforms and video
children together, rounded down to the output frame grid. These names do not fetch URLs.
`ShaderLayer.size` can animate; it controls `iResolution`.

Compose effects attach to any visual or group:

- `Mask(size=(w, h), radius=..., position=(x, y))` clips local layout coordinates;
  all geometry accepts scalar animations.
- `Filter(steps=(...), region=(x, y, w, h))` describes an ordered graph. Region is
  relative to object bounds; enlarge it for blur halos.
  Use `units="user"` for local pixels and `color_space="srgb"` when required.
- Steps are `Blur(result=..., source=..., sigma=(x, y))`, `Flood(result=..., color=...)`,
  `Composite(result=..., source=..., destination=..., operator="in")`, and
  `Merge(result=..., sources=(...))`. Inputs are prior results or
  `SourceGraphic`/`SourceAlpha`; result names are unique. Mask clips the final filter.
- `Offset(result=..., source=..., dx=..., dy=...)` translates an input.
  `ColorMatrix(result=..., source=..., values=(row1, row2, row3, row4))` transforms
  RGBA; each row has five coefficients, including the offset column.

Minimal animated shader:

```python
from fframes import Shader
from fframes.compose import Composition, ShaderLayer, Video

program = Shader(
    source="""
    uniform float iTime;
    half4 main(float2 position) {
        return half4(0.5 + 0.5 * sin(iTime), 0.3, 0.7, 1.0);
    }
"""
)
scene = Video(
    backend="skia",
    resolution=(320, 180),
    composition=Composition(
        duration=2,
        children=(ShaderLayer(shader=program, size=(320, 180)),),
    ),
).compile()
scene.save_png("shader.png", index=30)
```
