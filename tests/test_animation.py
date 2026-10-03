import pytest
from fframes import Keyframe, Timeline, _native, lowlevel
from fframes.models import Easing
from pydantic import ValidationError


@pytest.fixture
def timeline() -> Timeline:
    return Timeline(
        keyframes=(
            Keyframe(start=1, end=2, from_value=10, to_value=20),
            Keyframe(start=3, end=4, from_value=20, to_value=0),
        )
    )


def test_upstream_interpolation_holds_and_boundaries(timeline: Timeline) -> None:
    expected = [10, 10, 15, 20, 20, 20, 10, 0, 0]
    indices = (0, 30, 45, 60, 75, 90, 105, 120, 150)
    assert timeline.sample_many(indices, fps=30) == pytest.approx(expected)
    assert [timeline.sample(i, fps=30) for i in indices] == pytest.approx(expected)
    assert timeline.native is timeline.native
    assert timeline.sample_many(()) == []


@pytest.mark.parametrize("easing", ["linear", "ease_in", "ease_out", "ease_in_out"])
def test_easing_matches_css_reference(easing: Easing) -> None:
    curve = Timeline(keyframes=(Keyframe(start=0, end=1, from_value=0, to_value=1, easing=easing),))
    expected = {"linear": 0.5, "ease_in": 0.31536, "ease_out": 0.68464, "ease_in_out": 0.5}
    assert curve.sample(15) == pytest.approx(expected[easing], abs=1e-3)
    assert curve.sample(0) == pytest.approx(0)
    assert curve.sample(30) == pytest.approx(1)


def test_lowlevel_compilation_uses_the_same_engine(timeline: Timeline) -> None:
    native = lowlevel.compile_animation(timeline.keyframes)
    assert native.sample_many([0, 45, 90], 30) == [10, 15, 20]


def test_invalid_sample_arguments_are_rejected(timeline: Timeline) -> None:
    with pytest.raises(ValidationError):
        timeline.sample(-1)
    with pytest.raises(ValidationError):
        timeline.sample(1, fps=0)
    with pytest.raises(ValidationError):
        timeline.sample_many([1, -1])
    with pytest.raises(ValueError, match="fps"):
        timeline.native.sample(0, 0)
    with pytest.raises(ValueError, match="fps"):
        timeline.native.sample_many([0], 0)


def test_native_boundary_checks_float32_precision() -> None:
    with pytest.raises(ValueError, match="positive duration"):
        lowlevel.compile_animation((Keyframe(start=1e10, end=1e10 + 1, from_value=0, to_value=1),))


def test_native_boundary_rejects_invalid_keyframes() -> None:
    with pytest.raises(ValueError, match="at least one"):
        _native.compile_animation([])
    with pytest.raises(ValueError, match="unsupported easing"):
        _native.compile_animation([(0, 1, 0, 1, "typo")])
