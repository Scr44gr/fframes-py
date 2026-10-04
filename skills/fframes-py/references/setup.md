# Consumer setup

The distribution is `fframes-py`; import `fframes`. Use Python 3.11–3.14 and a
wheel matching the operating system and architecture. A wheel needs no Rust
toolchain. Check release availability before assuming a PyPI installation works.

For a published release, choose one:

```sh
uv add fframes-py
python -m pip install fframes-py
```

If supplied a wheel instead, pass its actual path to either command. Quote paths
containing spaces. The `abi3` wheel tagged `cp311` also serves Python 3.12–3.14.
Use `uv run python scene.py` in a uv project, or the interpreter where pip
installed the package. Install NumPy separately only if the application uses it.

## Check an installation

```sh
python -c "import fframes; from importlib.metadata import version; print(version('fframes-py'), fframes.__file__)"
```

Run this with the same interpreter used for the scene (`uv run python` for uv).
If imports fail, check the interpreter, wheel architecture and native runtime
dependencies supplied with the release. Bundled Windows wheels include FFmpeg
DLLs. An externally linked wheel needs matching DLLs: set `FFMPEG_DIR` to the
directory containing their `bin` before starting Python. Installing an unrelated
FFmpeg executable does not provide compatible libraries.

Start with `backend="cpu"` for shapes and text, or `"skia"` for shaders without
a GPU. See [shaders](shaders.md) for GPU backends and [media](media.md) for fonts,
assets and codec selection.
