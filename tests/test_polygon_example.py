from pathlib import Path

import pytest

from examples import low_poly
from examples.compose.low_poly import build as compose
from examples.native.low_poly import build as native


def test_pinned_polygon_extraction_preserves_order_geometry_and_color(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "bird.rs"
    source.write_text(
        '<polygon points="0,0 20,0 20,20" style="fill:rgb(12,128,255)"/>'
        '<polygon points="4,0 20,0 20,20" fill="rgb(255,64,8)"/>',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        low_poly,
        "files",
        lambda _name: {"art_popuga": source, "fredoka": Path(__file__).parent / "assets/Tuffy.ttf"},
    )
    a, b = native("popuga"), compose("popuga").compile()
    assert len(a) == len(b) == 900
    assert a.rgba(899) == b.rgba(899)
    assert a.rgba(0)[(2 * 1920 + 16) * 4 :][:4] == bytes.fromhex("ff4008ff")
    source.write_text('<polygon points="0,0" fill="unsupported"/>', encoding="utf-8")
    with pytest.raises(ValueError, match="polygon syntax"):
        low_poly.prepare("popuga")
