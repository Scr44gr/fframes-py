# Examples

[Index](index.md)

`examples/native/` uses SVG; `examples/compose/` uses components. Shared data and
choreography live in `examples/shared/`, not a third public API.

## Run

From a [development checkout](development.md), these need no downloaded assets:

```sh
uv run --no-sync python -m examples.native.motion
uv run --no-sync python -m examples.compose.composition
uv run --no-sync python -m examples.compose.reveals
uv run --no-sync python -m examples.native.three_d
uv run --no-sync python -m examples.compose.three_d
```

`reveals` demonstrates animated sizes and per-frame text. `three_d` puts an
animated 3D cube inside a 2D screen, then uses that screen on a 3D monitor;
its `build()` accepts `RenderSettings(device="gpu")`, with CPU as the default.

For an upstream port, fetch its assets once and choose an API:

```sh
uv run --no-sync python -m examples.assets hello_world
uv run --no-sync python -m examples.native.hello_world
uv run --no-sync python -m examples.compose.hello_world
```

Replace `hello_world` with a module from the table below. Output goes to
`output/native/` or `output/compose/`. Shader examples default to Vulkan on
Windows/Linux and Metal on macOS; append `--backend skia` for Skia CPU.

## Assets

[`upstream.toml`](../examples/upstream.toml) pins the
[1.2.0 example revision](https://github.com/dmtrKovalenko/fframes/tree/055bb6b9dcbbcca6532206847d43ea8e81fa2a0b/examples)
and each asset's SHA-256. Downloads are explicit, verified before replacement,
and cached outside Git. Rendering never downloads assets; no submodule is needed.

The cache is `fframes-py/examples` under Windows `%LOCALAPPDATA%`, macOS
`~/Library/Caches`, or Linux `$XDG_CACHE_HOME` (default `~/.cache`). Override it
with `FFRAMES_EXAMPLE_CACHE`. Fetching `intro` also needs Git for its pinned
commit-history text; it uses a temporary partial repository without checking out media.

## Port catalog

All 15 examples at that asset revision have both implementations. The names in
this table are Python module names; linked files contain their defaults and CLI.

| Module / upstream name | Native / compose | Variants or required choices |
| --- | --- | --- |
| `hello_world` / hello-world | [SVG](../examples/native/hello_world.py), [compose](../examples/compose/hello_world.py) | After fetching `hello_world`, run module `scenes` for the two-scene variant. |
| `shaders` | [SVG](../examples/native/shaders.py), [compose](../examples/compose/shaders.py) | SkSL and Shadertoy. |
| `neon_triangle` / neon-triangle | [SVG](../examples/native/neon_triangle.py), [compose](../examples/compose/neon_triangle.py) | Neon shader and animated readout. |
| `audio_announce` / audio-announce | [SVG](../examples/native/audio_announce.py), [compose](../examples/compose/audio_announce.py) | Spectrum curves, transparent video and captions. |
| `tiktok` | [SVG](../examples/native/tiktok.py), [compose](../examples/compose/tiktok.py) | Portrait speech, captions and spectrum. |
| `podcast` | [SVG](../examples/native/podcast.py), [compose](../examples/compose/podcast.py) | Optional `--goose-audio`, `--guest-audio`, `--duck-audio` drive independent spectra; soundtrack stays the original mix. |
| `teej_podcast` / teej-podcast | [SVG](../examples/native/teej_podcast.py), [compose](../examples/compose/teej_podcast.py) | Two synchronized clips. Berkeley Mono is not bundled; use `--font` or `--family "Sofia Sans Semi Condensed"`. |
| `motion_graphics` / motion-graphics | [SVG](../examples/native/motion_graphics.py), [compose](../examples/compose/motion_graphics.py) | `--scene motion`, `quote` or `install`; quote also accepts `--text`. Motion needs Helvetica Neue or an explicit `--family`/`--font`. |
| `signal_lab` / signal-lab | [SVG](../examples/native/signal_lab.py), [compose](../examples/compose/signal_lab.py) | Four studies with the original soundtrack. |
| `conference` / conference-splash-screen | [SVG](../examples/native/conference.py), [compose](../examples/compose/conference.py) | `--talk 0` or a speaker-name fragment such as `--talk Mattio`. |
| `marketing` | [SVG](../examples/native/marketing.py), [compose](../examples/compose/marketing.py) | Chalkboard SE is not bundled; supply `--font` or select `--family Arial`. |
| `beta` | [SVG](../examples/native/beta.py), [compose](../examples/compose/beta.py) | Same font choice as marketing; nested films retain only the narration soundtrack. |
| `low_poly` / low-poly-art | [SVG](../examples/native/low_poly.py), [compose](../examples/compose/low_poly.py) | Owl by default; `--bird pelican`, `popuga` or `spektacled_owl` selects other artwork. |
| `pixel_memory` / pixel-memory | [SVG](../examples/native/pixel_memory.py), [compose](../examples/compose/pixel_memory.py) | `--scene float`, `fibonacci`, `polaroid`, `spiral`, `parallax` or `video`; `--seed`/`--song` select layout/audio. Supply Indie Flower with `--font`, or use `--family "Space Grotesk"`. |
| `intro` / fframes-intro | [SVG](../examples/native/intro.py), [compose](../examples/compose/intro.py) | All 16 scenes, six shaders and 26 audio tracks; `--frame 2202` saves a global frame. |

The engine's 1.3.0 release adds `arm`, `svg-in-3d`, `lottie-launch`, `shader-mode`
and `made-of-motion`; these five complete films are **not ported**. The local
`three_d` study demonstrates nested textures, not a full `svg-in-3d` port.
Upstream `main` later renamed `lottie-launch` to `lottie` and removed
`motion-graphics`; our pinned examples remain reproducible.

## Differences and verification

- The guest spectrum follows its own track, correcting upstream's source mix-up.
  Gallery scene selection probes video metadata rather than the image provider.
- Python's seeded gallery layouts preserve distributions, not Rust's exact random
  sequence. The unpublished Passenger track is omitted. Font substitutions and
  floating-point/text normalization can change pixels.
- `intro` preserves upstream's commands and performance claims. They are not
  measurements or CLI features of this wrapper. Its 100,000-node headline is
  retained, although the source wall draws 3,334 text nodes.
- Complete ports were rendered locally on Windows; shader ports used Vulkan.
  Offline tests use small fixtures and substitute shaders, not downloaded films.
  Byte-identical output and Linux/macOS visual parity have not been established.

See [engine compatibility](upstream.md) for API gaps and platform test scope.
Upstream example code is © 2025–2026 Dmitriy Kovalenko, used under its
[MIT license](assets/LICENSE.txt).
