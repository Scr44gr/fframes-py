# Lottie

[Index](index.md)

```python
from fframes import Lottie, compose

animation = Lottie(source="animation.json", loop=True)
print(animation.info)  # native dimensions and duration in seconds
video = compose.Video(
    resolution=(640, 360),
    composition=compose.Composition(
        duration=4, children=(compose.LottieLayer(animation=animation, size=(320, 320)).at(0.5),)
    ),
)
```

`offset` skips source seconds; `speed` changes playback rate. Without `loop`,
playback holds the last frame. Looping repeats the interval from `offset` to EOF.
The layer's placement starts its local clock. `size` sets raster dimensions;
normal compose transforms, masks and filters remain available.

The SVG equivalent is `LottieBinding(name="animation", animation=animation,
size=(320, 320), start_at=0.5)` in `Video.lotties`, referenced by
`<image href="lottie:animation" width="320" height="320"/>`.
For meshes use [`LottieTexture`](three-d-assets.md#textures).

Parsing/evaluation uses upstream fframes and Velato. Supported vector paths,
fills, strokes, gradients, masks and transforms render on CPU or Skia. Upstream
omits text layers, image layers, time remapping, blend modes, effects and
expressions. Convert unsupported content to vector shapes and inspect the result;
a valid JSON file does not establish visual parity with After Effects.
