# Upstream compatibility

[Index](index.md)

The engine is pinned to **fframes 1.3.0**, released on 2026-10-20, commit
[`69174f0187b5`](https://github.com/dmtrKovalenko/fframes/tree/69174f0187b5d8e92329246898f70250b59f08f2).
This audit compares its published crates, source and authoring references with
[1.2.0](https://github.com/dmtrKovalenko/fframes/compare/v1.2.0...v1.3.0).

## New capabilities

| Upstream change | Python entry point / verification |
| --- | --- |
| 3D geometry, PBR, lights, environment, shadows, reflection, fog | [`three_d`](three-d.md); real pixel, occlusion and lighting tests. |
| glTF/GLB, STL, text extrusion, skinning, morphs, animation, instances, particles | [Assets and animation](three-d-assets.md); imported fixtures, deformation and random-access pose tests. |
| GPU 3D, MSAA, bloom, depth of field, motion blur | `RenderSettings`, `Focus`; CPU effect tests and opt-in real GPU comparison. |
| SVG ↔ 3D textures | `SvgTexture`, `SceneTexture`, `compose.Video.texture()`; nested scenes and animated texture tests. |
| Lottie | [`Lottie`, `LottieBinding`, `compose.LottieLayer`](lottie.md); playback boundaries, looping and texture tests. |
| Eight per-track audio processors, rate and fade curves | [`effects`, `AudioTrack`, `compose.Audio`](audio.md); frequency response, effect order, stereo and timing tests. |
| BT.601 / BT.709 output | `RenderOptions.color_matrix`; CPU/Skia decoded pixels and `ffprobe` stream tags. |
| Parallel inspection, crops, labels, sheets, onion skins and pop detection | [Inspection](inspection.md); both APIs, frame order, bounds and transition tests. |

Primitive constructors are consolidated: `Cylinder(top=0)` makes a cone,
`Ring(inner=0)` a disk, `Plane(axis="xz")` a floor, and `Box(radius=...)` a rounded
box. A smaller `Renderer.size` with a larger SVG/compose placement replaces
upstream's redundant `scaled` constructor. Scene recipes evaluate in Rust;
they do not accept a Python callback per frame.

## Inherited engine changes

The pinned dependencies include the closed-form cubic Bézier solver, SVG ID and
numeric font-weight fixes, `svgr/usvgr` 0.50.2 and the `lru` 0.18.5 security fix.
Media decoding now respects input color metadata, handles MKV/WebM container
duration, sizes resized buffers correctly and discards failed conversions.
Texture tests exercise resized decoding, seeking and looping.

Encoder scheduling, GOP alignment, unfinished-segment cleanup, MP4 remuxing,
NEON color conversion and Vulkan resource lifetime fixes come from upstream.
The wrapper uses those implementations; it does not duplicate them or promise
a speedup without measurement. Existing codec tests exercise multi-segment output.

## Boundaries

- Vulkan can share 3D and SVG textures internally. Rust `wgpu` device/queue handles
  and borrowed GPU textures are not public Python objects. Metal composition
  currently reads back 3D pixels; do not assume end-to-end zero-copy encoding.
- Lottie and glTF have upstream format limitations, listed in their guides.
  GPU scene limits are explicit in [3D scenes](three-d.md#devices-and-ownership).
- MP4 is the tested delivery container. Direct MKV export can report an incorrect
  frame rate/duration in this upstream version. Correctly timed MKV input loops
  correctly; remux a verified MP4 when MKV delivery is required.
- Source video sampling follows upstream's first decoded timestamp at or after
  the requested time. Changing frame rate can therefore select the next source
  frame. The video timeline uses integer fps.
- Upstream's desktop player, WASM editor, Rust scaffolding CLI, landing pages and
  release infrastructure are separate applications, not wrapper APIs. Their new
  inspection operations are exposed as Python functions above.

The [existing example ports](examples.md) retain their 1.2.0 asset pin. Upstream
1.3.0 adds `arm`, `svg-in-3d`, `lottie-launch`, `shader-mode` and `made-of-motion`.
The new reusable rendering features are bound; those five complete films are
not claimed as Python ports. The new self-contained examples demonstrate nested
3D textures through both Python APIs without downloading media; the Lottie guide
shows playback of an existing JSON file.

## Platform verification

CI builds one stable-ABI wheel for Linux x86-64, Windows x86-64 and macOS arm64,
then tests it on Python 3.11–3.14. The 3D CPU tests run in every matrix job.
Set `FFRAMES_TEST_3D_GPU=1` on a host with a working driver for the GPU comparison;
hosted CI passing CPU tests does not establish GPU parity.

Local 1.3.0 checks include Windows CPU, Skia CPU and Vulkan. Cross-platform status
must be taken from the CI run for the exact wrapper commit, not the upstream
release or a previous wrapper build. Python coverage does not measure native
Rust/FFmpeg coverage.
