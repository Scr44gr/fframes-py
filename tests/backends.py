"""Rasterizers exercised by shared rendering contracts."""

import os
import sys

import pytest

BACKENDS = (
    "cpu",
    "skia",
    pytest.param(
        "metal" if sys.platform == "darwin" else "vulkan",
        marks=pytest.mark.skipif(
            not os.environ.get("FFRAMES_TEST_3D_GPU"),
            reason="Set FFRAMES_TEST_3D_GPU for real GPU parity",
        ),
    ),
)
