import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("guide", ["rendering", "analysis", "buffers", "timing"])
def test_documented_rendering_and_multiline_captions_execute(guide: str, tmp_path: Path) -> None:
    font = tmp_path / "tests" / "assets" / "Tuffy.ttf"
    font.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "tests" / "assets" / "Tuffy.ttf", font)
    blocks = re.findall(
        r"```python\n(.*?)\n```",
        (ROOT / "docs" / f"{guide}.md").read_text(encoding="utf-8"),
        re.S,
    )
    outputs: tuple[str, ...]
    if guide == "rendering":
        source = "\n\n".join(blocks)
        outputs = (
            "output/preview.png",
            "output/video.mp4",
            "output/excerpt.mp4",
            "output/scaled.mp4",
        )
    elif guide == "analysis":
        (tmp_path / "captions.vtt").write_text(
            "WEBVTT\n\n00:00.000 --> 00:01.000\nFirst line\nSecond line\n\n"
            "00:01.000 --> 00:01.000\nZero duration\n",
            encoding="utf-8",
        )
        source = (
            blocks[-1]
            + """
from fframes.compose import Video

video = Video(
    resolution=(320, 180),
    fonts=(Path("tests/assets/Tuffy.ttf"),),
    load_system_fonts=False,
    composition=Composition(duration=1, children=items),
)
compiled = video.compile()
compiled.save_png("captions.png")
"""
            + blocks[0]
            + "\nassert inspection.report.duration_seconds == 1\n"
        )
        outputs = ("captions.png",)
    else:
        source = "\n\n".join(blocks)
        source += (
            "\n" + ("compiled" if guide == "buffers" else "video") + '.save_png("preview.png")'
        )
        outputs = ("preview.png",)
    script = tmp_path / "example.py"
    script.write_text(source, encoding="utf-8")
    result = subprocess.run(  # noqa: S603 -- Execute repository-owned documentation with the real wheel.
        [sys.executable, str(script)], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert all((tmp_path / path).stat().st_size > 100 for path in outputs)
