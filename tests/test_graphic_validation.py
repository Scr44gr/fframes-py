import pytest
from pydantic import ValidationError

from fframes import Font, Spring
from fframes.compose import Circle, Rectangle, Samples, Text, TextRun, Tween
from fframes.values import Scalar


@pytest.mark.parametrize("axis", [0, 1], ids=["width", "height"])
@pytest.mark.parametrize(
    "extent",
    [
        0,
        -1,
        10_000_001,
        Tween(from_value=0, to_value=16, duration=1),
        Tween(from_value=16, to_value=0, duration=1),
        Samples(values=(1, 0, 1), fps=30),
        Tween(from_value=16, to_value=1, duration=1, easing=Spring(damping=1)),
    ],
    ids=["zero", "negative", "too_large", "from_zero", "to_zero", "zero_sample", "undershoot"],
)
def test_rectangle_rejects_nonpositive_or_oversized_extents_with_a_reveal_alternative(
    axis: int, extent: Scalar
) -> None:
    with pytest.raises(ValidationError) as caught:
        Rectangle(size=(extent, 16) if axis == 0 else (16, extent))
    (error,) = caught.value.errors()
    assert error["loc"] == ("size",)
    assert f"Rectangle.size[{axis}]" in error["msg"]
    assert ("width" if axis == 0 else "height") in error["msg"]
    assert "greater than 0 and at most 10000000 throughout animation" in error["msg"]
    assert "opacity=Tween(from_value=0, to_value=1, duration=1)" in error["msg"]


def test_circle_allows_zero_but_rejects_a_negative_tween_endpoint() -> None:
    assert Circle(radius=0).radius == 0
    with pytest.raises(ValidationError, match="circle radius must stay between 0 and 10000000"):
        Circle(radius=Tween(from_value=0, to_value=-1, duration=1))


@pytest.mark.parametrize("weight", [100, 450, 700, 900])
def test_font_weights_share_the_integer_contract_across_layout_and_graphics(weight: int) -> None:
    assert Font(family="sans-serif", weight=weight).weight == weight
    assert Text(content="Label", font_weight=weight).font_weight == weight
    assert TextRun(content="Label", font_weight=weight).font_weight == weight


@pytest.mark.parametrize("weight", ["bold", "700", 700.0, True, 99, 901])
def test_font_weights_reject_names_coercion_and_out_of_range_values(
    weight: str | float | int | bool,
) -> None:
    with pytest.raises(ValidationError, match="weight"):
        Font.model_validate({"family": "sans-serif", "weight": weight})
    with pytest.raises(ValidationError, match="font_weight"):
        Text.model_validate({"content": "Label", "font_weight": weight})
    with pytest.raises(ValidationError, match="font_weight"):
        TextRun.model_validate({"content": "Label", "font_weight": weight})
