# Upstream examples

[Index](index.md)

Ports target [fframes at `055bb6b9`](https://github.com/dmtrKovalenko/fframes/tree/055bb6b9dcbbcca6532206847d43ea8e81fa2a0b/examples).
Each port has an SVG version in `examples/native` and a component version in
`examples/compose`. Shared choreography lives in `examples/`; the intro uses `examples/intro/`.

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

The motion studies have three variants, all 1920×1080 at 60 fps:

```sh
uv run --no-sync python -m examples.assets motion_graphics
uv run --no-sync python -m examples.compose.motion_graphics --scene quote --text "SPEED\n!=\nFAST"
uv run --no-sync python -m examples.native.motion_graphics --scene install
uv run --no-sync python -m examples.compose.motion_graphics --family Arial
```

`motion`, `quote` and `install` last 4, 3 and 10 seconds respectively. Both APIs
accept the same flags. The main study defaults to upstream's Helvetica Neue,
which upstream does not distribute. Supply it with `--font path/to/font.ttf`,
or explicitly select an installed replacement with `--family`. The local Windows
render used Arial. Quote and install use the pinned Bebas Neue and JetBrains Mono.

Assets come from the commit and SHA-256 hashes in
[`examples/upstream.toml`](../examples/upstream.toml). Downloads are explicit,
verified before replacement, and reused across checkouts. Rendering only reads
verified local files; it never downloads them.

The default cache is `fframes-py/examples` under Windows `%LOCALAPPDATA%`, macOS
`~/Library/Caches`, or Linux `$XDG_CACHE_HOME` (falling back to `~/.cache`). Set
`FFRAMES_EXAMPLE_CACHE` to choose another directory. Assets and rendered output
do not belong in Git; no submodule initialization is needed.

`signal_lab` uses the same fetch/run commands. Its four six-second studies run
at 1920×1080, 30 fps, with continuous progress and the pinned `pulse.wav` track.

The same commands run `tiktok` (portrait, 60 fps), `audio_announce` (30 fps),
`podcast` (60 fps) and `teej_podcast` (24 fps). Teej defaults to Berkeley Mono,
which upstream does not distribute; use `--family "Sofia Sans Semi Condensed"`
for the bundled alternative, or `--font` with your own font. Podcast accepts
optional `--goose-audio`, `--guest-audio` and `--duck-audio` paths to animate each
speaker independently; its soundtrack is the original mix. Its guest panel
correctly follows the guest track, fixing upstream's accidental goose dependency.

`low_poly` renders the owl by default. `--bird pelican`, `--bird popuga` and
`--bird spektacled_owl` select the other original artworks. Their source files
are cached as data; Python reads only polygon coordinates and colors. The owl
runs for 10 seconds with sound and animated texture; the others last 15 seconds.

`conference` accepts `--talk 0` or a speaker-name fragment such as `--talk Mattio`.
Its 11 sessions, speaker photos, sponsor artwork and fonts are pinned together.
The original track determines its duration; the second scene begins at frame 91.

`marketing` includes the original soundtrack, captions, Ferris animation and logo
outro. It defaults to upstream's unbundled Chalkboard SE; use `--family Arial`
or provide the font with `--font`. It runs for 1,310 frames at 60 fps.

`beta` uses the same font flags and embeds four earlier examples without mixing
their soundtracks into its narration. Its seven scenes include the phone/GitHub
overlap; the audio tail extends it to 2,126 frames. The phone uses the pinned
Inter 24pt face, and its simulated FPS counter uses a fixed random seed.

`pixel_memory` builds a seeded photo film with four published soundtrack choices.
Use `--scene float`, `fibonacci`, `polaroid`, `spiral`, `parallax` or `video` to
inspect an individual algorithm. `--seed` selects repeatable layouts; `--song`
selects the full-film soundtrack. Indie Flower is not bundled upstream: supply
`--font`, or use the pinned alternative with `--family "Space Grotesk"`.
Polaroid dates use EXIF and the original per-photo corrections. The Python random
generator preserves the source distributions, not Rust's exact seed sequence.
Scene selection uses the real video metadata; upstream accidentally probes its
image-only provider. The unpublished Passenger track is not offered.

`intro` runs all 16 scenes at 1920×1080, 60 fps for 127.5 seconds, including
six original shaders, chroma-keyed clips, beat-synchronized cuts and 26 audio tracks.
Use the shader backend flags above; `--frame 2202` saves one global frame as a PNG.
Fetching this example also requires Git: a temporary partial repository supplies
its pinned commit history without checking out media. The resulting text is
hash-verified and cached with the other assets.

The intro preserves upstream's commands, benchmark figures and marketing claims.
They describe the original Rust project, **not measurements or CLI features of
this Python wrapper**. Its displayed 100,000-node headline is also preserved;
the source wall actually draws 3,334 text nodes.

## Port status

All 15 upstream examples now have both implementations. This covers their
rendered compositions; it does not assert parity with every upstream engine API.

| Upstream example | Implementations |
| --- | --- |
| `hello-world` | Ported: [native](../examples/native/hello_world.py), [compose](../examples/compose/hello_world.py); [native scenes](../examples/native/scenes.py), [compose scenes](../examples/compose/scenes.py). |
| `shaders` | Ported: [native](../examples/native/shaders.py), [compose](../examples/compose/shaders.py). |
| `neon-triangle` | Ported: [native](../examples/native/neon_triangle.py), [compose](../examples/compose/neon_triangle.py). |
| `audio-announce` | Ported: [native](../examples/native/audio_announce.py), [compose](../examples/compose/audio_announce.py); cubic spectrum curves, transparent video and glowing captions. |
| `tiktok` | Ported: [native](../examples/native/tiktok.py), [compose](../examples/compose/tiktok.py); original speech, captions, portrait and spectrum. |
| `podcast` | Ported: [native](../examples/native/podcast.py), [compose](../examples/compose/podcast.py); original artwork and independent speaker spectra. |
| `teej-podcast` | Ported: [native](../examples/native/teej_podcast.py), [compose](../examples/compose/teej_podcast.py); five-minute interview, two synchronized clips and chapter navigation. |
| `motion-graphics` | Ported: [native](../examples/native/motion_graphics.py), [compose](../examples/compose/motion_graphics.py), including quote and install variants. |
| `signal-lab` | Ported: [native](../examples/native/signal_lab.py), [compose](../examples/compose/signal_lab.py); four studies with the original soundtrack. |
| `conference-splash-screen` | Ported: [native](../examples/native/conference.py), [compose](../examples/compose/conference.py); sponsor intro and selectable speaker cards. |
| `marketing` | Ported: [native](../examples/native/marketing.py), [compose](../examples/compose/marketing.py); original audio, Ferris, spectra, captions and logo reveal. |
| `beta` | Ported: [native](../examples/native/beta.py), [compose](../examples/compose/beta.py); seven scenes with nested examples, phone interface and original narration. |
| `low-poly-art` | Ported: [native](../examples/native/low_poly.py), [compose](../examples/compose/low_poly.py); all four birds, including the owl's patterned title and soundtrack. |
| `pixel-memory` | Ported: [native](../examples/native/pixel_memory.py), [compose](../examples/compose/pixel_memory.py); all six gallery algorithms, EXIF dates, heart-shaped bokeh, signature and synchronized clips. |
| `fframes-intro` | Ported: [native](../examples/native/intro.py), [compose](../examples/compose/intro.py); all 16 scenes, six shaders, synchronized clips, depth ordering, grain and original sound mix. |

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
