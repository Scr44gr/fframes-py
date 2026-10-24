---
name: fframes-py
description: Create, edit, render and debug videos using fframes-py. Covers compose components, SVG, 3D scenes, model animation, textures, shaders, Lottie, clips, audio effects and output verification through the public Python API.
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
| Build 3D scenes, animate models or put video on a mesh | [3D scenes](references/three-d.md) |
| Play a Lottie animation or use it as a texture | [Lottie](references/lottie.md) |
| Configure images, fonts, sound and exported video | [Media and rendering](references/media.md) |
| Supply generated PCM/pixels or query named scenes | [Buffers and timelines](references/buffers.md) |
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
4. Establish framing, lighting and layer order with a small preview before a full
   export. Inspect consecutive frames around transitions, not just isolated stills.
   Use the verification reference and report checks that could not run.

The references are self-contained. If behavior differs, check the installed
version and public signatures before changing application code.
