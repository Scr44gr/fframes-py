from pathlib import Path

import pytest
from pydantic import ValidationError

from fframes import Font, TextLayout

FONT = Path(__file__).parent / "assets/Tuffy.ttf"


def test_native_metrics_fit_unicode_and_wrap_without_losing_words(tmp_path: Path) -> None:
    source = tmp_path / "font.ttf"
    source.write_bytes(FONT.read_bytes())
    layout = TextLayout(fonts=(source,))
    font = Font(family="Tuffy", size=24)
    a, space, full = layout.widths(("hello", " ", "hello world"), font)
    source.unlink()
    assert layout.width("hello ", font) == a + space
    assert layout.wrap("hello world\nnew line", font, full) == ("hello world", "new line")
    assert layout.wrap("hello world", font, a) == ("hello", "world")
    assert layout.fit("hello world", font, full) == "hello world"
    assert layout.fit("héllo 日本 world", font, a).endswith("…")
    assert layout.width(layout.fit("héllo 日本 world", font, a), font) <= a
    assert layout.fit("hello world", font, 1) == ""
    assert layout.fit("hello world", font, a, marker="") == "hello"
    with pytest.raises(ValueError, match="font family"):
        layout.width("hello", Font(family="missing-family"))


def test_layout_inputs_fail_before_native_work() -> None:
    with pytest.raises(ValidationError):
        Font(family="Tuffy", size=0)
    with pytest.raises(ValidationError):
        TextLayout().wrap("hello", Font(family="Tuffy"), 0)
