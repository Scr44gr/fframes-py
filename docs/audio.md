# Audio

[Index](index.md)

For waveform frequency data and timed captions, see [Analysis and subtitles](analysis.md).

Add `Audio` items to the same `Composition.children` tuple as visuals.
Overlapping tracks mix; child order does not create audio priority. Paths identify
local files decoded during compilation. The mixer uses stereo at 48,000 Hz;
mono input is available in both output channels.

| Field | Default | Meaning |
| --- | --- | --- |
| `source` | Required | Audio file path, or a media file with a decodable audio stream. |
| `offset` | `0` | Seconds skipped at the start of the source; must precede EOF. |
| `loop` | `False` | Repeat the source portion from `offset` through EOF. |
| `gain_db` | `0` | Gain from −120 to +24 dB; negative values reduce level. |
| `pan` | `0` | −1 left, 0 centered, +1 right. |
| `fade_in` | `0` | Fade duration in seconds from the audible start. |
| `fade_out` | `0` | Fade duration in seconds leading to the audible end. |
| `fade_curve` | `"equal_power"` | Also `"linear"`, `"s_curve"` or `"exponential"`. |
| `rate` | `1` | Speed and pitch together, from 0.05 to 20; source offset stays in source seconds. |
| `effects` | `()` | Ordered native processing steps, applied before gain, pan, fades and ducking. |
| `voice` | `False` | Mark this track's interval as voice for ducking. |
| `duck` | `None` | `Ducking(...)` lowers this track during voice intervals. |

For existing `assets/music.wav` and `assets/hit.wav`:

```python
from pathlib import Path

from fframes.compose import Audio, Composition

soundtrack = Composition(
    duration=8,
    children=(
        Audio(
            source=Path("assets/music.wav"),
            offset=1,
            loop=True,
            gain_db=-12,
            fade_in=0.2,
            fade_out=0.5,
        ),
        Audio(source=Path("assets/hit.wav"), pan=0.25).at(2, duration=1),
    ),
)
```

The music repeats the portion after source second 1 for eight seconds. The hit
starts at composition second 2 and stops after one second or EOF, whichever comes
first. Fades span the complete audible interval, not each loop repetition.

`.at()` controls destination time; `offset` controls source time. Nested timings
follow the [same clip rules](layers.md#clips-and-local-time) as visuals, but audio
placement is rounded to sample positions rather than video frames. Visual opacity,
position and scale do not mute or modify audio. There is no group gain control.

Sources are decoded in full. Loops materialize their audible interval once, so
long tracks and long repetitions increase memory use. The upstream mixer applies
its default limiting/declick behavior; leave headroom when overlapping tracks.

Use `compiled.audio_samples()` to inspect the mix: interleaved left/right float32,
little-endian, at 48 kHz. This returns raw bytes, not a WAV file. Its length covers
the encoded video duration, including silence. Audio is mixed into `render()`
automatically; audio codec selection currently follows the native encoder defaults.

## Processing

Effects are shared by `fframes.AudioTrack` and `compose.Audio`:

```python
from fframes.compose import Audio
from fframes.effects import Compressor, Highpass, NormalizeLufs

voice = Audio(
    source="voice.wav",
    voice=True,
    effects=(Highpass(hz=80), Compressor(threshold_db=-18), NormalizeLufs(lufs=-16)),
)
```

The engine processes each audible track once at 48 kHz, after resampling for
`rate`. Available effects are `Highpass`, `Lowpass`, `LowShelf`, `HighShelf`,
`Peak`, `Compressor`, `NormalizeLufs` and `StereoWidth`. Frequencies are 1–23520 Hz;
compressor attack/release use seconds. Normalization leaves silence and intervals
shorter than 400 ms unchanged. A later `gain_db` still changes normalized level.

`StereoWidth(width=0)` makes stereo mono; 1 preserves stereo. Mono input gains
upstream's filtered, delayed side signal when width is positive. `Ducking` reacts
to marked **intervals**, including silent voice tracks; it is not signal detection.
Check the actual mix and listen before choosing gains or publishing an export.
