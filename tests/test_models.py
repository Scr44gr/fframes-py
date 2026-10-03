import math

import pytest
from fframes import Keyframe, RenderOptions, Timeline, Video, VideoConfig
from pydantic import ValidationError


@pytest.mark.parametrize("field", ["width", "height", "fps"])
@pytest.mark.parametrize("value", [0, -1, True, 1.5, "30", 2**31])
def test_config_rejects_invalid_integers(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        VideoConfig.model_validate({field: value})


def test_models_are_frozen_and_forbid_extra_fields() -> None:
    config = VideoConfig()
    with pytest.raises(ValidationError, match="frozen"):
        config.width = 10  # type: ignore[misc]  # Exercise runtime rejection of a frozen field.
    with pytest.raises(ValidationError, match="extra_forbidden"):
        VideoConfig.model_validate({"typo": 10})
    assert VideoConfig.model_validate_json(config.model_dump_json()) == config


@pytest.mark.parametrize("value", [math.inf, -math.inf, math.nan])
@pytest.mark.parametrize("field", ["start", "end", "from_value", "to_value"])
def test_keyframes_require_finite_values(field: str, value: float) -> None:
    data = {"start": 0.0, "end": 1.0, "from_value": 0.0, "to_value": 10.0, field: value}
    with pytest.raises(ValidationError):
        Keyframe.model_validate(data)


@pytest.mark.parametrize("end", [0, -1])
def test_keyframe_requires_positive_duration(end: int) -> None:
    with pytest.raises(ValidationError):
        Keyframe(start=0, end=end, from_value=0, to_value=1)


def test_timeline_requires_ordered_nonoverlapping_keyframes() -> None:
    first = Keyframe(start=0, end=2, from_value=0, to_value=1)
    second = Keyframe(start=1, end=3, from_value=1, to_value=2)
    with pytest.raises(ValidationError, match="overlap"):
        Timeline(keyframes=(first, second))
    with pytest.raises(ValidationError):
        Timeline(keyframes=())


def test_interpolation_cannot_overflow() -> None:
    with pytest.raises(ValidationError, match="range must be finite"):
        Keyframe(start=0, end=1, from_value=-1e308, to_value=1e308)


@pytest.mark.parametrize("frames", [(), ("",), (12,), (None,)])
def test_video_requires_nonempty_strings(frames: tuple[object, ...]) -> None:
    with pytest.raises(ValidationError):
        Video.model_validate({"frames": frames})


@pytest.mark.parametrize("encoder", ["", "bad\0name", "mpeg4 --flag"])
def test_encoder_rejects_invalid_names(encoder: str) -> None:
    with pytest.raises(ValidationError):
        RenderOptions(encoder=encoder)
