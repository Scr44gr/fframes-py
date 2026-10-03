# Development

- Use uv; keep `uv.lock` and `Cargo.lock` committed. Develop with the newest stable
  Python 3.14 patch while preserving Python 3.11–3.14 compatibility.
- Check official documentation and published releases before choosing or changing
  dependencies or GitHub Actions. Do not infer current APIs from training data.
- Target full feature parity with upstream fframes, including GPU shaders and
  synchronized video clips. Add missing bindings rather than simplify or omit
  upstream examples to fit the wrapper's current limitations.
- Expose engine capabilities through `fframes` and composable equivalents through
  `fframes.compose`, sharing native implementations. Verify parity against a
  recorded upstream version or commit on each supported backend and platform.
- Use Pydantic v2 for public input validation. Keep models immutable and reuse
  validation schemas between the low-level and Pythonic APIs.
- Keep expensive operations and batch loops in Rust; release the GIL for native
  work. Do not add Python callbacks to rendering without measuring the cost.
- Use concrete types throughout Python, stubs and tests. No `Any`, unknown types,
  dynamic `getattr`/`setattr`, or blanket type-checker suppressions.
- Keep filenames descriptive and short. Share implementations instead of copying
  upstream redundancy. Document unavoidable adaptations to upstream internals.
- Keep the Python package in `src/fframes/` and native Rust sources in `rust/`.
- Keep the README short and example driven. State actual supported capabilities.
- Before delivery run Ruff lint/format, mypy, pytest with coverage, cargo fmt,
  clippy and cargo test. Rendering tests must use the real compiled extension.
- Test installed wheels on Linux, Windows and macOS with all supported Python
  versions. Preserve a single platform matrix and stable-ABI wheel reuse.
- Do not claim remote CI passed unless it ran. Native FFmpeg dependencies and
  Python coverage versus native coverage must remain explicit.
