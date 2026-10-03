# Layers and timing

[Index](index.md)

## Drawing order and coordinates

`Composition.children` is ordered back to front: the last visible child is drawn
on top. A nested composition is a group in that order; its children cannot be
interleaved with a sibling's children. There is no separate `z_index`.

`Composition.size=(width, height)` defines a local canvas. Omit it to inherit the
parent's size; the root inherits `Video.resolution`. It neither resizes child
geometry nor clips overflow. Use `scale` to resize a whole group. The final video
canvas clips content outside the output bounds.

`Position` places the top-left of the item's untransformed layout bounds:

| Axis | Pixel coordinate | Alignment values |
| --- | --- | --- |
| `x` | Positive rightward; negative allowed | `"left"`, `"center"`, `"right"` |
| `y` | Positive downward; negative allowed | `"top"`, `"center"`, `"bottom"` |

Alignment uses the parent's local canvas. A circle's bounds are its diameter;
text uses its shaped ink bounds. Stroke can extend beyond layout bounds.

All visuals and compositions share `position`, `opacity` (0–1), `rotation`
(clockwise degrees), and `scale` (positive, at most 10,000). Rotation and scale
use the item's layout center unless `origin=(x, y)` supplies a local pivot.
For example, `origin=(0, 0)` rotates about the top-left. Group opacity applies to the composited children,
so it differs from lowering each child's opacity separately.

## Clips and local time

`item.at(start_at, duration=...)` creates `Clip(content=item, ...)` without copying
or changing the item. Time is in local seconds; starts are nonnegative.
Intervals include their start and exclude their end: `[start, end)`.

```python
from fframes.compose import Circle, Composition, Position, Tween

runner = Circle(
    radius=20,
    fill="#3776AB",
    position=Position(x=Tween(from_value=0, to_value=200, duration=2), y=40),
)
group = Composition(size=(320, 120), children=(runner.at(1, duration=2),))
scene = Composition(duration=6, children=(group.at(2, duration=3),))
```

Here the group is active at video times `[2, 5)`, and the circle at `[3, 5)`.
Its tween starts from zero at time 3. Each repeated occurrence gets its own local
clock. Calling `.at()` on an existing clip wraps it again: the delays add.

An omitted duration inherits the remaining parent interval. An explicit duration
caps content; it cannot extend the parent or stretch a child's animation. Static
graphics persist throughout their interval. Audio also stops at source EOF unless
looping. Content wholly outside the parent interval is skipped during compilation.

## Tweens and frame boundaries

`Tween(from_value=..., to_value=..., duration=..., easing="linear")` can replace
numeric `Position.x/y`, `opacity`, `rotation` or `scale`. It holds the final value
after its duration. Supported easing: `linear`, `ease_in`, `ease_out`, `ease_in_out`.
Geometry, dimensions and audio controls do not accept tweens. For animated paint
and frame counters, see [ColorTween and TextTemplate](graphics.md).

Visuals are sampled at `index / fps`; frame indices start at zero. A start between
frames first appears at the next frame, and the end is exclusive. The video frame
count rounds the root duration up to a whole frame; `video.duration` reports this
encoded duration. Content remains capped by the requested root interval, with
silence in any rounded audio tail.
