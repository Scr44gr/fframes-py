# Media and rendering

## Resolve assets

Use real local paths; resolve them relative to the script or a known project root
when the working directory may vary. HTTP(S) source URLs are not supported.
`Image` requires an explicit size and stretches to fit. Choose proportional
dimensions to preserve aspect ratio.

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
- Audio mixes at stereo 48 kHz with native limiting/declick defaults. It is
  sample-aligned, independent of video fps. Visual opacity does not mute it.

Compilation decodes sources in full; loops materialize the audible interval.
Budget memory accordingly. There is no audio-generation API: generate or obtain
the requested sound as a file first, then compose it. Audio codec selection is
currently native-default behavior rather than a Python option.

## Compile and export

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

Use `fframes.compose.RenderOptions(encoder="mpeg4", bitrate=8_000_000, concurrency=4)`
as an explicit example, not a mandatory worker count. Default concurrency is CPU
count. The available codecs come from the linked FFmpeg build; do not assume
`libx264` exists. Lowercase `.mp4` with MPEG-4 is the basic compatible output.
Other accepted containers are `.mov`, `.mkv`, `.avi`, `.webm`, subject to codec
compatibility. An extension alone does not select a compatible video encoder.

Create destination parents. Encoding needs even dimensions and uses YUV420P,
which loses alpha; set an opaque first layer when a background is needed. PNG/RGBA
retain alpha. Rendering cleans temporary segments and replaces the destination
only on success. Compile again if assets or component inputs change.
