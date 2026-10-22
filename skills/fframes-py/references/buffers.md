# Binary media and scene queries

Use `Pcm`, `ImageBuffer` or `VideoFrames` as typed sources. Pass immutable `bytes`;
use NumPy `tobytes()` for an explicit snapshot of a mutable array.

- `Pcm(data=..., sample_rate=48000, channels=2)` accepts interleaved float32
  little-endian. `slice(start, end)` shares storage and selects relative sample
  frames, end exclusive. Tracks and `AudioData` accept it.
- `ImageBuffer(data=...)` decodes encoded images; `size=(w, h)` instead means
  exactly `w*h*4` straight RGBA8 bytes. Bindings, uniforms and textures accept it.
- `VideoFrames(data=..., size=(w, h), fps=30)` holds contiguous straight RGBA8
  frames. Clip, shader and texture timing follows the existing source-clock rules.

Compile through the public Video/Renderer API; binary payloads travel outside
JSON. PCM deinterleaving and pixel conversion create native storage, so input
compilation is not zero-copy. Reuse compiled objects. Output `bytes` can be viewed
with `np.frombuffer`; copy only when writable data is required.

Name compose groups with `Composition(name=...)`; inspect `compiled.timeline`.
For SVG, supply `Video(chapters=(SceneRange(name=..., frames=(start, end)), ...))`.
`resolve_frame("Intro@0.5s")`, `resolve_range("Intro")` and `scenes_at(frame)`
use original frame indices. `Intro[1]` disambiguates a reused name; overlaps and
nested clipping remain in the report. `resolve_range("1s..2s")` returns an
end-exclusive pair suitable for `RenderOptions.frame_range`.
