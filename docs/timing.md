# Named timeline queries

[Index](index.md)

Name compositions to query their compiled, visible frame intervals. Names may
repeat and intervals may overlap. Nested intervals are clipped by their parents.

```python
from fframes import RenderOptions
from fframes.compose import Composition, Text, Video

video = Video(
    composition=Composition(
        duration=3,
        children=(
            Composition(name="Intro", duration=1, children=(Text(content="Hello"),)),
            Composition(name="Detail", duration=2).at(1),
        ),
    )
).compile()
timeline = video.timeline
assert timeline.resolve_range("Detail") == (30, 90)
options = RenderOptions(frame_range=timeline.resolve_range("Detail"))
```

`fframes.Video(chapters=(SceneRange(name="Intro", frames=(0, 30)), ...))`
supplies the same information for SVG sequences. `inspect_timeline(video.native)`
works with either compiled API. It returns fps, duration and named ranges without
rendering. `TimelineIndex(...)` also works independently.

| Selector | Meaning |
| --- | --- |
| `12`, `12f` | Zero-based frame 12. |
| `1.2s`, `0:01.2` | Original timeline timestamp. |
| `50%`, `start`, `end` | Whole-video position; `end` is its last frame. |
| `Intro`, `#0` | Scene name (case-insensitive) or declaration index. |
| `Intro[1]` | Second occurrence of that name. |
| `Intro@50%`, `Intro@0.2s` | Position within a scene. |

`resolve_frame(spec)` returns one index. `resolve_range("a..b")` returns an
end-exclusive pair; omitted endpoints mean the timeline boundary. A scene alone
selects its whole interval; a scene on the right of `..` supplies its end.
Selectors follow upstream clamping rules. Explicit `RenderOptions.frame_range`
bounds are validated, not clamped. Ambiguous names raise an error with selectors
for disambiguation. `scenes_at(frame)` returns all active ranges.
