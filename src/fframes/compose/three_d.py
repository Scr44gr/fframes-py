"""Place a native 3D scene among ordinary composable visual layers."""

from typing import Literal

from fframes.compose.components import Visual
from fframes.three_d import Renderer


class Scene3D(Visual):
    """A 3D image with 2D placement, clipping, filters and compositing."""

    kind: Literal["scene3d"] = "scene3d"
    renderer: Renderer
