import shutil
import subprocess
from pathlib import Path

import pytest

import fframes
from examples.compose import three_d as composed
from examples.native import three_d as native


def test_nested_monitor_examples_match_and_encode_motion_across_workers(tmp_path: Path) -> None:
    svg = native.build(size=(64, 36))
    typed = composed.build(size=(64, 36)).compile()
    assert len(svg) == len(typed) == 90
    for frame in (0, 45, 89):
        assert svg.rgba(frame) == typed.rgba(frame)
    assert typed.rgba(0) != typed.rgba(45)
    ffmpeg = shutil.which("ffmpeg")
    assert ffmpeg is not None
    decoded = []
    for workers in (1, 3):
        path = tmp_path / f"monitor-{workers}.mp4"
        typed.render(path, options=fframes.RenderOptions(concurrency=workers, color_matrix="bt709"))
        info = fframes.probe_video(path)
        assert (info.width, info.height, info.fps) == (64, 36, 30)
        assert info.duration == pytest.approx(3)
        decoded.append(
            subprocess.run(  # noqa: S603 -- Decode the known temporary render, without a shell.
                [ffmpeg, "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                capture_output=True,
                check=True,
            ).stdout
        )
    assert len(decoded[0]) == 90 * 64 * 36 * 4
    assert decoded[0] == decoded[1]
