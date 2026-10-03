import pytest
from pydantic import ValidationError

import fframes
from fframes import Keyframe, Timeline, _native
from fframes.models import BasicEasing


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
def test_easing_matches_css_reference(easing: BasicEasing) -> None:
    curve = Timeline(keyframes=(Keyframe(start=0, end=1, from_value=0, to_value=1, easing=easing),))
    expected = {"linear": 0.5, "ease_in": 0.31536, "ease_out": 0.68464, "ease_in_out": 0.5}
    assert curve.sample(15) == pytest.approx(expected[easing], abs=1e-3)
    assert curve.sample(0) == pytest.approx(0)
    assert curve.sample(30) == pytest.approx(1)


def test_compiled_animation_uses_the_same_engine(timeline: Timeline) -> None:
    native: fframes.Animation = fframes.compile_animation(timeline.keyframes)
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
        fframes.compile_animation((Keyframe(start=1e10, end=1e10 + 1, from_value=0, to_value=1),))


def test_native_boundary_rejects_invalid_keyframes() -> None:
    with pytest.raises(ValueError, match="at least one"):
        _native.compile_animation([])
    with pytest.raises(ValueError, match="unsupported easing"):
        _native.compile_animation([(0, 1, 0, 1, "typo")])


def test_color_keyframes_preserve_upstream_rgba_rounding_and_holds() -> None:
    color = fframes.compile_color_animation(
        (
            fframes.ColorKeyframe(start=1, end=2, from_value="#FF000000", to_value="#0000FFFF"),
            fframes.ColorKeyframe(start=3, end=4, from_value="#0000FF", to_value="#FFFFFF"),
        )
    )
    indices = (150, 45, 0, 75, 105)
    expected = ["#FFFFFFFF", "#7F007F7F", "#FF000000", "#0000FFFF", "#7F7FFFFF"]
    assert color.sample_many(indices, 30) == expected
    assert [color.sample(i, 30) for i in indices] == expected
    assert color.sample_many((), 30) == []
    with pytest.raises(ValueError, match="fps"):
        color.sample_many([0], 0)


def test_color_keyframes_validate_intervals_and_native_colors() -> None:
    with pytest.raises(ValidationError, match="overlap"):
        fframes.compile_color_animation(
            (
                fframes.ColorKeyframe(start=0, end=2, from_value="#000000", to_value="#FFFFFF"),
                fframes.ColorKeyframe(start=1, end=3, from_value="#000000", to_value="#FFFFFF"),
            )
        )
    with pytest.raises(ValueError, match="color"):
        _native.compile_color_animation([(0, 1, "invalid", "#FFFFFF", "linear")])


def test_custom_bezier_matches_named_upstream_curve() -> None:
    bezier = fframes.CubicBezier(x1=0.42, y1=0, x2=0.58, y2=1)
    curve = fframes.compile_animation(
        (Keyframe(start=0, end=2, from_value=0, to_value=1, easing=bezier),)
    )
    reference = fframes.compile_animation(
        (Keyframe(start=0, end=2, from_value=0, to_value=1, easing="ease_in_out"),)
    )
    assert curve.sample_many(range(61), 30) == reference.sample_many(range(61), 30)


def test_spring_uses_elapsed_seconds_and_retains_physical_overshoot() -> None:
    from fframes import compose

    spring = fframes.Spring()
    tween = fframes.Tween(from_value=0, to_value=16, start_at=0.2, duration=1.8, easing=spring)
    curve = fframes.compile_animation(
        (Keyframe(start=0.2, end=2, from_value=0, to_value=16, easing=spring),)
    )
    samples = curve.sample_many(range(60), 30)
    assert max(samples) > 16
    assert samples[-1] == pytest.approx(16)
    scene = compose.Video(
        resolution=(32, 8),
        fps=30,
        load_system_fonts=False,
        composition=compose.Composition(
            duration=2,
            children=(
                compose.Rectangle(size=(4, 8), fill="#ff0000", position=compose.Position(x=tween)),
            ),
        ),
    ).compile()
    reference = fframes.compile_video(
        fframes.VideoConfig(width=32, height=8),
        tuple(
            '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="8">'
            f'<rect x="{x}" width="4" height="8" fill="red"/></svg>'
            for x in samples
        ),
    )
    for index in (0, 6, 9, 12, 18, 59):
        assert scene.rgba(index) == reference.rgba(index)
    with pytest.raises(ValidationError, match="opacity"):
        compose.Rectangle(
            size=(1, 1), opacity=fframes.Tween(from_value=0, to_value=1, duration=1, easing=spring)
        )
    with pytest.raises(ValidationError, match=r"settling|stiffness/mass"):
        fframes.Spring(mass=1e-20)
    critical = fframes.Tween(
        from_value=0, to_value=1, duration=1, easing=fframes.Spring(damping=100)
    )
    assert compose.Rectangle(size=(1, 1), opacity=critical).opacity == critical
