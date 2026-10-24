# fframes-py

Create videos in Python; Rust handles rendering and encoding. Supports
Python 3.11–3.14. Start with [installation](installation.md), then [compose](compose.md).

## Choose an API

| Import | Use it for |
| --- | --- |
| `fframes.compose` | Reusable graphics, local animation and audio without writing SVG. |
| `fframes` | Compile SVG frames or scalar keyframes; cache them with `Video` or `Timeline`. |

`fframes.Video` and `fframes.compose.Video` accept different inputs. Import from
the namespace you intend to use. `fframes._native` and `compose.compiler` are internal.

## Guides

| Topic | What it answers |
| --- | --- |
| [Installation](installation.md) | Install the package and check runtime requirements. |
| [Compose](compose.md) | First video and the model validation rules. |
| [Layers and timing](layers.md) | Drawing order, local coordinates, clips and tweens. |
| [Graphics](graphics.md) | Text, shapes, paths, images and paint. |
| [Components](components.md) | Define typed, reusable building blocks. |
| [Shaders](shaders.md) | SkSL, Shadertoy and typed uniforms in both APIs. |
| [3D scenes](three-d.md) | Geometry, lights, cameras and CPU/GPU rendering. |
| [3D assets](three-d-assets.md) | glTF, rigs, morph targets and nested render textures. |
| [Lottie](lottie.md) | Vector animation playback and supported content. |
| [Masks and filters](filters.md) | Clip layers and build reusable filter graphs. |
| [In-memory media](buffers.md) | PCM slices, encoded images and RGBA frame buffers. |
| [Named timelines](timing.md) | Scene reports and frame/time selectors. |
| [Audio](audio.md) | Place, trim, loop and mix sound. |
| [Analysis and subtitles](analysis.md) | Mix reports, FFT, NumPy views and WebVTT cues. |
| [Rendering](rendering.md) | Resolution, fonts, compilation, previews and encoder settings. |
| [Inspection](inspection.md) | Named layers, crops, contact sheets and continuity checks. |
| [Codec licenses](codecs.md) | Third-party licenses and redistribution conditions. |
| [Low level](lowlevel.md) | SVG rendering and scalar animation signatures. |
| [Upstream examples](examples.md) | Paired ports, asset cache and feature parity status. |
| [Upstream audit](upstream.md) | Engine capability map, adaptations and platform verification. |
| [Development](development.md) | Rebuild, check and package the bindings. |
| [Releases](releases.md) | Versioning, PyPI setup and publishing tested distributions. |

Current scope: finite, in-memory scenes rendered with CPU or Skia backends.
Both APIs support synchronized video files. HTML/CSS layout and streaming
authoring are not exposed.
