# Low-level operations

Use this path for existing SVG frame sequences or sampled scalar animation.
Use `import fframes`; its root exports the input models and compilation functions.
Keep it separate from compose; neither API's native video is an item in the other.

## SVG frames

1. Build a nonempty **tuple** of complete SVG strings, one string per frame.
   Match SVG and output dimensions. Escape dynamic text/attributes when authoring
   XML, or choose compose when no SVG input exists.
2. Set `fframes.VideoConfig(width=w, height=h, fps=n, fonts=(font_path,),
   load_system_fonts=False)` for reproducible text. Explicit font bytes are owned
   after compilation. Enable system fonts only when host-dependent faces are intended.
3. Call `native = fframes.compile_video(config, frames)` once. It owns the
   sequence; malformed SVG can still fail later when rasterized.
   Ordinary `<image>` references, including URLs, are skipped; registered
   `shader:` references use the [shader bindings](shaders.md). Use compose
   `Image` for local raster assets.
4. Preview with `native.rgba(index)` or `native.save_png(index, Path(...))`.
   Unlike compose, native `save_png` takes the index first and returns `None`.
5. Encode with `fframes.render(native, path, fframes.RenderOptions(concurrency=...))`.
   This public helper manages temporary files and returns a `Path`.

The result is silent; no Python callback runs during rendering. All SVG strings
are held in memory. `len(native) / config.fps` gives duration. Do not call
`native.render` directly unless deliberately managing its extra temporary-directory
argument. Even dimensions and codec/container rules from the media reference apply.
`RenderOptions` is shared with compose, including its bitrate setting.

## Scalar keyframes

Pass an ordered, nonempty tuple of
`fframes.Keyframe(start=..., end=..., from_value=..., to_value=..., easing="linear")`
to `fframes.compile_animation(...)`. Times are seconds, nonnegative,
non-overlapping and `end > start`; values are finite. Available easing curves are
`linear`, `ease_in`, `ease_out`, `ease_in_out`, `Spring(...)` and
`CubicBezier(x1=..., y1=..., x2=..., y2=...)`.

Prefer `animation.sample_many(indices, fps)` for batches; use
`animation.sample(index, fps)` for one frame. Both native methods take fps
positionally; indices are nonnegative. Values hold outside intervals and in gaps.
Native timestamps are float32; avoid huge absolute clocks with tiny intervals.

For color interpolation use `ColorKeyframe` with six/eight-digit hex strings and
`compile_color_animation`. Sampling returns `#RRGGBBAA` using upstream channel
rounding; do not reconstruct colors from independently rounded scalar samples.

`fframes.Timeline(keyframes=...)` is a cached scalar wrapper, not a scene timeline.
Its sample methods accept keyword-only `fps=30`. `fframes.Video(config=..., frames=...)`
is the cached SVG wrapper; it exposes `save_png(path, index=0)`, `rgba(index=0)` and
`render(path, options=...)`. Neither is `fframes.compose.Video`.
