# Compose

[Index](index.md)

Use `fframes.compose` to describe visuals and sound as Python objects. A
`Composition` groups content; `Video` supplies the output canvas and frame rate.
After [installation](installation.md), this complete example produces a 2-second video:

```python
from pathlib import Path

from fframes.compose import Composition, Position, Rectangle, Text, Video

output = Path("output")
output.mkdir(exist_ok=True)
video = Video(
    resolution=(1280, 720),
    fps=30,
    composition=Composition(
        duration=2,
        children=(
            Rectangle(size=(1280, 720), fill="#172033"),
            Text(
                content="Hello world",
                position=Position(x="center", y="center"),
                fill="#FFD43B",
                font_size=64,
            ),
        ),
    ),
)
video.render(output / "hello.mp4")
```

This example uses system fonts. For identical font selection on different
machines, configure [explicit fonts](rendering.md#fonts).
For a complete animated component with generated sound, run
`uv run --no-sync python -m examples.compose.composition` from the checkout.

## Model rules

- Use tuples for `children`, `resolution`, `size`, `fonts` and path `segments`.
- Models use strict Pydantic v2 validation, reject unknown fields, and are frozen.
  Numbers must be finite; strings such as `"30"` are not numeric inputs.
- Construct a new model to change inputs. Pydantic's `model_copy(update=...)`
  does not validate updates; do not use it to bypass these constraints.
- The root composition needs a positive `duration` in seconds (at most 86,400).
  Nested duration is optional; [timing](layers.md#clips-and-local-time) explains inheritance.

Python constructs the description once per compilation. Rust evaluates the
animations, rasterizes, mixes sound and encodes. Reuse a
[compiled video](rendering.md#compile-and-preview) when producing several outputs.
