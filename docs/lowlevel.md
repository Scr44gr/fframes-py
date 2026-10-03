# Low-level SVG and scalar animation

[Index](index.md)

Use `fframes.lowlevel` when SVG frames already exist or you need sampled numeric
keyframes. The public functions validate inputs and return reusable native
objects. Use [compose](compose.md) for typed graphics and audio authoring.

## SVG video

```python
from pathlib import Path

from fframes import RenderOptions, VideoConfig, lowlevel

svg = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
    '<rect width="64" height="64" fill="#3776AB"/></svg>'
)
config = VideoConfig(width=64, height=64, fps=30)
native = lowlevel.compile_video(config, (svg,) * 30)
output = Path("output")
output.mkdir(exist_ok=True)
native.save_png(0, output / "raw.png")
lowlevel.render(native, output / "raw.mp4", RenderOptions(concurrency=2))
```

`frames` is a nonempty tuple of complete SVG strings, one per frame. Match SVG
dimensions to the output configuration. `VideoConfig` defaults to width 1920,
height 1080, fps 30, and `load_system_fonts=False`; enable it for system-font text.
The sequence is owned in memory; rendering is not a streaming callback interface.
SVG syntax is parsed when frames render, so compilation alone does not validate
every SVG document. SVG support follows the native renderer, not a web browser.
This API skips `<image>` references, including remote URLs. Use compose `Image`
items for local raster assets.

| Operation | Result |
| --- | --- |
| `len(native)` | Number of SVG frames; duration is this value divided by fps. |
| `native.rgba(index)` | Straight-alpha RGBA8 bytes for one zero-based frame index. |
| `native.save_png(index, Path(...))` | Write a PNG; returns `None`. Note the argument order. |
| `lowlevel.render(native, path, options=None)` | Encode silent video; return the destination `Path`. |

Prefer `lowlevel.render` over calling `native.render` directly: it manages the
temporary directory. [Encoding constraints](rendering.md#encoding) apply, but
raw render options expose no bitrate or audio settings.

## Scalar animation

```python
from fframes import Keyframe, lowlevel

keyframes = (
    Keyframe(start=1, end=2, from_value=10, to_value=20, easing="ease_in_out"),
    Keyframe(start=3, end=4, from_value=20, to_value=0),
)
animation = lowlevel.compile_animation(keyframes)
values = animation.sample_many((0, 45, 75, 105, 150), 30)
```

Keyframes use nonnegative seconds with `end > start`, finite values, ordered
non-overlapping intervals. Easing accepts `linear`, `ease_in`, `ease_out` and
`ease_in_out`. Sampling uses a nonnegative frame index and a positive integer fps.
Values hold before the first interval, in gaps and after the last interval.
Upstream keyframe timestamps use float32, so very large, closely spaced times may
be rejected when they collapse to the same native timestamp.

Use `sample(index, fps)` for one value and `sample_many(indices, fps)` for batches.
Batch sampling releases the GIL and avoids repeated Python/native calls. This
animation is not a composition timeline and cannot hold visual or audio layers.

## Convenience wrappers

`fframes.Timeline(keyframes=...)` caches its native animation; `sample` and
`sample_many` accept keyword-only `fps=30`. `fframes.Video(config=..., frames=...)`
caches its native SVG video and adds `duration`, `rgba(index=0)`,
`save_png(path, index=0)` and `render(path, options=...)`. Both expose `.native`.
The [motion example](../examples/motion.py) demonstrates these wrappers.
