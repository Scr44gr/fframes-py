# Verification and performance

Choose checks that address the changed behavior. A successful constructor or an
output filename alone does not prove a rendered scene is correct.

## Scene delivery

- Compile once and inspect PNGs at the first frame, a meaningful middle frame,
  and around changed clip boundaries. Confirm ordering, alignment, text and alpha.
- For audio changes, inspect the native mix at silence/overlap/fade boundaries
  and listen to the encoded result when playback is available. AAC is lossy;
  compare decoded levels/timing with tolerances, not byte equality.
- Check the final file's streams, dimensions, fps and duration. If a matching
  FFmpeg CLI is available, use `ffprobe -v error -show_streams -show_format output.mp4`.
  Report unverified playback or platform behavior explicitly.
- For application tests, render a small scene with the real package. Assert
  meaningful pixels, audible intervals or frame boundaries; constructor success
  alone does not test the result. Use explicit fonts for reproducible text.

## Diagnose cost before changing the design

Measure scene construction/compilation separately from rendering. Reuse a compiled
scene for repeated outputs; use native batch sampling for many scalar values.
Prefer groups, tweens and precomputed samples over repeated Python calls per
frame. For NumPy analysis, view returned buffers with `frombuffer`; allocate
only when writable data is needed. `Samples` takes owned values, not a shared view.

Account for full decoded media, materialized audio loops, and per-worker render
resources. Tune concurrency by measurement. A scene that exceeds memory needs
smaller assets or a revised sequence. Audio is decoded in full; video files are
decoded by rendering workers and must stay available until rendering ends.
