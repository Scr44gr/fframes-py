# Low-level SVG and animation

[Index](index.md)

Use `fframes` when SVG frames already exist or you need sampled numeric keyframes.
The public functions validate inputs and return reusable `fframes.SvgVideo` or
`fframes.Animation` objects. Use [compose](compose.md) for typed graphics and audio.

## SVG video

```python
from pathlib import Path

import fframes

svg = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
    '<rect width="64" height="64" fill="#3776AB"/></svg>'
)
config = fframes.VideoConfig(width=64, height=64, fps=30)
native = fframes.compile_video(config, (svg,) * 30)
output = Path("output")
output.mkdir(exist_ok=True)
native.save_png(0, output / "raw.png")
fframes.render(native, output / "raw.mp4", fframes.RenderOptions(concurrency=2))
```

`frames` is a nonempty tuple of complete SVG strings, one per frame. Match SVG
dimensions to the output configuration. `VideoConfig` defaults to width 1920,
height 1080, fps 30, and `load_system_fonts=False`. Supply `fonts=(Path(...), ...)`
for reproducible text or enable system fonts. Explicit font bytes are owned by
the compiled video; see [font configuration](rendering.md#fonts).
The sequence is owned in memory; rendering is not a streaming callback interface.
SVG syntax is parsed when frames render, so compilation alone does not validate
every SVG document. SVG support follows the native renderer, not a web browser.
Ordinary `<image>` references, including URLs, are skipped. Registered
`shader:` bindings render through Skia; see [shaders](shaders.md). Use compose
`Image` items for local raster assets.

| Operation | Result |
| --- | --- |
| `len(native)` | Number of SVG frames; duration is this value divided by fps. |
| `native.rgba(index)` | Straight-alpha RGBA8 bytes for one zero-based frame index. |
| `native.save_png(index, Path(...))` | Write a PNG; returns `None`. Note the argument order. |
| `fframes.render(native, path, options=None)` | Encode silent video; return the destination `Path`. |

Prefer `fframes.render` over calling `native.render` directly: it manages the
temporary directory. [Encoding constraints](rendering.md#encoding) apply. Both APIs share
`RenderOptions`; the raw SVG video remains silent.

## Scalar animation

```python
import fframes

keyframes = (
    fframes.Keyframe(start=1, end=2, from_value=10, to_value=20, easing="ease_in_out"),
    fframes.Keyframe(start=3, end=4, from_value=20, to_value=0),
)
animation = fframes.compile_animation(keyframes)
values = animation.sample_many((0, 45, 75, 105, 150), 30)
```

Keyframes use nonnegative seconds with `end > start`, finite values, ordered
non-overlapping intervals. Easing accepts `linear`, `ease_in`, `ease_out` and
`ease_in_out`, `Spring(...)` or `CubicBezier(x1=..., y1=..., x2=..., y2=...)`. Sampling uses a nonnegative frame index and a positive integer fps.
Values hold before the first interval, in gaps and after the last interval.
Upstream keyframe timestamps use float32, so very large, closely spaced times may
be rejected when they collapse to the same native timestamp.

Use `sample(index, fps)` for one value and `sample_many(indices, fps)` for batches.
Batch sampling releases the GIL and avoids repeated Python/native calls. This
animation is not a composition timeline and cannot hold visual or audio layers.
The [motion example](../examples/motion.py) combines batch sampling with SVG frames.

## Color animation

`compile_color_animation((ColorKeyframe(...), ...))` has the same interval and
sampling rules. Set `from_value` and `to_value` to `#RRGGBB` or `#RRGGBBAA`.
Its `ColorAnimation` returns `#RRGGBBAA` strings, using fframes' native RGBA
interpolation and rounding. Use it instead of rounding four scalar animations in
Python. The [hello-world port](../examples/native/hello_world.py) animates its
background this way.

## Convenience wrappers

`fframes.Timeline(keyframes=...)` caches its native animation; `sample` and
`sample_many` accept keyword-only `fps=30`. `fframes.Video(config=..., frames=...)`
caches its native SVG video and adds `duration`, `rgba(index=0)`,
`save_png(path, index=0)` and `render(path, options=...)`. Both expose `.native`.
