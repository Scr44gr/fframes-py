# Upstream examples

[Index](index.md)

Ports target [fframes at `055bb6b9`](https://github.com/dmtrKovalenko/fframes/tree/055bb6b9dcbbcca6532206847d43ea8e81fa2a0b/examples).
Each port has an SVG version in `examples/native` and a component version in
`examples/compose`. Shared scene constants live directly in `examples/`.

## Run

From a [configured checkout](development.md), fetch the fonts once:

```sh
uv run --no-sync python -m examples.assets hello_world
uv run --no-sync python -m examples.native.hello_world
uv run --no-sync python -m examples.compose.hello_world
```

Replace `hello_world` with `scenes` in the last two commands to render the
two-scene variant. Both variants run for 30 seconds at 1920×1080, 30 fps.
Output goes to `output/native/` or `output/compose/`.

The shader ports use Vulkan on Windows/Linux and Metal on macOS:

```sh
uv run --no-sync python -m examples.assets shaders
uv run --no-sync python -m examples.native.shaders
uv run --no-sync python -m examples.compose.shaders
```

Replace `shaders` with `neon_triangle` for the six-second, 60 fps neon scene.
`shaders` runs for eight seconds at 30 fps; both use 1920×1080. Append
`--backend skia` to render with Skia CPU when a GPU is unavailable. Shader source
files are cached like other assets; their original algorithms remain unchanged.

Assets come from the commit and SHA-256 hashes in
[`examples/upstream.toml`](../examples/upstream.toml). Downloads are explicit,
verified before replacement, and reused across checkouts. Rendering only reads
verified local files; it never downloads them.

The default cache is `fframes-py/examples` under Windows `%LOCALAPPDATA%`, macOS
`~/Library/Caches`, or Linux `$XDG_CACHE_HOME` (falling back to `~/.cache`). Set
`FFRAMES_EXAMPLE_CACHE` to choose another directory. Assets and rendered output
do not belong in Git; no submodule initialization is needed.

## Port status

The wrapper does **not yet have full upstream feature parity**. Pending entries
require both implementations and render validation; an unimplemented entry is
not replaced by a simplified scene. Requirements below identify the main gaps,
not an exhaustive engine API inventory.

| Upstream example | Status / remaining requirements |
| --- | --- |
| `hello-world` | Ported: [native](../examples/native/hello_world.py), [compose](../examples/compose/hello_world.py); [native scenes](../examples/native/scenes.py), [compose scenes](../examples/compose/scenes.py). |
| `shaders` | Ported: [native](../examples/native/shaders.py), [compose](../examples/compose/shaders.py). |
| `neon-triangle` | Ported: [native](../examples/native/neon_triangle.py), [compose](../examples/compose/neon_triangle.py). |
| `audio-announce` | Pending: synchronized video clips, spectrum analysis, subtitles, filters. |
| `tiktok` | Pending: audio spectrum, VTT subtitles, text wrapping, filters. |
| `podcast` | Pending: audio visualization, subtitles, text layout, image masks. |
| `teej-podcast` | Pending: synchronized clips and chapter layout; user media required. |
| `motion-graphics` | Pending: springs, masks, text alignment/spacing, character reveal; includes quote and install variants. |
| `signal-lab` | Pending: springs/Bézier easing, text fitting, animated geometry, audio. |
| `conference-splash-screen` | Pending: speaker/sponsor layouts, text wrapping and masks. |
| `marketing` | Pending: media, filters and animated graphics. |
| `beta` | Pending: nested demonstration scenes, paths and embedded media. |
| `low-poly-art` | Pending: polygon scenes, patterned paint and animated geometry; includes four birds. |
| `pixel-memory` | Pending: procedural photo scenes, shaders and clips; user photos required. |
| `fframes-intro` | Pending: shaders, clips, transitions and text effects; referenced audio is absent upstream. |

Completed ports were rendered locally on Windows with the pinned fonts. Offline
tests exercise timing and geometry using the repository's test font. Small edge
differences remain between SVG parsing and typed-tree rasterization; byte-identical
output and Linux/macOS visual parity have not been established.

Shader ports were rendered through Vulkan on Windows and previewed with Skia CPU.
Their CI tests use small substitute shaders to check composition without network
or GPU access; they do not replace validation of the pinned upstream programs.
The neon readout is precomputed once, and adjacent clips reproduce its title
flicker while reusing one component. Floating-point rounding and SVG whitespace
normalization can differ from the original Rust formatting.

Upstream example code is © 2025–2026 Dmitriy Kovalenko, used under its
[MIT license](assets/LICENSE.txt). Repeated SVG IDs and redundant wrappers from
the original two-scene example are omitted; its obsolete timing calls are
expressed through the current APIs.
