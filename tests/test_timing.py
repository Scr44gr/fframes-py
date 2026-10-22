import pytest
from pydantic import ValidationError

import fframes as f
from fframes import compose as c


def test_scene_reports_include_nested_clipped_overlapping_and_reused_compositions() -> None:
    intro = c.Composition(name="Intro", duration=1)
    composition = c.Composition(
        name="Film",
        duration=3,
        children=(
            intro,
            c.Composition(name="Cut", duration=1, children=(intro.at(0.5),)).at(1),
            c.Composition(name="Tail", duration=2).at(2.5),
        ),
    )
    video = c.Video(resolution=(16, 16), fps=10, composition=composition).compile()
    timeline = video.timeline
    assert [(s.name, s.frames) for s in timeline.scenes] == [
        ("Film", (0, 30)),
        ("Intro", (0, 10)),
        ("Cut", (10, 20)),
        ("Intro", (15, 20)),
        ("Tail", (25, 30)),
    ]
    assert timeline.resolve_frame("Intro[1]@50%") == 17
    assert timeline.resolve_range("cut") == (10, 20)
    assert timeline.resolve_range("1s..2s") == (10, 20)
    assert timeline.resolve_frame("end") == 29
    assert [s.name for s in timeline.scenes_at(16)] == ["Film", "Cut", "Intro"]
    assert [s.name for s in timeline.scenes_at(20)] == ["Film"]
    with pytest.raises(ValueError, match="matches scenes"):
        timeline.resolve_frame("Intro")
    with pytest.raises(ValueError, match="available"):
        timeline.resolve_frame("missing")
    with pytest.raises(ValueError, match="outside"):
        timeline.scenes_at(30)
    raw = f.Video(
        config=f.VideoConfig(width=16, height=16, fps=10),
        frames=('<svg width="16" height="16"/>',) * 30,
        chapters=timeline.scenes,
    )
    assert raw.timeline == timeline


def test_timeline_rejects_empty_out_of_bounds_ranges_and_resolves_numeric_specs() -> None:
    with pytest.raises(ValidationError, match="start < end"):
        f.SceneRange(name="empty", frames=(3, 3))
    with pytest.raises(ValidationError, match="within"):
        f.TimelineIndex(
            fps=10, duration_in_frames=20, scenes=(f.SceneRange(name="long", frames=(0, 21)),)
        )
    timeline = f.TimelineIndex(fps=10, duration_in_frames=100)
    assert [timeline.resolve_frame(s) for s in ("12f", "1.2s", "0:01.2", "50%", "start")] == [
        12,
        12,
        12,
        50,
        0,
    ]
    assert timeline.resolve_range("50f..") == (50, 100)
    with pytest.raises(ValueError, match="empty"):
        timeline.resolve_range("50..20")
