---
name: fframes-py
description: Create, edit, render and debug Python videos with fframes-py, using reusable compose components or direct SVG and scalar animation. Use for fframes-py scenes, layer timing, audio mixing, native setup and output verification.
---

# fframes-py

Turn the user's scene into typed Python descriptions and render with the installed
fframes-py package. Keep authored content and output settings separate. This skill
covers the Python wrapper; upstream Rust examples may expose unavailable features.
When porting an upstream example in this checkout, consult `docs/examples.md`
for paired ports and gaps. Fetch pinned assets explicitly with
`python -m examples.assets <name>`; rendering must work from the verified cache.

## Select only the references needed

| Task | Read |
| --- | --- |
| Install, rebuild, or resolve native import failures | [Setup](references/setup.md) |
| Author components, arrange layers, or animate a scene | [Composition](references/composition.md) |
| Add shader layers, masks or filters | [Shaders and effects](references/shaders.md) |
| Configure images, fonts, sound and exported video | [Media and rendering](references/media.md) |
| Render existing SVG or sample numeric keyframes | [Low level](references/lowlevel.md) |
| Check correctness, performance, or reported failures | [Verification](references/verification.md) |

## Working rules

1. Use `fframes.compose` for object-based scenes. Choose `fframes` when
   inputs are already SVG frames or scalar keyframes. Do not confuse the two
   `Video` classes; `RenderOptions` is shared.
2. Establish duration, resolution, fps and available assets from the task. Choose
   reasonable defaults for unspecified preferences and report material assumptions.
3. Use frozen, typed Pydantic inputs and tuple collections. Keep Python work in
   scene construction; compile once before repeated previews or exports.
4. Preview meaningful frames and check the final output using the verification
   reference. Report the produced file and any checks that could not run.

These references are self-contained for the current public API. In a checkout,
use `docs/index.md` for full examples and inspect public definitions when behavior
differs. With an installed package, inspect its version and public signatures.
Use `_native.pyi` only to understand native return-object methods; do not build
consumer code on `_native` or the private compiler plan. Before changing
dependencies, read their current official documentation and the project's lockfiles.
