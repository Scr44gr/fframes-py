# Analysis and subtitles

[Index](index.md)

These utilities are shared by `fframes` and `fframes.compose`. Run them while
building a scene, before rendering frames.

## Mixed audio

Given a `compose.CompiledVideo` named `compiled` (or a raw `Video`):

```python
from fframes import AudioAnalysisOptions, AudioSection, analyze_audio

inspection = analyze_audio(
    compiled.native,
    options=AudioAnalysisOptions(
        sections=(AudioSection(name="Intro", start=0, end=1),),
        at=(0.5,),
        waveform_bins=200,
    ),
)
```

`AudioInspection.report` contains integrated LUFS, loudness range, maximum
momentary/short-term loudness, sample/true peak, clipped sample count, silent
ranges and section levels. Undefined silent levels are `None`.
`waveform.left/right` contains min/max bins covering the full interval, including
its final samples. `activity` reports active sources, source time, gain, ducking,
voice flags, playback rate and effects at each requested `at` time. `file` is a
path for file sources and an opaque identifier for memory sources.

`frame_range` uses original end-exclusive indices. Section bounds and `at` use
original seconds; sections are intersected with the analyzed range. Report times
are relative to `start_seconds`. Set `sample_rate` to measure a resampled mix;
it defaults to 48000. Analysis runs in Rust and allocates the selected mixed PCM
interval. Use the same `mix` as the export for comparable measurements.

## Audio spectrum

```python
import numpy as np

from fframes import AudioData

audio = AudioData(source="voice.mp3")
spectrum = audio.spectrum(frames=300, fps=30, sample_size=64, smooth=4, center=True)
magnitudes = np.frombuffer(spectrum.data, dtype="<f4").reshape(spectrum.frames, spectrum.bins)
heights = np.empty_like(magnitudes)
np.multiply(magnitudes, 200, out=heights)
np.clip(heights, 10, 200, out=heights)
```

NumPy is optional (`uv add numpy`). `frombuffer` and `reshape` above share the
immutable native result; only `heights` allocates writable storage. Keep using
`out=` for in-place arithmetic. `Samples` currently transfers values into Rust
through JSON, so that later step does copy.

`AudioData` decodes mono samples once and owns them independently of the file.
Analysis releases the GIL. `sample_size` is a power of two from 2 through 1024;
the result has half that many unnormalized magnitude bins, excluding Nyquist.
`center=True` rearranges bins so low frequencies appear in the middle.

`smooth=0` disables averaging. Otherwise, after the first `2*smooth+1` frames,
each result averages `[frame-smooth, frame+smooth)`, following upstream timing.
`window` accepts `None`, `"hann"`, `"hamming"`, or `"hamming_legacy"`; the last
reproduces upstream 1.2.0's nonstandard coefficients for existing scenes.

## WebVTT

```python
from pathlib import Path

from fframes import Subtitles
from fframes.compose import Composition, Position, Text

track = Subtitles.parse(Path("captions.vtt").read_text(encoding="utf-8"))
items = tuple(
    Composition(
        children=tuple(
            Text(content=line, position=Position(y=index * 40))
            for index, line in enumerate(cue.text.splitlines())
            if line
        ),
    ).at(cue.start, duration=cue.end - cue.start)
    for cue in track.cues
    if cue.end > cue.start
)
```

Cues preserve source order, overlaps, multiline text, identifiers and layout
settings. Header, styles, notes and regions remain available as data. Parsing
does not execute CSS or translate cue markup into styled text; supply your own
layout and handling of overlapping cues. `Text` accepts one line, so split cues
as above; use `TextLayout.wrap` when line lengths also need to fit a given width.
