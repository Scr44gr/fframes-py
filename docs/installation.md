# Installation

[Index](index.md)

## Use a wheel

Install a wheel matching your OS and architecture with `uv add /path/to/package.whl`
or `python -m pip install /path/to/package.whl`, replacing the path with its actual
filename. This guide does not assume a published PyPI release. Once published,
use `uv add fframes-py` or `python -m pip install fframes-py`.

A wheel needs no Rust compiler. Repaired Windows wheels include the FFmpeg DLLs;
neither `FFMPEG_DIR` nor a separate FFmpeg executable is required for rendering.
The `cp311-abi3` wheel supports Python 3.11–3.14 on its platform.

## Build from source

The remaining commands run from a checkout of this repository. Install
[uv](https://docs.astral.sh/uv/getting-started/installation/) and
[Rust through rustup](https://www.rust-lang.org/tools/install), then prepare the
native dependencies **before** building the Python extension.
The checked-in manifests and lockfiles define the dependency versions.

## Native dependencies

### Windows

Install current Visual Studio Build Tools (2022 or newer) with **Desktop development with C++**, its
Windows SDK, and LLVM. Use 64-bit Python and matching native libraries.
In the PowerShell session that will build or run the package:

```powershell
. ./scripts/setup-native.ps1
```

The script downloads the FFmpeg 9 LGPL shared build into `.native/`, sets
`FFMPEG_DIR`, adds its `bin` to `PATH`, and sets `LIBCLANG_PATH` to
`C:\Program Files\LLVM\bin`. Override the latter after sourcing the script if
LLVM is installed elsewhere. The script does not install the compiler or LLVM.

For an editable installation or an unrepaired wheel, keep `FFMPEG_DIR` set at
runtime too: importing fframes registers `$env:FFMPEG_DIR\bin` as a DLL search
directory. This directory must exist. Distributed wheels bundle these DLLs
through Maturin's configured repair step.

### Linux (Debian/Ubuntu)

```sh
sudo apt-get update
sudo apt-get install -y build-essential clang libclang-dev libfontconfig1-dev nasm patchelf pkg-config ffmpeg
```

### macOS

Install the Xcode command-line tools (`xcode-select --install`), then:

```sh
brew install llvm nasm pkg-config ffmpeg
export LIBCLANG_PATH="$(brew --prefix llvm)/lib"
```

On Linux/macOS, run this in the same Bash session before building:

```bash
source ./scripts/setup-openh264.sh
```

It installs a pinned, checksum-verified OpenH264 static library under `.native/`
and exports `PKG_CONFIG_PATH`. Upstream's `build-portable` feature then builds or
downloads FFmpeg with OpenH264 enabled. The first build needs network access and
can take time. The FFmpeg CLI supplies `ffprobe` and decoding checks for tests;
it is not the library linked into the extension.
The CI native setup is maintained in
[the composite action](../.github/actions/native/action.yml).

## Build the development environment

```sh
rustup show
uv python install 3.14
uv sync --locked --no-install-project
uv run --no-sync maturin develop --release --locked --uv
uv run --no-sync python -m examples.compose.composition
```

`rustup show` installs the toolchain selected by `rust-toolchain.toml` if needed.
The sync installs development dependencies; Maturin builds and installs the
extension into `.venv`. `--no-sync` keeps later commands from replacing that build.
The example writes a preview, a generated tone and a video under `output/compose/composition/`.

## Use it from another uv project

After preparing native dependencies, add the checkout as a dependency:

```sh
uv add --editable /absolute/path/to/fframes-py
```

Use your actual checkout path, quoted if it contains spaces. This builds the
extension from source and needs the native environment described above.

## If setup fails

| Symptom | Check |
| --- | --- |
| `DLL load failed` importing `_native` | Check wheel/interpreter architecture. For an editable install or externally linked wheel, check `FFMPEG_DIR` and its `bin`. |
| libclang cannot be found | Point `LIBCLANG_PATH` at the directory containing the libclang library. |
| Unresolved `__std_*` symbols linking Skia | Update the C++ toolset and use its developer shell; old 2019 STL libraries cannot link current Skia binaries. |
| Missing linker or C headers | Install the platform's compiler/SDK listed above. |
| Rust edits have no effect | Re-run the Maturin command; editable Python imports do not rebuild Rust. |

See [uv projects](https://docs.astral.sh/uv/guides/projects/) and
[Maturin local development](https://www.maturin.rs/local_development) for the tools'
own environment behavior.
