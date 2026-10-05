# Graphics

[Index](index.md)

Import these classes from `fframes.compose`. All visuals use the
[shared placement and transforms](layers.md#drawing-order-and-coordinates).
Explicit sizes are positive pixel lengths, at most 10,000,000 per dimension.

| Class | Required inputs | Additional configuration |
| --- | --- | --- |
| `Rectangle` | `size=(width, height)` | `radius=0` for square corners; accepts scalar animation. |
| `Circle` | `radius` | Accepts scalar animation, including zero for reveals. |
| `Ellipse` | `size=(width, height)` | Inscribed in its local bounds. |
| `Text` | `content` | `font_family="sans-serif"`, `font_size=32`, `font_weight=400`. |
| `ShaderLayer` | `shader`, `size` | [Native shader program](shaders.md). |
| `Image` | `source`, `size` | Raster file stretched to the given dimensions. |
| `VideoClip` | `source`, `size` | Synchronized local video; `offset=0`, `loop=False`. |
| `VectorPath` | `size`, `segments` | Absolute coordinates within its local canvas. |

## Animated sizes

Each `Rectangle.size` dimension accepts a number, `Tween` or `Samples` and must
stay **greater than zero**, including tween endpoints, samples and spring
overshoot. `Tween(from_value=0, ...)` is rejected for either dimension. Start
with a positive width and animate opacity from zero for a fully invisible start:

```python
from fframes.compose import Circle, Rectangle, Tween

bar = Rectangle(
    size=(Tween(from_value=1, to_value=240, duration=1), 16),
    opacity=Tween(from_value=0, to_value=1, duration=1),
)
disc = Circle(radius=Tween(from_value=0, to_value=16, duration=1))
```

`Circle.radius` accepts zero as empty geometry and rejects negative values.
Unlike rectangle dimensions, a circle's zero initial radius uses a one-pixel
layout bound; its animated geometry still grows from `(0, 0)` to `(2*r, 2*r)`.
For both shapes, alignment and the default transform pivot use the initial
bounds. Use explicit positions and origins when an expanding shape must stay centered.

## Text

`Text` accepts one nonempty line, with no newline or NUL. `font_weight` is an
integer from 100 through 900, including intermediate values such as 450;
use `700` for bold, not `"bold"` or `"700"`. Available font faces determine the
result. `TextRun.font_weight` and `Font.weight` use the same validation.
`letter_spacing=0` sets additional spacing in pixels. Use separate positioned
text items for multiple lines. Characters such as `<` and `&` need no XML escaping.
See [font configuration](rendering.md#fonts).

For mixed colors or fonts on one baseline, pass
`content=(TextRun(content="Hello "), TextRun(content="world", fill="#FFD43B"))`.
Runs inherit the enclosing `Text` style; optional `font_family`, `font_size`,
`font_weight` and `fill` override it. Shaping, spacing and anchoring stay native.
`dx` and `dy` move the text cursor before a run; subsequent runs continue there.

By default, position aligns the shaped ink bounds. Use `anchor="baseline"` to
interpret x/y as SVG baseline coordinates. For a live counter, pass
`content=TextTemplate(template="Frame {frame} / {seconds:.2f}s")`.
Rust formats the item's local frame index and
elapsed seconds during rendering. Supported fields are `{frame}` and
`{seconds:.0f}` through `{seconds:.9f}`; double braces produce literal braces.

With baseline coordinates, `text_anchor="start" | "middle" | "end"` aligns the
text horizontally; `baseline="central"` centers it vertically on y. Font style
is `font_style="normal" | "italic" | "oblique"`, subject to available faces.

For finite custom readouts, precompute one line per frame:

```python
from fframes.compose import Position, Text, TextFrames

counter = Text(
    content=TextFrames(frames=tuple(f"Frame {index}" for index in range(30))),
    font_weight=700,
    anchor="baseline",
    position=Position(x=24, y=48),
).at(0.5, duration=2)
```

At `Video(fps=30, ...)`, this clip starts at video frame 15 with `"Frame 0"`;
frame 16 shows `"Frame 1"`, and frame 44 reaches `"Frame 29"`. The last line holds
until the clip ends. `TextFrames` uses the video's fps, with no separate rate.
Its nonempty tuple may contain `""` for an invisible frame; newline and NUL are
invalid. Rust selects lines during rendering, without a Python callback.
Both `TextFrames` and `TextTemplate` require `anchor="baseline"` and numeric
positions (numbers, `Tween` or `Samples`). To center changing text, use a numeric
x coordinate with `text_anchor="middle"`; `Position(x="center")` is invalid.

Run [the complete example](../examples/compose/reveals.py) with
`uv run --no-sync python -m examples.compose.reveals` from a configured checkout.
It combines animated dimensions, a zero-radius circle and per-frame text.

## Text layout

`Font` and `TextLayout` are available from both APIs. Load fonts once and perform
layout during construction:

```python
from fframes import Font, TextLayout

layout = TextLayout(fonts=("assets/Inter.ttf",))
font = Font(family="Inter", size=32)
widths = layout.widths(("Hello", "Hello world"), font)
title = layout.fit("A longer title", font, 240)
lines = layout.wrap("Words that wrap into separate lines", font, 240)
```

These are upstream's integer character-advance metrics, including spaces, not
shaped ink bounds. They exclude kerning and additional letter spacing. `fit`
uses an ellipsis by default (`marker=""` clips); `wrap` preserves whole words,
so a word wider than the requested width remains on its own line. A missing
font family raises `ValueError`. Position the resulting lines with `Text`.

All visuals support [masks and filter graphs](filters.md).

## Paint

Colors are `#RRGGBB` or `#RRGGBBAA`; named colors and three-digit hex are rejected.
Shapes and text default to black. `Rectangle`, `Circle`, `Ellipse`, `Text` and `VectorPath` accept
`fill=None` for no fill and `stroke=Stroke(color=..., width=...)` for an outline.
Stroke width defaults to 1 and is centered on the geometry's boundary.
Set `cap="round" | "square" | "butt"`, `join="round" | "bevel" | "miter"`,
and `miter_limit=4`. `dash=(8, 4)` alternates painted and empty lengths;
individual lengths also accept `Tween` or `Samples` and must stay nonnegative.
`dash_offset` accepts a number, `Tween` or `Samples`. An empty dash tuple is solid.
`rendering="crispEdges"` disables antialiasing on a shape; the default is `"auto"`.

Fill and stroke colors also accept
`ColorTween(from_value="#FF0000", to_value="#0000FF", duration=2)`.
It uses the same local clock and easing options as `Tween`, interpolates all four
RGBA channels in Rust, and holds its final color after the duration.

`ColorSamples(values=("#ff0000", "#0000ff"), fps=2)` holds discrete colors on
the local clock; use it anywhere a fill, stroke or shader color is accepted.

Fills and strokes also accept paint objects:

```python
from fframes.compose import LinearGradient, Pattern, Stop

gradient = LinearGradient(
    start=(0, 0),
    end=(0, 1),
    stops=(Stop(offset=0, color="#A855F7"), Stop(offset=1, color="#22D3EE00")),
)
texture = Pattern(source="noise.png", size=(230, 177))
```

Gradient coordinates default to bounding-box fractions; `units="user"` uses local
pixels. Stops are ordered, with offsets from 0 to 1; repeated offsets make sharp
transitions. `spread="pad" | "repeat" | "reflect"` controls values beyond the ends.
`RadialGradient` uses `center=(0.5, 0.5)`, `radius=0.5` and an optional `focus`.
`Pattern` repeats a raster image stretched into its pixel-sized tile. Images are
decoded once and shared with other image components. Both paint types accept
`matrix=(a, b, c, d, e, f)`, including `Tween` or `Samples` in any coefficient.
Coordinates are local to the graphic, before its placement transform.

## Paths

Use `MoveTo` to start a contour, `LineTo` for a straight edge, `CubicTo` for a
cubic Bézier, and `Close()` to join back to that contour's start. At least two
segments are required, beginning with `MoveTo`. `size` controls alignment and
transform origin; it does not normalize coordinates or clip the path.

Coordinates in `MoveTo`, `LineTo` and `CubicTo` also accept `Tween` or `Samples`.
Rust evaluates only animated commands; static geometry is retained. For imported
artwork, `segments="M0 0h40v20z"` accepts the complete SVG path-data grammar,
including relative commands, quadratic curves and arcs. It is validated natively
and parsed at compilation; no XML document or Python frame callback is needed.

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
Images are loaded at compilation, not at model construction. Images and video clips
accept `fit="fill"` (stretch, the default), `"contain"` (preserve aspect ratio with
transparent margins), or `"cover"` (preserve aspect ratio and crop). Both aspect
ratio modes center the source in `size`.

`probe_image(path)` returns `ImageInfo(width, height, exif)`. Each EXIF field has
an IFD number, tag and display value with units. Missing or unreadable EXIF yields
an empty tuple; invalid image data raises an error. This uses the native image
decoder once, so retain the result when inspecting the same photo repeatedly.

## Video clips

```python
from fframes import probe_video
from fframes.compose import Audio, Composition, VideoClip

info = probe_video("interview.mp4")
scene = Composition(
    duration=8,
    children=(
        VideoClip(source="interview.mp4", size=(1280, 720), offset=2).at(1, duration=6),
        Audio(source="interview.mp4", offset=2).at(1, duration=6),
    ),
)
```

`offset` is a source timestamp; `.at()` places the clip on the parent's clock.
Playback uses the output frame rate and becomes transparent at source EOF.
Frame selection follows upstream: the first source timestamp at or after the
target, holding the final frame until EOF. A slower source can therefore advance
early when the source and output frame rates differ.
`loop=True` repeats the interval from offset to EOF. Audio is explicit: add an
`Audio` item with matching timing to keep sound, or omit it for a silent clip.
Masks and transforms work like other visuals.

Each render worker owns its decoder cache, keyed by the complete local path.
Source pixels stay in Rust; decoding and color conversion can allocate new
buffers. Keep source files unchanged and available while using the compiled
video. This differs from images and audio, which are loaded into owned memory.
