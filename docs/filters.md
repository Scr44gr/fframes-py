# Masks and filters

[Index](index.md)

All compose visuals, including groups, accept `mask` and `filter`. They operate in
the item's local coordinates and follow its transforms. `Composition.size` alone
does not clip children.

`Mask(size=(width, height), radius=0, position=(0, 0))` clips to a rectangle with
optional rounded corners. Position is relative to the local layout origin,
including the ink origin of bounds-anchored text. The mask clips the filtered
result; group opacity is applied after compositing. Size, position and radius
also accept `Tween` or `Samples`.

Filters are ordered graphs. Each step names a `result`; its inputs refer to earlier
results, `SourceGraphic` or `SourceAlpha`. The last step produces the output.

| Step | Inputs |
| --- | --- |
| `Blur` | `source="SourceGraphic"`, `sigma=(x, y)` in pixels. |
| `Flood` | `color` in hex RGBA. |
| `Offset` | `source="SourceGraphic"`, `dx=0`, `dy=0` in local pixels. |
| `ColorMatrix` | `source="SourceGraphic"`, `values`: four rows of five RGBA coefficients. |
| `Composite` | `source`, `destination`, `operator`: `over`, `in`, `out`, `atop`, `xor`, or `arithmetic` with four `coefficients`. |
| `Blend` | `source`, `destination`, CSS `mode` such as `screen` or `multiply`. |
| `DisplacementMap` | `source`, `destination` map, pixel `scale`, RGBA `x_channel`/`y_channel`. |
| `Morphology` | `operator="erode"` or `"dilate"`, positive x/y pixel `radius`. |
| `Turbulence` | x/y `frequency`, `octaves`, `seed`, `noise="turbulence"`/`"fractalNoise"`, `stitch`. |
| `ConvolveMatrix` | x/y `order`, row-major `kernel`, optional nonzero `divisor`, `bias`, `target`, `edge`, `preserve_alpha`. |
| `ComponentTransfer` | Independent `red`, `green`, `blue`, `alpha` functions; `None` preserves the channel. |
| `Lighting` | Alpha height field, `light`, `surface_scale`, `color`, `constant`; `mode="specular"` requires `exponent`. |
| `FilterImage` | File or `ImageBuffer` `source`; `fit="contain"`, `"cover"` or `"stretch"`. |
| `Tile` | Repeat a prior `source` subregion. |
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
will be clipped. Set `units="user"` for a region in local pixels instead.
`color_space="linear"` is the SVG default; `"srgb"` selects sRGB processing.
Results may differ slightly between CPU and Skia. Reuse a `Filter` across items.

`ColorMatrix` multiplies `(r, g, b, a, 1)` by its four rows and clamps the result.
The last column supplies offsets. For example, `(0, 0, 0, 0.5, 0)` as the alpha
row halves opacity; `(0, 0, 0, 127, 0)` hardens partially transparent edges.

Each primitive can set its own `region` in local pixels. This is separate from
the outer filter region and is useful for tiling. Convolution defaults to the
kernel's center and sum (or 1 for a zero sum), with `edge="duplicate"`.

Channel transfers are `LinearTransfer(slope=..., intercept=...)`,
`GammaTransfer(amplitude=..., exponent=..., offset=...)`, and
`TableTransfer(values=(...), kind="table" | "discrete")`.
For filter lighting, import `DistantLight`, `PointLight` or `SpotLight` from
`fframes.compose.filters`; these use pixels/degrees, independently of 3D lights.

## Content masks

`LayerMask` uses any visual or reusable component as an alpha or luminance mask.
It shares the target's local canvas, transforms and clock. Mask content is not
painted as a separate visible layer and cannot contain audio.

```python
from fframes.compose import Circle, LayerMask, Position, Rectangle, Tween

reveal = LayerMask(
    content=Circle(
        radius=Tween(from_value=0, to_value=80, duration=1),
        fill="#ffffff",
        position=Position(x="center", y="center"),
    )
)
panel = Rectangle(size=(200, 100), fill="#3288ff", mask=reveal)
```

`mode="alpha"` uses opacity regardless of color. `mode="luminance"` uses
brightness multiplied by alpha. `region` has the same fractional bounds syntax
as the default filter region. Images, paths, text, gradients, shaders and nested
masked compositions use their usual APIs inside the mask.
