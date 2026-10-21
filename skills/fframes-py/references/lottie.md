# Lottie

Use a local JSON path; no implicit downloads.

```python
from fframes import Lottie, compose

animation = Lottie(source="confetti.json", loop=True)
print(animation.info.width, animation.info.height, animation.info.duration)
layer = compose.LottieLayer(animation=animation, size=(400, 400)).at(1, duration=3)
```

For SVG, pass `LottieBinding(name="confetti", animation=animation, size=(400, 400))`
to `fframes.Video(lotties=...)` and reference `lottie:confetti` in an image element.
For a mesh, use `three_d.Texture(source=three_d.LottieTexture(animation=animation,
size=(400, 400)))`.

Placement starts the local clock. `offset` skips source seconds; `speed` changes
playback rate. Without looping, the final frame holds. Looping repeats from offset
to the source end. Inspect the JSON's real dimensions and duration before placement.

The upstream renderer supports vector animation, not full After Effects playback:
text/image layers, time remapping, blend modes, effects and expressions are not
rendered. Preview representative frames; successful parsing is not proof that
every layer is supported. Unsupported content needs conversion to supported
vectors or pre-rendered footage.
