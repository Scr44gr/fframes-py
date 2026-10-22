# In-memory media

[Index](index.md)

Use `Pcm`, `ImageBuffer` and `VideoFrames` wherever the corresponding file source
is accepted: audio tracks/FFT, image bindings/uniforms/textures, or video clips/
uniforms/textures. Compose media still requires its display `size`.

```python
import numpy as np
from fframes import ImageBuffer, Pcm
from fframes.compose import Audio, Composition, Image, Video

samples = np.zeros((48000, 2), dtype="<f4")
audio = Pcm(data=samples.tobytes(), sample_rate=48000, channels=2)
excerpt = audio.slice(12000, 36000)
assert excerpt.data is audio.data

image = ImageBuffer(data=bytes((40, 100, 255, 255)) * 64 * 64, size=(64, 64))
video = Video(
    resolution=(320, 180),
    composition=Composition(
        duration=1,
        children=(
            Image(source=image, size=(320, 180)),
            Audio(source=excerpt),
        ),
    ),
)
compiled = video.compile()
```

| Source | Storage |
| --- | --- |
| `Pcm` | Interleaved little-endian float32, one or two channels. `sample_rate` describes the source. `slice(start, end)` uses relative sample-frame indices, end exclusive. |
| `ImageBuffer` | Encoded image bytes when `size=None`; otherwise exactly `width * height * 4` straight RGBA8 bytes. |
| `VideoFrames` | Contiguous straight RGBA8 frames, `size=(width, height)`, source `fps`. The existing clip offset, loop and EOF rules apply. |

Inputs retain immutable `bytes`. `array.tobytes()` makes an explicit snapshot;
mutable arrays and memoryviews are not retained by reference. PCM slices share
that snapshot. Compilation borrows payloads outside JSON, then owns decoded
planar samples or premultiplied pixels. These conversions allocate; selected PCM
slices copy only their selected samples. Texture resizing and mipmaps also allocate.

Reuse compiled objects to avoid repeating conversion. Buffer-backed scenes must
be compiled through `Video`/`Renderer`; standalone JSON serialization cannot carry
their binary payloads. For output arrays, `np.frombuffer(compiled.rgba(), dtype="u1")`
creates a read-only view without another pixel copy.
