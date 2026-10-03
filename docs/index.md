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
| [Installation](installation.md) | Native dependencies, uv setup, using a local checkout or wheel. |
| [Compose](compose.md) | First video and the model validation rules. |
| [Layers and timing](layers.md) | Drawing order, local coordinates, clips and tweens. |
| [Graphics](graphics.md) | Text, shapes, paths, images and paint. |
| [Components](components.md) | Define typed, reusable building blocks. |
| [Shaders](shaders.md) | SkSL, Shadertoy and typed uniforms in both APIs. |
| [Masks and filters](filters.md) | Clip layers and build reusable filter graphs. |
| [Audio](audio.md) | Place, trim, loop and mix sound. |
| [Rendering](rendering.md) | Resolution, fonts, compilation, previews and encoder settings. |
| [Low level](lowlevel.md) | SVG rendering and scalar animation signatures. |
| [Upstream examples](examples.md) | Paired ports, asset cache and feature parity status. |
| [Development](development.md) | Rebuild, check and package the bindings. |

Current scope: finite, in-memory scenes rendered with CPU or Skia backends.
Compose still has no video-file visual clip, HTML/CSS layout or streaming API.
Upstream fframes capabilities are not automatically exposed by this wrapper.
