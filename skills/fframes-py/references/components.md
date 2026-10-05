# Reusable components

Subclass `Component` with typed fields and describe its contents in `compose()`.
The resulting model is immutable; validate dimensions with Pydantic constraints.

```python
from pydantic import PositiveFloat

from fframes.compose import Component, Composition, Position, Rectangle, Video


class Tile(Component):
    side: PositiveFloat = 64

    def compose(self) -> Composition:
        return Composition(
            size=(self.side, self.side),
            children=(Rectangle(size=(self.side, self.side), fill="#FFD43B"),),
        )


tile = Tile()
scene = Video(
    resolution=(320, 180),
    composition=Composition(
        duration=2,
        children=(
            tile.at(0, duration=1),
            Composition(
                size=(64, 64), children=(tile,), position=Position(x=96), scale=0.8, opacity=0.9
            ).at(1, duration=1),
        ),
    ),
).compile()
scene.save_png("tile.png", index=30)
```

An instance expands once per compilation; reuse it when inputs match. Each timed
placement restarts its local animations. Components supply content and `.at()`;
wrap a placement in `Composition` for independent transforms, masks or opacity.
Give that group an explicit `size` when using alignment or a center pivot.
`Tile(position=..., scale=..., opacity=...)` is invalid: these are not built-in
`Component` fields. The error shows which property to move to the wrapper.
If a subclass declares such an input itself, `compose()` must implement its effect.

`compose()` has no frame argument. Keep expansion deterministic and acyclic.
Construct new instances for changed inputs; `model_copy(update=...)` bypasses
validation. Store application inputs when persistence is needed.
