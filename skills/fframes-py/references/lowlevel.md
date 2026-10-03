# Low-level operations

Use this path for existing SVG frame sequences or sampled scalar animation.
Import `Keyframe`, `VideoConfig`, `RenderOptions`, and `lowlevel` from `fframes`.
Keep it separate from compose; neither API's native video is an item in the other.

## SVG frames

1. Build a nonempty **tuple** of complete SVG strings, one string per frame.
   Match SVG and output dimensions. Escape dynamic text/attributes when authoring
   XML, or choose compose when no SVG input exists.
2. Set `VideoConfig(width=w, height=h, fps=n, load_system_fonts=False)`; enable
   system fonts if the SVG contains text that requires them. This API has no
   explicit font-file parameter.
3. Call `native = lowlevel.compile_video(config, frames)` once. It owns the
   sequence; malformed SVG can still fail later when rasterized.
4. Preview with `native.rgba(index)` or `native.save_png(index, Path(...))`.
   Unlike compose, native `save_png` takes the index first and returns `None`.
5. Encode with `lowlevel.render(native, path, RenderOptions(concurrency=...))`.
   This public helper manages temporary files and returns a `Path`.

The result is silent; no Python callback runs during rendering. All SVG strings
are held in memory. `len(native) / config.fps` gives duration. Do not call
`native.render` directly unless deliberately managing its extra temporary-directory
argument. Even dimensions and codec/container rules from the media reference apply.
The raw `RenderOptions` has `encoder` and `concurrency`, with no bitrate field.

## Scalar keyframes

Pass an ordered, nonempty tuple of
`Keyframe(start=..., end=..., from_value=..., to_value=..., easing="linear")`
to `lowlevel.compile_animation(...)`. Times are seconds, nonnegative,
non-overlapping and `end > start`; values are finite. Available easing curves are
`linear`, `ease_in`, `ease_out`, `ease_in_out`.

Prefer `animation.sample_many(indices, fps)` for batches; use
`animation.sample(index, fps)` for one frame. Both native methods take fps
positionally; indices are nonnegative. Values hold outside intervals and in gaps.
Native timestamps are float32; avoid huge absolute clocks with tiny intervals.

`fframes.Timeline(keyframes=...)` is a cached scalar wrapper, not a scene timeline.
Its sample methods accept keyword-only `fps=30`. `fframes.Video(config=..., frames=...)`
is the cached SVG wrapper; it exposes `save_png(path, index=0)`, `rgba(index=0)` and
`render(path, options=...)`. Neither is `fframes.compose.Video`.
