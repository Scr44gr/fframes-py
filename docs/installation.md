# Installation

[Index](index.md)

The commands below run from a checkout of this repository. Install
[uv](https://docs.astral.sh/uv/getting-started/installation/) and
[Rust through rustup](https://www.rust-lang.org/tools/install), then prepare the
native dependencies **before** building the Python extension.
The checked-in manifests and lockfiles define the dependency versions.

## Native dependencies

### Windows

Install Visual Studio Build Tools with **Desktop development with C++**, its
Windows SDK, and LLVM. Use 64-bit Python and matching native libraries.
In the PowerShell session that will build or run the package:

```powershell
. ./scripts/setup-native.ps1
```

The script downloads the FFmpeg 9 LGPL shared build into `.native/`, sets
`FFMPEG_DIR`, adds its `bin` to `PATH`, and sets `LIBCLANG_PATH` to
`C:\Program Files\LLVM\bin`. Override the latter after sourcing the script if
LLVM is installed elsewhere. The script does not install the compiler or LLVM.

Keep `FFMPEG_DIR` set at runtime too: importing fframes registers
`$env:FFMPEG_DIR\bin` as a DLL search directory. This directory must exist.
The Windows wheels built here currently depend on these external FFmpeg DLLs.

### Linux (Debian/Ubuntu)

```sh
sudo apt-get update
sudo apt-get install -y build-essential clang libclang-dev nasm pkg-config
```

### macOS

Install the Xcode command-line tools (`xcode-select --install`), then:

```sh
brew install llvm nasm pkg-config
export LIBCLANG_PATH="$(brew --prefix llvm)/lib"
```

On Linux/macOS the enabled upstream `build-portable` feature builds/downloads
FFmpeg dependencies. The first build needs network access and can take time.
The CI native setup is maintained in
[the composite action](../.github/actions/native/action.yml).

## Build the development environment

```sh
rustup show
uv python install 3.14
uv sync --locked --no-install-project
uv run --no-sync maturin develop --release --locked --uv
uv run --no-sync python -m examples.composition
```

`rustup show` installs the toolchain selected by `rust-toolchain.toml` if needed.
The sync installs development dependencies; Maturin builds and installs the
extension into `.venv`. `--no-sync` keeps later commands from replacing that build.
The example writes a preview, a generated tone and a video under `output/composition/`.

## Use it from another uv project

After preparing native dependencies, add the checkout as a dependency:

```sh
uv add --editable /absolute/path/to/fframes-py
```

Use your actual checkout path, quoted if it contains spaces. This builds the
extension from source. Alternatively, use `uv add /absolute/path/to/package.whl`
with a wheel built for your OS and architecture. This guide does not assume a
published PyPI release. A wheel install does not require the Rust compiler;
Windows still needs the runtime DLL configuration above.

## If setup fails

| Symptom | Check |
| --- | --- |
| `DLL load failed` importing `_native` | Set `FFMPEG_DIR` before starting Python; check its `bin` and architecture. |
| libclang cannot be found | Point `LIBCLANG_PATH` at the directory containing the libclang library. |
| Missing linker or C headers | Install the platform's compiler/SDK listed above. |
| Rust edits have no effect | Re-run the Maturin command; editable Python imports do not rebuild Rust. |

See [uv projects](https://docs.astral.sh/uv/guides/projects/) and
[Maturin local development](https://www.maturin.rs/local_development) for the tools'
own environment behavior.
