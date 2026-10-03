# Masks and filters

[Index](index.md)

All compose visuals, including groups, accept `mask` and `filter`. They operate in
the item's local coordinates and follow its transforms. `Composition.size` alone
does not clip children.

`Mask(size=(width, height), radius=0, position=(0, 0))` clips to a rectangle with
optional rounded corners. Position is relative to the local layout origin,
including the ink origin of bounds-anchored text. The mask clips the filtered
result; group opacity is applied after compositing.

Filters are ordered graphs. Each step names a `result`; its inputs refer to earlier
results, `SourceGraphic` or `SourceAlpha`. The last step produces the output.

| Step | Inputs |
| --- | --- |
| `Blur` | `source="SourceGraphic"`, `sigma=(x, y)` in pixels. |
| `Flood` | `color` in hex RGBA. |
| `Composite` | `source`, `destination`, `operator`: `over`, `in`, `out`, `atop`, `xor`. |
| `Merge` | `sources` tuple, painted in order. Repeated inputs are allowed. |

```python
from fframes.compose import Blur, Composite, Filter, Flood, Merge, Rectangle

glow = Filter(
    region=(-0.5, -0.5, 2, 2),
    steps=(
        Blur(result="blur", source="SourceAlpha", sigma=(8, 8)),
        Flood(result="tint", color="#FF2BD6"),
        Composite(result="glow", source="tint", destination="blur", operator="in"),
        Merge(result="output", sources=("glow", "SourceGraphic")),
    ),
)
panel = Rectangle(size=(200, 100), fill="#FFFFFF", filter=glow)
```

`region=(x, y, width, height)` is relative to the source object's bounding box.
It defaults to `(-0.1, -0.1, 1.2, 1.2)`; expand it for large blurs or their halo
will be clipped. Filtering uses the native SVG filter color-space rules and may
differ slightly between CPU and Skia. Reuse a `Filter` description across items.
