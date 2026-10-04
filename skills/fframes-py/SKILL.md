---
name: fframes-py
description: Create, edit, render and debug videos in Python applications using fframes-py. Use for reusable compose components, SVG sequences, layer timing, shaders, clips, audio mixing and output verification. Covers the public wrapper API and consumer installation.
---

# fframes-py

Create scenes using the installed `fframes-py` package. Keep authored content and
output settings separate. Use the public Python API described here; an upstream
Rust example does not establish that an equivalent Python method exists.

## Select only the references needed

| Task | Read |
| --- | --- |
| Install the package or diagnose import failures | [Setup](references/setup.md) |
| Arrange layers, draw shapes or animate a scene | [Composition](references/composition.md) |
| Reuse a typed scene element across placements | [Components](references/components.md) |
| Add shader layers, masks or filters | [Shaders and effects](references/shaders.md) |
| Configure images, fonts, sound and exported video | [Media and rendering](references/media.md) |
| Analyze audio or place captions | [Analysis](references/analysis.md) |
| Render existing SVG or sample numeric keyframes | [Low level](references/lowlevel.md) |
| Check correctness, performance, or reported failures | [Verification](references/verification.md) |

## Working rules

1. Use `fframes.compose` for object-based scenes. Choose `fframes` when
   inputs are already SVG frames or scalar keyframes. Do not confuse the two
   `Video` classes; `RenderOptions` is shared.
2. Establish duration, resolution, fps and available assets from the task. Choose
   reasonable defaults for unspecified preferences and report material assumptions.
3. Use typed inputs and tuple collections. Keep Python work in scene construction;
   compile once before repeated previews or exports.
4. Preview meaningful frames and check the final output using the verification
   reference. Report the produced file and any checks that could not run.

The references are self-contained. If behavior differs, check the installed
version and public signatures before changing application code.
