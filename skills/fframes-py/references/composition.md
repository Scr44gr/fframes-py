# Composition and layers

Import scene types from `fframes.compose`. Assemble
`Video(composition=Composition(duration=..., children=(...)), resolution=(w, h), fps=n)`.
The root duration is required; dimensions and fps are positive integers. Models
are frozen and reject extra fields. Use tuples, not lists, for model collections.
Construct validated replacements; `model_copy(update=...)` does not validate.

## Choose primitives

| Need | Description |
| --- | --- |
| Panel/background | `Rectangle(size=(w, h), radius=0, fill="#RRGGBB")` |
| Disc | `Circle(radius=r, fill=...)`; local top-left is `(0, 0)`, not the center. |
| Label | `Text(content=..., font_size=32, font_family="sans-serif", font_weight=400)` |
| Custom silhouette | `VectorPath(size=(w, h), segments=(MoveTo(...), ...))` |
| Elliptical geometry | `Ellipse(size=(w, h), fill="#RRGGBB")` |
| Raster asset | `Image(source=path, size=(w, h))`; see the media reference. |

Colors require six or eight hex digits. Shapes and text accept `fill=None` and
`Stroke(color=..., width=...)`. Text is single-line; split lines into positioned
items. Paths start with `MoveTo(x=..., y=...)` and have at least two segments;
use `LineTo(x=..., y=...)`, `CubicTo(control1=(x, y), control2=(x, y), end=(x, y))`
and `Close()`. Coordinates are absolute within the path, not normalized to `size`.
Imported path data can be passed directly as `segments="M0 0h20v20z"`; typed
segment coordinates accept `Tween` and `Samples`. Use `rendering="crispEdges"`
only when the artwork intentionally omits antialiasing.

For mixed typography, use `Text(content=(TextRun(content="Hello "),
TextRun(content="world", fill="#FFD43B")))`. Runs inherit the text's style and
share its baseline and anchor; they can override font family, size and weight.
`LinearGradient(stops=(Stop(offset=0, color=...), Stop(offset=1, color=...)))`
and `RadialGradient(...)` work as fill or stroke paint. Gradient coordinates use
bounding-box fractions unless `units="user"`. `Pattern(source=path, size=(w, h))`
repeats a raster tile in local pixels. Paint and visual `matrix=(a,b,c,d,e,f)`
coefficients accept scalar animations. Stroke supports `cap`, `join`, `miter_limit`,
`dash=(painted, empty, ...)` and animated `dash_offset`.

## Arrange the scene

- Put the background first and overlays last in `children`. Nested compositions
  occupy one place in that order. There is no `z_index` field.
- Give reusable groups an explicit `size`. It defines layout coordinates, not a
  clipping mask or resize operation. Omitted size inherits the parent's canvas.
- Use `Position(x=..., y=...)` in pixels, or axis alignment: x has
  `left/center/right`; y has `top/center/bottom`. Placement aligns untransformed
  bounds; text uses ink bounds and strokes can overflow.
- Apply group `opacity`, `rotation` and `scale` to move the visual as a unit.
  Rotation is clockwise; rotation/scale pivot at the layout center unless
  `origin=(x, y)` supplies a local pivot. Group opacity
  composites children first. These transforms do not alter audio.

## Schedule motion

Place an item with `.at(start_at, duration=...)`. Start is local to the parent;
duration caps content and never stretches it. Intervals are `[start, end)`.
Nested delays add; each repeated occurrence restarts its animation clock.
Unspecified duration inherits the enclosing interval. Root duration caps everything.

Use `Tween(from_value=..., to_value=..., duration=..., easing="linear")` for
numeric x/y, opacity, rotation or scale. Other easing values are `ease_in`,
`ease_out`, `ease_in_out`, `Spring(...)` and `CubicBezier(...)`. `start_at` delays
the tween locally; endpoints hold. Springs can overshoot; duration caps settling. Opacity stays within 0–1, scale stays
positive. Fill and stroke accept `ColorTween` with hex endpoints and the same
duration/easing fields. Rectangle dimensions accept tweens. For discrete changes,
schedule separate items in adjacent clips. Avoid Python loops rebuilding SVG per
frame when compose can express the scene.

Use `Samples(values=(...), fps=30)` for procedural scalar values prepared once.
Rust holds each value for `1/fps` local seconds, then holds the last. This works
for transforms, rectangle extents and shader float uniforms. It transfers owned
values through JSON, not a shared NumPy view. Animated rectangle layout uses its
initial size; choose explicit positions and origins when needed.

`Text(anchor="baseline", position=Position(x=..., y=...))` uses SVG baseline
coordinates instead of ink bounds. A live readout can use
`content=TextTemplate(template="Frame {frame}, {seconds:.2f}s")` with that anchor
and numeric positions. Only `{frame}` and `{seconds:.0f}` through `{seconds:.9f}`
are supported; fields use the item's local clock and are formatted in Rust.
For finite custom readouts, `TextFrames(frames=(...))` selects precomputed lines by
local frame and holds the last line; it has the same anchoring requirements.
Empty lines are allowed in `TextFrames`. Text accepts `text_anchor="middle"`
or `"end"`, `baseline="central"`, and `font_style="italic" | "oblique"`.
For layout, use `TextLayout(fonts=(...))` and `Font(family=..., size=32)` from
either API. `widths((...), font)` batches upstream integer advance metrics;
`fit(text, font, width, marker="…")` truncates, and `wrap(text, font, width)`
returns lines. Metrics exclude kerning and letter spacing; missing families fail.
`letter_spacing` adjusts text spacing in pixels. See [effects](shaders.md) for
shader layers, clipping masks and filter graphs.

## Reuse components

Subclass `Component` with typed Pydantic fields and `compose() -> Composition`.
Compose existing items there; it has no frame argument. An instance expands once
per compilation, so reuse the instance when its inputs match. Wrap each placement
in a composition for independent transforms; the component itself only supplies
content and `.at()`. Keep expansion deterministic and acyclic. Persist application
inputs, not custom components or private compiler JSON. For a full class example,
see `docs/components.md` when working in the repository.
