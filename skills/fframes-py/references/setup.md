# Setup

Use a checkout or an existing wheel; do not assume the package is published on
PyPI. The distribution is `fframes-py`, the import is `fframes`. Supported Python
versions are 3.11–3.14; develop with 3.14. Keep versions in project manifests and
lockfiles rather than adding independent pins to generated scripts.

## In a checkout

Prepare the host before running uv:

| Host | Native requirements |
| --- | --- |
| Windows | Current Visual Studio C++ Build Tools (2022+) and SDK and LLVM; source `. ./scripts/setup-native.ps1` in the PowerShell session used to build/run. |
| Debian/Ubuntu | `build-essential clang libclang-dev libfontconfig1-dev nasm pkg-config`. |
| macOS | Xcode command-line tools, Homebrew `llvm nasm pkg-config`; set `LIBCLANG_PATH` to `$(brew --prefix llvm)/lib`. |

On Windows the setup script downloads FFmpeg 9 shared LGPL libraries and sets
`FFMPEG_DIR`, `PATH` and `LIBCLANG_PATH`. Its default LLVM path is
`C:\Program Files\LLVM\bin`; override that variable afterward if necessary.
Linux/macOS use the upstream portable FFmpeg build. Keep the native environment
in each shell that builds or runs the extension.

```sh
rustup show
uv python install 3.14
uv sync --locked --no-install-project
uv run --no-sync maturin develop --release --locked --uv
```

Run application scripts with `uv run --no-sync python path/to/script.py` in this
prepared environment. Repeat the Maturin command after Rust edits. Python-only
edits use the editable installation immediately.

## In a consumer project

Use `uv add --editable /absolute/path/to/fframes-py` with native build dependencies
prepared, or `uv add /absolute/path/to/package.whl` for a compatible wheel.
Windows wheel users still need matching FFmpeg DLLs: set `FFMPEG_DIR` to their
parent directory before importing fframes. A wheel does not require Rust to run.

For an import failure, inspect `fframes.__file__` when import succeeds, the active
Python/architecture, and the native library paths. Installing an unrelated
`ffmpeg` executable alone does not supply the matching DLLs or build headers.
The checkout's `docs/installation.md` has complete platform commands.
