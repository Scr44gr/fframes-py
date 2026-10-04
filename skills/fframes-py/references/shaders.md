# Shaders and effects

Set `Video(backend="skia")` for Skia CPU, `"vulkan"` on Windows/Linux or `"metal"`
on macOS. The default `"cpu"` backend cannot draw shaders. GPU rendering requires a
working driver; GPU readback and encoding are not automatically zero-copy.

Use `fframes.Shader(source=..., language="sksl", uniforms=(...))`. Shadertoy GLSL
with `mainImage` uses `language="shadertoy"`. Compilation checks source and bindings.
Do not infer that arbitrary GLSL or every SVG feature is supported.

| Binding from `fframes` | Value |
| --- | --- |
| `FloatUniform(name=..., value=...)` | Float or `Tween`. |
| `ColorUniform(name=..., value=...)` | Hex RGBA or `ColorTween`. |
| `VectorUniform(name=..., value=(...))` | 2–4 floats. |
| `IntUniform(name=..., value=...)` | int32. |
| `ImageUniform(name=..., source=path)` | Local raster; binds `uniform shader`. |

Names must match declarations. Built-ins `iTime`, `iTimeDelta`, `iFrame` and
`iResolution` are managed by the renderer; do not bind them. Missing values follow
upstream zero/transparent defaults. Source files are read at authoring time;
image uniforms are decoded once when compiling the video.

For compose, use `ShaderLayer(shader=program, size=(w, h))` with ordinary visual
placement. Its clock restarts at the first visible frame of each occurrence.
For SVG, bind `ShaderBinding(name="effect", shader=program)` through the `shaders`
argument of `compile_video` or `Video`, and reference `href="shader:effect"`.
SVG bindings follow the global video clock; these names do not fetch URLs.

Compose effects attach to any visual or group:

- `Mask(size=(w, h), radius=..., position=(x, y))` clips local layout coordinates.
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

In the checkout, `docs/shaders.md` and `docs/filters.md` contain runnable patterns;
the paired `shaders` and `neon_triangle` examples retain the upstream compositions.
