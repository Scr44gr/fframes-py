# Installation

[Index](index.md)

Install with one of:

```sh
uv add fframes-py
python -m pip install fframes-py
```

The distribution is `fframes-py`; import `fframes`. Wheels support Python
3.11–3.14 on their OS/architecture without a Rust compiler. Repaired Windows
wheels include FFmpeg DLLs; rendering needs no separate FFmpeg executable.

In a uv project, prefix Python commands with `uv run`. To install a supplied
wheel, replace `fframes-py` with its actual path.

## Runtime requirements

Start with `backend="cpu"` for graphics or `"skia"` for shaders without a GPU.
Vulkan/Metal need suitable drivers; see [backends](rendering.md#backends).
Install NumPy separately only if using the array-analysis examples.

If `_native` fails to import, check the interpreter and wheel architecture.
Externally linked builds also need matching native libraries; the
[build guide](building.md#troubleshooting) covers those environments.
Installing an unrelated FFmpeg executable does not repair missing extension DLLs.
