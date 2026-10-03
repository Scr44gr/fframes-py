# Graphics

[Index](index.md)

Import these classes from `fframes.compose`. All visuals use the
[shared placement and transforms](layers.md#drawing-order-and-coordinates).
Sizes are positive pixel lengths, at most 10,000,000 per dimension.

| Class | Required inputs | Additional configuration |
| --- | --- | --- |
| `Rectangle` | `size=(width, height)` | `radius=0` for square corners. |
| `Circle` | `radius` | Layout bounds are `(2 * radius, 2 * radius)`. |
| `Text` | `content` | `font_family="sans-serif"`, `font_size=32`, `font_weight=400`. |
| `Image` | `source`, `size` | Raster file stretched to the given dimensions. |
| `VectorPath` | `size`, `segments` | Absolute coordinates within its local canvas. |

`Text` accepts one nonempty line, with no newline or NUL. Weight is an integer
from 100 through 900; available faces determine the result. Use separate positioned
text items for multiple lines. Characters such as `<` and `&` need no XML escaping.
See [font configuration](rendering.md#fonts).

## Paint

Colors are `#RRGGBB` or `#RRGGBBAA`; named colors and three-digit hex are rejected.
Shapes and text default to black. `Rectangle`, `Circle` and `VectorPath` accept
`fill=None` for no fill and `stroke=Stroke(color=..., width=...)` for an outline.
Stroke width defaults to 1 and is centered on the geometry's boundary.

## Paths

Use `MoveTo` to start a contour, `LineTo` for a straight edge, `CubicTo` for a
cubic Bézier, and `Close()` to join back to that contour's start. At least two
segments are required, beginning with `MoveTo`. `size` controls alignment and
transform origin; it does not normalize coordinates or clip the path.

```python
from fframes.compose import Close, CubicTo, LineTo, MoveTo, Stroke, VectorPath

leaf = VectorPath(
    size=(120, 80),
    fill="#4CAF50",
    stroke=Stroke(color="#FFFFFF", width=3),
    segments=(
        MoveTo(x=0, y=80),
        CubicTo(control1=(0, 0), control2=(120, 0), end=(120, 80)),
        LineTo(x=60, y=60),
        Close(),
    ),
)
```

## Images

`Image(source=Path("assets/logo.png"), size=(160, 90))` requires a local file;
paths are relative to the process working directory. PNG is a useful choice for
transparency. The decoder determines which other raster formats are available.
Images are loaded at compilation, not at model construction. There is no automatic
contain/cover mode: compute a size with the source's aspect ratio to avoid stretching.
