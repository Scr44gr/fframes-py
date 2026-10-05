# Reusable components

[Index](index.md)

Subclass `Component`, declare typed Pydantic fields, and implement
`compose() -> Composition`. Return existing visuals, audio or other components.
Use field constraints to validate the component's own inputs.

```python
from typing import Annotated

from pydantic import Field

from fframes.compose import Component, Composition, Position, Rectangle, Text


class Badge(Component):
    label: Annotated[str, Field(min_length=1, max_length=24)]

    def compose(self) -> Composition:
        return Composition(
            size=(320, 96),
            children=(
                Rectangle(size=(320, 96), radius=16, fill="#FFD43B"),
                Text(content=self.label, position=Position(x="center", y="center")),
            ),
        )


badge = Badge(label="Python + Rust")
placed = Composition(
    size=(320, 96),
    children=(badge,),
    position=Position(x=64, y=48),
    scale=0.8,
    opacity=0.9,
)
scene = Composition(
    duration=5,
    children=(badge.at(0, duration=2), placed.at(3, duration=2)),
)
```

The same instance expands once per `Video.compile()`, even when placed several
times. Each placement has independent timing. Equal but distinct instances are
not the same cache entry. Keep `compose()` deterministic; it describes content
and receives no frame callback. A second compilation expands components again.

`Component` describes content; `Composition` supplies visual placement.
`Badge(label="Hello", position=Position(x=64))` is invalid: put `position`,
`scale`, `rotation` or `opacity` on the wrapper, as above. Give it a `size` for
alignment and the transform pivot; omitted size inherits the parent's canvas.
Errors for `position`, `scale` and `opacity` show the wrapper correction.
`.at()` controls time. A subclass may declare its own inputs with these names,
but must explicitly use them in `compose()`; they are never automatic transforms.

Avoid recursive component expansion; cycles and nesting beyond 64 traversal
levels are rejected. Python component classes and the private compiled plan are
not a public JSON interchange format. Persist your application's own typed input
data, then construct components from it.
