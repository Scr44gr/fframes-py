# Rendering

[Index](index.md)

## Video configuration

Import `Video` and `RenderOptions` from `fframes.compose` for these settings.

| `Video` field | Default | Purpose |
| --- | --- | --- |
| `composition` | Required | Root composition with an explicit duration. |
| `resolution` | `(1920, 1080)` | Positive integer width and height in pixels. |
| `fps` | `30` | Positive integer frames per second; fractional rates are not accepted. |
| `fonts` | `()` | Tuple of explicit font file paths. |
| `load_system_fonts` | `True` | Include fonts installed on the host. |

Fonts, images and audio take filesystem paths; HTTP(S) source URLs are not supported.

Resolution changes the root canvas, not the dimensions of authored shapes.
See [layers](layers.md) for local sizing and scaling.

## Fonts

For repeatable text layout, supply font files, disable system fonts, and choose
their actual family name on `Text`. A family name is not a file path. This example
uses the repository's public-domain test font; run it from the checkout root:

```python
from pathlib import Path

from fframes.compose import Composition, Position, Text, Video

video = Video(
    resolution=(640, 360),
    fonts=(Path("tests/assets/Tuffy.ttf"),),
    load_system_fonts=False,
    composition=Composition(
        duration=1,
        children=(
            Text(
                content="Hello world",
                font_family="Tuffy",
                position=Position(x="center", y="center"),
            ),
        ),
    ),
)
```

Use a font covering your text's characters. Unknown family names can fall back to
other loaded faces; they do not guarantee a particular font. Text needs at least
one loaded font. Invalid explicit font files fail compilation.

## Compile and preview

Continuing with `video` above:

```python
output = Path("output")
output.mkdir(exist_ok=True)
compiled = video.compile()
compiled.save_png(output / "preview.png", index=0)
pixels = compiled.rgba(0)
compiled.render(output / "video.mp4")
```

`compile()` expands components and loads assets once. The compiled object owns
image/audio data and explicit font bytes; subsequent file edits do not affect it.
Compile again to observe changes. System fonts still depend on host files.

`len(video)` and `len(compiled)` return frame counts. Preview indices must be in
`[0, len(compiled))`. `rgba()` returns row-major, straight-alpha RGBA8 bytes:
`width * height * 4` bytes. PNG and RGBA preserve transparency. `save_png()` needs
a `.png` suffix. For repeated previews use `compiled`; the convenience methods on
`video` compile afresh each time. [Audio samples](audio.md) are also available.

## Encoding

| `RenderOptions` field | Default | Meaning |
| --- | --- | --- |
| `encoder` | `"mpeg4"` | Exact FFmpeg video encoder name. |
| `bitrate` | `8_000_000` | Positive integer video bitrate in bits per second. |
| `concurrency` | CPU count, or 1 | Positive number of native rendering workers. |

Pass options as `compiled.render(path, options=RenderOptions(concurrency=4))`.
More workers use more resources; measure before increasing the count. Encoding
runs in Rust with the GIL released. The raw API's separate `RenderOptions` has
`encoder` and `concurrency` only.

Create the output's parent directory before rendering. Supported suffixes are
lowercase `.mp4`, `.mov`, `.mkv`, `.avi` and `.webm`; codec/container compatibility
is still required. Start with MPEG-4 in MP4. Other encoders depend on the linked
FFmpeg build; the LGPL build does not guarantee `libx264`. An unrelated `ffmpeg`
CLI installation does not change the codecs in the extension's native libraries.

Video encoding requires even width/height and uses YUV420P without alpha. Put an
opaque background as the first layer to choose the video's background color.
Temporary segments are created beside the destination and cleaned up on exit;
the existing destination is replaced only after a successful video render.
