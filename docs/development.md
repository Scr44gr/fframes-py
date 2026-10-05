# Development

[Index](index.md)

Follow [installation](installation.md) first. Python lives in `src/fframes/`,
Rust in `rust/`, and executable usage examples in `examples/`. Read `AGENTS.md`
for repository conventions; consumer code should use the public namespaces.

## Build and check

Python-only edits are visible through the editable install. After Rust changes:

```sh
uv run --no-sync maturin develop --release --locked --uv
```

With native dependencies configured in the current shell:

```sh
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync mypy
uv run --no-sync pytest
cargo fmt --check
cargo clippy --locked --all-targets --all-features -- -D warnings
cargo test --locked
```

Pytest uses the real extension and enforces 95% Python branch-aware coverage;
this is not Rust coverage. Prefer tests of pixels, clip boundaries, audio samples,
decodable output and failure cleanup over assertions that repeat model defaults.
Use explicit test fonts for reproducible text checks.

## Configuration ownership

| File | Maintains |
| --- | --- |
| `pyproject.toml` | Python compatibility, dependencies, Maturin, Ruff, mypy, pytest and coverage. |
| `uv.lock` | Resolved Python dependencies; update through uv. |
| `Cargo.toml`, `Cargo.lock` | Native dependency constraints, resolved crates and ABI feature. |
| `.python-version`, `rust-toolchain.toml` | Development interpreter line and Rust toolchain. |
| `.github/actions/native/action.yml` | Shared OS dependency installation. |
| `.github/workflows/ci.yml` | Platform builds and installed-wheel tests on Python 3.11–3.14. |
| `.github/workflows/release.yml` | Version-tag validation and PyPI publishing after the shared CI passes. |

Ruff targets Python 3.11, including annotations, imports, readability and docstrings;
mypy runs in strict mode with the Pydantic plugin. Keep concrete types through the
Python/native boundary. Do not add per-frame Python callbacks or duplicate raw
validation in compose. Review official release notes before dependency or action
upgrades; update lockfiles rather than embedding versions throughout the docs.

## Distribution and CI

```sh
uv build --no-sources --wheel --out-dir dist
uv build --no-sources --sdist --out-dir dist
```

PyO3 uses `abi3-py311`: one wheel per OS/architecture can serve the supported
CPython versions. CI builds once on each of Linux, macOS and Windows, then installs
those wheels for Python 3.11–3.14. Preserve this shared matrix rather than duplicating
workflow configuration. Check actual CI results before claiming platform success.
See [releases](releases.md) for versioning and the one-time PyPI configuration.

On Linux, Rust test executables link to Python's shared library. If `cargo test`
cannot find `libpython`, expose the selected interpreter's library directory:

```sh
export PYO3_PYTHON="$(uv python find)"
python_lib=$(uv run --no-sync python -c 'import sysconfig; print(sysconfig.get_config_var("LIBDIR"))')
export LD_LIBRARY_PATH="$python_lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
```

Maturin's [repair setting](https://www.maturin.rs/config) bundles external native
libraries, including FFmpeg DLLs on Windows. Test jobs install only FFmpeg CLI
inspection tools, without setting `FFMPEG_DIR` or build-library search paths.
`ffprobe` checks the actual output codec/pixel format and `ffmpeg` decodes the
whole video; both executables must be on `PATH` when running pytest locally.

Connect the repository in Codecov to enable the coverage badge. CI uploads the
Linux/Python 3.14 report using [OIDC](https://github.com/codecov/codecov-action#using-oidc)
(`id-token: write`); no `CODECOV_TOKEN` secret is needed. `codecov.yml` maps installed
package paths to `src/fframes/`. Windows wheels contain a generated DLL loader that
shifts source lines, so their reports stay in CI artifacts. Every OS/Python pair
still runs the full tests and enforces 95% coverage. Upload errors do not fail CI
while Codecov is being configured.

To test a wheel locally, create a separate uv environment, install pytest,
pytest-cov and NumPy plus the exact wheel path, and run that environment's Python with
`-m pytest`. Check `fframes.__file__` points into that environment's `site-packages`,
not the editable checkout. Test with build-machine library paths removed.

The Cargo include list packages `docs/` in the source distribution. The project
skill lives separately in `skills/fframes-py`; neither it nor personal installed
skills are Python runtime dependencies.
