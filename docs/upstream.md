# Upstream compatibility

[Index](index.md)

Audited on **2026-10-22** against the latest published engine, **fframes 1.3.0**,
commit [`69174f0187b5`](https://github.com/dmtrKovalenko/fframes/tree/69174f0187b5d8e92329246898f70250b59f08f2).
The wrapper pins this version. Upstream `main` at
[`654ae86`](https://github.com/dmtrKovalenko/fframes/tree/654ae86ffdff31202940d8cf05cdcdc30efe6228)
adds example/documentation changes; it contains no newer engine changes.

This is a capability map, **not a claim of complete API or platform parity**.
The comparison covers the published crates and upstream's API, 3D and audio
references. Python APIs share native implementations; Rust builder aliases and
language-specific helpers are consolidated rather than copied verbatim.

## Available

| Capability | Python entry points | Verification |
| --- | --- | --- |
| SVG, scalar/color easing, text metrics | `Video`, `Timeline`, `TextLayout`; [low level](lowlevel.md) | Animation, text layout and SVG pixel tests. |
| Composable layers, timing, graphics and effects | [Compose](compose.md), [graphics](graphics.md), [filters](filters.md) | Pixels, local clocks, nesting, masks and invalid inputs. |
| SkSL/Shadertoy, images and synchronized clips | [Shaders](shaders.md), `ImageBinding`, `VideoBinding`, `compose.VideoClip` | Shader compilation, sampled uniforms, seeking, loops and EOF. |
| Track mixing, ducking, eight audio processors, FFT and WebVTT | [Audio](audio.md), [analysis](analysis.md) | Samples, channel separation, frequency response, effect order and cues. |
| 3D geometry, PBR, cameras, lights, environment, shadows, fog and reflection | [`three_d`](three-d.md), `SceneBinding`, `compose.Scene3D` | Real pixels, occlusion, projection and lighting. |
| glTF/GLB, STL, text extrusion, skins, morphs, instances and particles | [3D assets](three-d-assets.md) | Imported fixtures, deformation and random-access animation. |
| Nested SVG/compose/3D textures and Lottie | `SvgTexture`, `SceneTexture`, `Video.texture()`, [Lottie](lottie.md) | Nested rendering, playback clocks and texture pixels. |
| CPU/GPU 3D, MSAA, bloom, depth of field and motion blur | `RenderSettings`, `Focus` | CPU effects; opt-in GPU comparisons. |
| Frame diagnostics, crops, labels, sheets, onion skins and pop detection | [Inspection](inspection.md) | Both APIs, frame ordering, bounds and transitions. |
| Encoding, BT.601/709 and frame-range export | [RenderOptions](rendering.md#encoding) | `ffprobe`, full decoding, color values, audio synchronization and failure cleanup. |

The dependency also supplies the 1.3.0 decoding, scheduler, remuxing, Bézier,
font-weight and resource-lifetime fixes. See the
[upstream release](https://github.com/dmtrKovalenko/fframes/releases/tag/v1.3.0)
for its change log; the wrapper does not reimplement those fixes.

## Remaining wrapper gaps

| Upstream surface | Current boundary |
| --- | --- |
| `AudioMixOptions`, `LimiterOptions` | Master gain, limiter configuration and de-click control use native defaults; only per-track controls are public. |
| Loudness/audio reports | No Python binding for LUFS, true peak, clipping/silence reports, waveform reports or active-track inspection. FFT is available. |
| In-memory media providers | No raw PCM source/slicing API or general image/video buffer provider. Sources use files; `PixelTexture` separately accepts owned 3D texture pixels. |
| `AbortSignal` and rendering logger | No public cancellation signal or progress reporting API. |
| Advanced `EncoderOptions` | No codec parameter dictionary, GOP/quantizer controls, selectable audio encoder/rate, or general output pixel/sample formats. Available video encoder names can be selected. |
| Export overrides | No render-time fps or resolution scaling option. Set fps when authoring; compose scaling and resized PNG previews are separate operations. |
| Named timeline queries | No `TimelineIndex`/`TimeSpec` scene selectors or automatic scene report. Compose uses explicit numeric placement; `Timeline` is scalar animation. |
| Mutable 3D editing | Recipes expose supported animated properties, not arbitrary per-frame mutation, model material overrides or topology changes. Recompile changed descriptions. |
| General SVG filters/masks in compose | Compose exposes the steps in its filter guide and a rounded rectangular mask; other SVG constructs require the low-level API and renderer support. |

These are missing Python interfaces, not limitations of upstream's Rust API.

## Adaptations and engine limits

- `Cylinder(top=0)` is a cone, `Ring(inner=0)` a disk, `Plane(axis="xz")` a floor,
  and `Box(radius=...)` a rounded box. Geometry transforms and `text_shapes`
  replace redundant constructor variants. Use `PixelTexture` for precomputed
  procedural pixels; rendering never invokes Python callbacks.
- Rust GPU handles and borrowed textures are not public Python objects. Vulkan
  can share nested GPU textures internally; Metal composition reads back 3D
  pixels. This does not establish zero-copy encoding.
- [3D assets](three-d-assets.md) and [Lottie](lottie.md) list their upstream format
  limitations. [3D scenes](three-d.md) covers GPU limits and antialiasing.
- MP4 is the tested delivery container. Direct MKV export can have incorrect
  frame-rate/duration metadata in this engine version; remux a verified MP4.
- Video sampling selects the first source timestamp at or after the requested
  time; [clip timing](graphics.md#video-clips) explains unequal frame rates.
- The desktop player, WASM editor, Rust CLI/scaffolding and websites are separate
  applications, not Python bindings. Static previews do not provide a live player.

[Example ports](examples.md) record their own asset revision and unported films.
Porting a film does not verify every engine feature.

## Verification scope

CI is configured to build one stable-ABI wheel for Linux x86-64, Windows x86-64
and macOS arm64, then test each on Python 3.11–3.14. CPU tests run in that matrix.
`FFRAMES_TEST_3D_GPU=1` enables real GPU comparisons on a host with a driver;
hosted CPU tests cannot establish GPU parity.

Local evidence covers Windows CPU, Skia CPU and Vulkan. Linux/macOS status must
come from CI for the exact wrapper commit. Python coverage does not measure
native Rust/FFmpeg coverage; passing tests do not prove every asset or backend
renders identically.
