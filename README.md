<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/logo-dark.svg" />
    <img alt="fframes-py" src="docs/assets/logo.svg" width="440" />
  </picture>
</p>

<p align="center">
  <b>The power of <a href="https://github.com/dmtrKovalenko/fframes">fframes</a>, made simple in Python.</b>
</p>

<p align="center">
  <a href="docs/index.md">Documentation</a> ·
  <a href="examples/composition.py">Example</a> ·
  <a href="skills/fframes-py/SKILL.md">Agent skill</a>
</p>

## Quick start

```sh
pip install fframes-py
```

Or with uv:

```sh
uv add fframes-py
```

Render a three-second title card:

```python
from fframes.compose import Composition, Position, Rectangle, Text, Tween, Video

video = Video(
    resolution=(1280, 720),
    fps=30,
    composition=Composition(
        duration=3,
        children=(
            Rectangle(size=(1280, 720), fill="#172033"),
            Text(
                content="Hello, frames",
                position=Position(x="center", y="center"),
                font_size=64,
                fill="#FFD43B",
                opacity=Tween(from_value=0, to_value=1, duration=1),
            ),
        ),
    ),
)
video.render("hello.mp4")
```

Text uses system fonts; supply [font files](docs/rendering.md#fonts) for reproducible
layout. For repeated previews or exports, reuse `video.compile()`.

## Low level

Render a one-second sequence of SVG frames:

```python
import fframes

svg = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360">'
    '<rect width="640" height="360" fill="#3776AB"/></svg>'
)
native = fframes.compile_video(fframes.VideoConfig(width=640, height=360, fps=30), (svg,) * 30)
fframes.render(native, "frames.mp4")
```

See [low-level operations](docs/lowlevel.md) for scalar animation and frame sampling.
