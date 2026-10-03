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
- For an export-failure fix, check that an existing destination survives and
  temporary segments disappear. Keep scratch output in a temporary directory.

## Library changes

In the repository, follow `AGENTS.md` and `docs/development.md`. Rebuild native
edits before pytest. Exercise the real extension: assert representative pixels,
frame/sample boundaries, decoded output or meaningful error recovery. Avoid
tests that repeat defaults or mock the rendering behavior under examination.

Run Ruff, mypy, pytest with the configured coverage gate, cargo fmt, Clippy and
Rust tests. Installed-wheel tests must use the wheel's `site-packages`, not an
editable checkout. The platform matrix covers Python 3.11–3.14 on Linux, macOS
and Windows; local success alone does not establish the other platforms. Python
coverage does not measure native code.

## Diagnose cost before changing the design

Measure scene construction/compilation separately from rendering. Reuse a compiled
scene for repeated outputs; use native batch sampling for many scalar values.
Prefer groups and tweens over repeated Python calls per frame. Keep heavy loops
in Rust and preserve GIL release for native work. Use direct typed attributes;
do not introduce `Any`, dynamic `getattr`/`setattr`, or duplicated validation.

Account for full decoded media, materialized audio loops, and per-worker render
resources. Tune concurrency by measurement. A scene that exceeds memory needs
smaller assets or a revised sequence; the current API is not a streaming renderer.
