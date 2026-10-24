# Inspect a video

[Index](index.md)

These functions take `fframes.Video.native` or `compose.Video.compile().native`.
They use the compiled assets and renderer, with native batch work and no Python
frame callbacks.

```python
import fframes
from fframes import compose

video = (
    compose.Video(
        resolution=(640, 360),
        composition=compose.Composition(
            duration=2, children=(compose.Rectangle(id="panel", size=(200, 120), fill="#3288ff"),)
        ),
    )
    .compile()
    .native
)

reports = fframes.inspect_frames(video, (0, 15, 59))
fframes.save_preview(video, "detail.png", frame=15, crop=(0, 0, 320, 180), labels=True)
fframes.contact_sheet(video, "sheet.png", frames=(0, 15, 30, 59), columns=2)
pops = fframes.detect_pops(video)
```

| Function | Result |
| --- | --- |
| `inspect_frames` | Ordered frame reports: named element bounds and typed diagnostics. |
| `save_preview` | PNG, optionally resized, labelled and then cropped. |
| `contact_sheet` | Labelled grid; `onion=True` overlays the selected frames. |
| `detect_pops` | Local steps/flashes and their regions, scanning consecutive frames in constant memory. |

Frame indices are zero-based. Crop coordinates refer to the requested preview
`size`, not the original canvas. A pop's region likewise refers to the inspection
resolution; its frame remains an original video index. Pop detection excludes
whole-frame cuts and is a review cue, not an error verdict.

Use unique `id` values on compose visuals or SVG elements to identify layers.
Reports inspect SVG structure, not the contents of raster images or 3D meshes.
Check actual rendered frames for occlusion, font fallback, texture sharpness,
lighting and camera framing. Inspect consecutive frames around transitions;
widely spaced snapshots can miss brief defects. Listen separately to audio and
verify encoded stream metadata with `ffprobe`.
