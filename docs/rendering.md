# Rendering

[Index](index.md)

## Video configuration

Import `Video` and `RenderOptions` from `fframes.compose` for these settings.

| `Video` field | Default | Purpose |
| --- | --- | --- |
| `composition` | Required | Root composition with an explicit duration. |
| `resolution` | `(1920, 1080)` | Positive integer width and height in pixels. |
| `backend` | `"cpu"` | Rasterizer; see backend choices below. |
| `fps` | `30` | Positive integer frames per second; fractional rates are not accepted. |
| `fonts` | `()` | Tuple of explicit font file paths. |
| `load_system_fonts` | `True` | Include fonts installed on the host. |

Fonts take filesystem paths. Media also accepts [in-memory buffers](buffers.md).
HTTP(S) source URLs are not supported.

Resolution changes the root canvas, not the dimensions of authored shapes.
See [layers](layers.md) for local sizing and scaling.

## Backends

| Backend | Platforms | Use |
| --- | --- | --- |
| `cpu` | All | Default CPU SVG renderer. |
| `skia` | All | Skia CPU, including shaders; suitable for tests without a GPU. |
| `vulkan` | Windows/Linux | Skia GPU; requires a working Vulkan driver. |
| `metal` | macOS | Skia GPU through Metal. |

Selection is explicit; unsupported backends raise an error. GPU rasterization
does not imply hardware encoding or zero-copy export. Rendering reuses one native
renderer per worker; independent `rgba`/PNG previews create temporary contexts.
Both APIs use these choices. See [shaders](shaders.md) for program bindings.

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
        duration=2,
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

The returned `bytes` own a copy of native output. If using NumPy, prefer a
read-only buffer view over another copy; keep its owner alive. Request a writable
copy only when mutation is needed.

## Encoding

| `RenderOptions` field | Default | Meaning |
| --- | --- | --- |
| `encoder` | `"libopenh264"` | Exact FFmpeg video encoder name (H.264). |
| `bitrate` | `8_000_000` | Positive integer video bitrate in bits per second. |
| `concurrency` | CPU count, or 1 | Positive number of native rendering workers. |
| `color_matrix` | `"bt601"` | `"bt601"` or `"bt709"`; controls YUV conversion and encoded color tags together. |
| `frame_range` | `None` | Export original indices `[start, end)`; `None` exports the whole video. |
| `fps`, `scale` | `None`, `1` | Output frame rate and resolution multiplier; authoring clocks remain unchanged. |
| `pixel_format` | `None` | Negotiate YUV420P/NV12, or require an explicit FFmpeg pixel format. |
| `gop_size` | `24` | Maximum GOP size requested from the encoder; 0 requests intra frames. |
| `qmin`, `qmax`, `qcompress`, `max_qdiff` | `15`, `60`, `0.6`, `4` | Encoder quantizer controls. |
| `bitrate_tolerance`, `tag` | `0`, `None` | Rate tolerance and optional four-character codec tag. |
| `codec_params` | `()` | Unique `(name, value)` string pairs passed to the codec. Invalid options fail. |
| `audio` | `AudioEncoderOptions()` | Audio encoder, bitrate, sample rate, sample format and codec parameters. |
| `audio_mix` | `AudioMixOptions()` | [Master gain, limiter and de-click](audio.md#master-mix). |

Pass options as `compiled.render(path, options=RenderOptions(concurrency=4))`.
More workers use more resources; measure before increasing the count. Encoding
runs in Rust with the GIL released. Both APIs share the same `RenderOptions`.

To export seconds 0.5–1.5 of the 30 fps example above:

```python
from fframes import RenderOptions

compiled.render(output / "excerpt.mp4", options=RenderOptions(frame_range=(15, 45)))
```

The interval must satisfy `0 <= start < end <= len(compiled)`; invalid bounds
raise an error rather than being clamped. Animation and media keep their original
timeline clocks. The exported file starts at time zero, with audio trimmed to the
same interval. The compiled video's length and previews remain unchanged.

Create the output's parent directory before rendering. Supported suffixes are
lowercase `.mp4`, `.mov`, `.mkv`, `.avi` and `.webm`; codec/container compatibility
is still required. Use `.mp4` for H.264 video, with AAC when audio is present.
MP4 metadata precedes media data for fast-start playback. MPEG-4 Part 2 remains
available explicitly through `RenderOptions(encoder="mpeg4")`.

`fframes.available_encoders()` lists video encoders in the **linked** FFmpeg library.
Pass `"audio"` to list audio encoders. Hardware entries may still need a compatible
device and driver. Missing encoders
raise an error; rendering never silently substitutes a different codec. Installing
an unrelated `ffmpeg` CLI does not change the extension's encoders.

Default video encoding requires even width/height and 8-bit 4:2:0 without alpha.
The encoder receives YUV420P, or NV12 when it requires semiplanar input (for
example, Intel Quick Sync). H.264 output still reports `yuv420p` in ffprobe.
OpenH264 also requires at least 16 pixels on each axis. Put an
opaque background as the first layer to choose the video's background color.
Temporary segments are created beside the destination and cleaned up on exit;
the existing destination is replaced only after a successful video render.

Check a delivered file with an independently installed `ffprobe`:

```sh
ffprobe -v error -show_entries stream=codec_name,profile,pix_fmt,width,height -of json video.mp4
```

Expect `h264` and `yuv420p` for video, and `aac` if there is audio. This verifies
the file, not acceptance by a particular app: apps can also limit duration,
dimensions or file size. See [codec licensing](codecs.md) for distribution details.

## Export controls

```python
from fframes import AudioEncoderOptions, RenderControl, RenderOptions

options = RenderOptions(
    fps=60,
    scale=0.5,
    concurrency=4,
    audio=AudioEncoderOptions(encoder="aac", sample_rate=44100),
)
control = RenderControl()
# Run this call in an application worker to poll or cancel from another thread.
compiled.render(output / "scaled.mp4", options=options, control=control)
```

Scaling rounds output dimensions to the nearest integer and scales the rendered
canvas. The frame count rounds up at the output fps; authored SVG/TextFrames and
sampled values retain their source clocks. Audio covers the selected original
interval. A fractional final video frame can extend beyond it by less than one
output frame.

`AudioEncoderOptions` defaults to AAC, 192000 bit/s, 48000 Hz and `"fltp"`.
Sample formats are `fltp`, `flt`, `s16`, `s16p`, `s32`, `s32p`; the selected encoder
must support the requested rate and format. Explicit video pixel formats also
require codec support. Codec parameters cannot override stream layout; use the
typed fields for dimensions, frame rate and audio rate. Codec-specific controls
remain subject to FFmpeg's implementation.

`control.progress` reports state, completed/total video and audio frames, and
native warnings. `control.cancel()` requests cooperative cancellation; an active
native operation finishes before cancellation is observed. The current upstream
mux/audio-encoding stage checks cancellation at its boundaries. Cancelled exports
preserve the existing destination. Use a new control for each export; no Python
callbacks run in the rendering loop.
