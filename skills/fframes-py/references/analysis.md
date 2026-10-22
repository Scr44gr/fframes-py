# Spectrum and captions

Import `AudioData` and `Subtitles` from either public namespace. Analyze sources
once during construction; never decode or calculate FFT in a Python frame callback.

`AudioData(source=path).spectrum(frames=..., fps=..., sample_size=64, smooth=4)`
returns `Spectrum(data, frames, bins, fps)`. `data` is immutable float32
little-endian, row-major frames by `sample_size // 2` unnormalized bins. Powers
of two from 2 through 1024 are supported. `smooth=0` disables averaging;
`center=True` moves low frequencies to the middle. `window="hamming_legacy"`
is only for matching upstream's original, nonstandard coefficients.

Use `np.frombuffer(result.data, dtype="<f4").reshape(result.frames, result.bins)`
for a read-only view. Allocate one writable result when needed, then use `out=`.
Do not claim the current JSON-based `Samples` input is zero-copy.

`Subtitles.parse(path.read_text(encoding="utf-8"))` returns ordered cues with
`start`, `end`, `text`, optional `name` and `settings`. Preserve overlapping cues
unless the intended layout explicitly prioritizes one. Skip zero-duration cues
when creating timed layers. Parsing retains markup, styles and regions as data;
it does not render them. Measure line wrapping with `TextLayout` and place each
line using `Text`. Define the visual style explicitly.

## Mix reports

`analyze_audio(compiled.native, options=AudioAnalysisOptions(...))` works for
compose and raw native videos. It returns `.report` (LUFS, peaks, clipping,
silence and named section levels), `.waveform.left/right` min/max bins and
`.activity` at requested original seconds. Undefined silent levels are `None`.
Use `AudioSection(name=..., start=..., end=...)` for original-time intervals.
`frame_range` uses original indices; report times are relative to
`.start_seconds`. Analysis allocates the selected mixed interval. Set the same
`mix` and `sample_rate` as the export before comparing measurements.
