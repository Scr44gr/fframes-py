# Analysis and subtitles

[Index](index.md)

These utilities are shared by `fframes` and `fframes.compose`. Run them while
building a scene, before rendering frames.

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
from fframes.compose import Text

track = Subtitles.parse(Path("captions.vtt").read_text(encoding="utf-8"))
items = tuple(
    Text(content=cue.text).at(cue.start, duration=cue.end - cue.start)
    for cue in track.cues
    if cue.end > cue.start
)
```

Cues preserve source order, overlaps, multiline text, identifiers and layout
settings. Header, styles, notes and regions remain available as data. Parsing
does not execute CSS or translate cue markup into styled text; supply your own
layout and handling of overlapping cues. Use `TextLayout.wrap` for measured lines.
