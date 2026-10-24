# Media and rendering

## Resolve assets

Use real local paths; resolve them relative to the script or a known project root
when the working directory may vary. HTTP(S) source URLs are not supported.
`Image` and `VideoClip` require an explicit size. Choose `fit="contain"` for
proportional margins, `"cover"` for proportional cropping, or `"fill"` to stretch.
`fframes.probe_image(path)` returns decoded dimensions and EXIF fields; EXIF can
be absent. Use the dimensions to choose a layout size before constructing `Image`.

For reproducible labels, pass `Video(fonts=(font_path,), load_system_fonts=False, ...)`
and set `Text.font_family` to the font's internal family name. System fonts default
to enabled in compose and can vary by host. Check glyph coverage for the actual
text. Fonts, image data and audio sources are loaded at compilation; explicit font
bytes and media are owned afterward. System font files still depend on the host.

## Place and mix audio

Add `Audio(source=path, ...).at(start, duration=...)` to composition children.
`.at()` moves it on the destination clock; `offset` skips source seconds.
Do not use one in place of the other.

- `gain_db=0` is unchanged level; reduce it to leave headroom for overlaps.
  Valid range is −120 through +24. `pan` ranges from −1 left to +1 right.
- `loop=True` repeats the source suffix starting at `offset`. Without looping,
  audio stops at EOF or the parent/clip end, whichever comes first.
- `fade_in` and `fade_out` are seconds over the whole audible interval,
  including loops. Offsets must precede EOF; all timing values are nonnegative.
- Audio defaults to stereo 48 kHz with native limiting/declick. Exports and
  analysis can select another sample rate. Timing is sample-aligned, independent
  of video fps. Visual opacity does not mute audio.
- `rate` resamples playback, changing pitch and duration. It is not pitch-preserving
  time stretch. `effects` applies `fframes.effects` processors in tuple order:
  `Highpass`, `Lowpass`, `LowShelf`, `HighShelf`, `Peak`, `Compressor`,
  `NormalizeLufs` and `StereoWidth`.
  Filter frequencies are 1–23520 Hz. Set fade curves explicitly when needed.
  Mark dialogue `voice=True` and use `Ducking` on background tracks.

Compilation decodes sources in full; loops materialize the audible interval.
Budget memory accordingly. Generate or obtain sound as a file or `Pcm`, then
compose it. Pass `AudioMixOptions` through `RenderOptions(audio_mix=...)`,
`audio_samples(mix=...)` and `AudioAnalysisOptions(mix=...)` consistently.
It controls `master_gain_db`, `declick` and `limiter`; `None` disables the limiter.
`LimiterOptions(ceiling_db=-1, lookahead_ms=5, release_ms=80)` gives its defaults.
Use `analyze_audio` from the analysis reference to measure the mixed signal.

## Compile and export

`VideoClip(source="clip.mp4", size=(1280, 720), offset=2, loop=False)` is a visual
from `fframes.compose`. Place it with `.at()`; it becomes transparent at EOF.
Looping repeats the suffix from offset to EOF. Add a separate `Audio` with the
same timing for sound. Each rendering worker owns its decoder; keep video files
unchanged and available until rendering ends. `fframes.probe_video(path)` returns
dimensions, duration and source fps. Decoded pixels never pass through Python.

Call `compiled = video.compile()` once, then reuse:

| Call | Use |
| --- | --- |
| `compiled.save_png(path, index=i)` | Inspect a frame; path must end in `.png`. |
| `compiled.rgba(i)` | Straight-alpha RGBA8, row-major bytes. |
| `compiled.audio_samples()` | Raw interleaved stereo float32 little-endian bytes at 48 kHz. |
| `compiled.render(path, options=...)` | Encode the scene and mix its audio. |

Valid indices are `0 <= i < len(compiled)`. Video length rounds duration up to
whole frames; the audio tail is silent. Convenience preview/export methods on
the uncompiled `Video` compile again on every call.

Use `fframes.compose.RenderOptions(bitrate=8_000_000, concurrency=4)`
as an explicit example, not a mandatory worker count. Default concurrency is CPU
count. The default is H.264 through `libopenh264`; prefer lowercase `.mp4`.
Use `fframes.available_encoders()` to inspect the linked library; do not assume
`libx264` exists. Missing encoders fail without a fallback.
Other accepted containers are `.mov`, `.mkv`, `.avi`, `.webm`, subject to codec
compatibility. An extension alone does not select a compatible video encoder.
Direct MKV output currently has upstream frame-rate/duration metadata issues;
prefer MP4 or remux a verified MP4. `color_matrix="bt709"` selects HD color
conversion and metadata; the compatibility default is `"bt601"`.
Verify delivered files with `ffprobe`: expect `h264`/`yuv420p`, plus `aac` for audio.

Create destination parents. Default H.264 encoding needs even dimensions (at least 16 pixels
per axis for OpenH264) and uses YUV420P,
which loses alpha; set an opaque first layer when a background is needed. PNG/RGBA
retain alpha. Rendering cleans temporary segments and replaces the destination
only on success. Compile again if assets or component inputs change.

For a short review export, pass `RenderOptions(frame_range=(start, end))`.
These are original frame indices with `0 <= start < end <= len(compiled)`;
end is exclusive. Original animation/media clocks are preserved; the output
starts at zero with matching trimmed audio. `fps`/`scale` override export settings
without retiming the authored scene; frame count rounds up at the output fps.
`pixel_format` requires encoder support. `codec_params` accepts unique string
pairs; use typed fields for stream layout. `audio=AudioEncoderOptions(...)`
selects encoder, bitrate, rate and format; unsupported settings fail explicitly.

Pass a new `RenderControl()` to each export. Poll `.progress` from another thread
for state, video/audio counters and warnings; `.cancel()` is cooperative. Active
native operations finish before cancellation is observed, including the upstream
mux/audio stage. No Python render callbacks are required.
