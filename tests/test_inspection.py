from pathlib import Path

import pytest

import fframes
from fframes import compose
from fframes.inspection import NativeVideo


@pytest.fixture(params=["native", "compose"])
def video(request: pytest.FixtureRequest) -> NativeVideo:
    if request.param == "native":
        return fframes.compile_video(
            fframes.VideoConfig(width=64, height=64, fps=10),
            tuple(
                '<svg width="64" height="64"><rect width="64" height="64" fill="black"/>'
                + (
                    '<rect id="square" x="8" y="8" width="16" height="16" fill="white"/>'
                    if index >= 4
                    else ""
                )
                + "</svg>"
                for index in range(10)
            ),
        )
    return (
        compose.Video(
            resolution=(64, 64),
            fps=10,
            composition=compose.Composition(
                duration=1,
                children=(
                    compose.Rectangle(size=(64, 64)),
                    compose.Rectangle(
                        id="square",
                        size=(16, 16),
                        fill="#ffffff",
                        position=compose.Position(x=8, y=8),
                    ).at(0.4),
                ),
            ),
        )
        .compile()
        .native
    )


def test_inspection_preserves_requested_order_and_named_bounds(video: NativeVideo) -> None:
    reports = fframes.inspect_frames(video, (6, 0, 5))
    assert [report.frame for report in reports] == [6, 0, 5]
    assert reports[0].seconds == 0.6
    square = next(element for element in reports[0].elements if element.id == "square")
    assert (square.x, square.y, square.width, square.height) == (8, 8, 16, 16)
    assert not reports[1].elements
    with pytest.raises(IndexError, match="out of range"):
        fframes.inspect_frames(video, (len(video),))


def test_preview_crop_sheet_and_onion_dimensions(video: NativeVideo, tmp_path: Path) -> None:
    cropped = fframes.save_preview(
        video,
        tmp_path / "crop.png",
        frame=5,
        size=(128, 128),
        crop=(16, 16, 32, 32),
        labels=True,
    )
    info = fframes.probe_image(cropped)
    assert (info.width, info.height) == (32, 32)
    sheet = fframes.contact_sheet(video, tmp_path / "sheet.png", frames=(0, 5, 9), columns=2)
    info = fframes.probe_image(sheet)
    assert info.width >= 128
    assert info.height >= 128
    onion = fframes.contact_sheet(video, tmp_path / "onion.png", frames=(0, 5), onion=True)
    info = fframes.probe_image(onion)
    assert (info.width, info.height) == (64, 64)
    with pytest.raises(ValueError, match="crop"):
        fframes.save_preview(video, tmp_path / "bad.png", crop=(63, 0, 2, 1))
    with pytest.raises(ValueError, match=r"\.png"):
        fframes.save_preview(video, tmp_path / "bad.jpg")


def test_continuity_detects_local_step_at_original_frame(video: NativeVideo) -> None:
    pops = fframes.detect_pops(video, start=1)
    assert len(pops) == 1
    pop = pops[0]
    assert (pop.frame, pop.kind) == (4, "step")
    assert pop.x <= 8
    assert pop.y <= 8
    assert pop.x + pop.width >= 24
    assert pop.y + pop.height >= 24
    assert not fframes.detect_pops(video, start=5, size=(32, 32))
    with pytest.raises(IndexError, match="frame count"):
        fframes.detect_pops(video, start=5, end=11)


def test_empty_frame_has_actionable_diagnostic_and_duplicate_ids_fail() -> None:
    video = compose.Video(composition=compose.Composition(duration=1)).compile().native
    (report,) = fframes.inspect_frames(video)
    assert any(d.kind == "empty_frame" and d.message and d.key for d in report.diagnostics)
    square = compose.Rectangle(id="duplicate", size=(16, 16))
    with pytest.raises(ValueError, match=r"duplicate visual id.*unique id"):
        compose.Video(
            composition=compose.Composition(duration=1, children=(square, square))
        ).compile()
