from typing import Annotated

import pytest
from pydantic import ConfigDict, Field, ValidationError, field_validator
from pydantic_core import PydanticCustomError

from fframes.compose import Component, Composition, Position, Rectangle, Video


class Tile(Component):
    side: Annotated[float, Field(gt=0)] = 16

    def compose(self) -> Composition:
        return Composition(
            size=(self.side, self.side),
            children=(Rectangle(size=(self.side, self.side), fill="#00FF00"),),
        )


@pytest.mark.parametrize(
    ("field", "value", "example", "x", "y", "alpha"),
    [
        ("position", Position(x=24, y=24), "Position(x=24, y=24)", 24, 24, 255),
        ("scale", 0.5, "0.5", 4, 4, 255),
        ("opacity", 0.5, "0.5", 0, 0, 128),
    ],
)
def test_component_error_explains_and_renders_the_wrapper_correction(
    field: str, value: Position | float, example: str, x: int, y: int, alpha: int
) -> None:
    with pytest.raises(ValidationError) as caught:
        Tile.model_validate({field: value})
    (error,) = caught.value.errors()
    assert error["type"] == "extra_forbidden"
    assert error["loc"] == (field,)
    assert f"'{field}' belongs on a Composition wrapper" in error["msg"]
    assert "Tile is a Component that describes content, not a visual layer" in error["msg"]
    assert f"Composition(children=(component,), {field}={example})" in error["msg"]

    corrected = Composition.model_validate({"size": (16, 16), "children": (Tile(),), field: value})
    pixels = Video(
        resolution=(64, 64),
        load_system_fonts=False,
        composition=Composition(duration=1, children=(corrected,)),
    ).rgba()
    offset = (y * 64 + x) * 4
    assert pixels[offset : offset + 4] == bytes((0, 255, 0, alpha))
    assert sum(pixels[3::4]) == (64 if field == "scale" else 256) * alpha


def test_placement_guidance_preserves_other_errors_and_reports_all_misplaced_fields() -> None:
    with pytest.raises(ValidationError) as caught:
        Tile.model_validate({"side": -1, "position": None, "scale": 0, "opacity": 0, "typo": 1})
    errors = {error["loc"]: error for error in caught.value.errors()}
    assert set(errors) == {("side",), ("position",), ("scale",), ("opacity",), ("typo",)}
    assert errors[("side",)]["type"] == "greater_than"
    assert errors[("side",)]["ctx"] == {"gt": 0.0}
    assert errors[("typo",)]["msg"] == "Extra inputs are not permitted"
    for field in ("position", "scale", "opacity"):
        assert f"'{field}' belongs on a Composition wrapper" in errors[(field,)]["msg"]


def test_declared_component_fields_keep_their_validation_and_are_not_auto_transforms() -> None:
    class ScaledTile(Tile):
        factor: float = Field(alias="scale")

        @field_validator("factor")
        @classmethod
        def positive_factor(cls, value: float) -> float:
            if value <= 0:
                raise PydanticCustomError(
                    "positive_factor", "factor must exceed {minimum}", {"minimum": 0}
                )
            return value

    tile = ScaledTile(scale=0.5)
    assert tile.factor == 0.5
    assert tile.compose().scale == 1
    assert ScaledTile.model_validate(tile) is tile
    with pytest.raises(ValidationError) as caught:
        ScaledTile.model_validate({"scale": 0, "opacity": 0.5})
    errors = caught.value.errors()
    assert errors[0]["loc"] == ("scale",)
    assert errors[0]["type"] == "positive_factor"
    assert errors[0]["msg"] == "factor must exceed 0"
    assert errors[0]["ctx"] == {"minimum": 0}
    assert "Composition" in errors[1]["msg"]
    with pytest.raises(ValidationError, match="factor must exceed 0"):
        ScaledTile(scale=0)


def test_nested_extra_fields_do_not_receive_component_placement_guidance() -> None:
    class PositionedTile(Tile):
        origin: Position

    with pytest.raises(ValidationError) as caught:
        PositionedTile.model_validate({"origin": {"opacity": 0.5}, "opacity": 0.5})
    nested, outer = caught.value.errors()
    assert nested["loc"] == ("origin", "opacity")
    assert nested["msg"] == "Extra inputs are not permitted"
    assert "Composition" in outer["msg"]


def test_placement_guidance_respects_hidden_inputs() -> None:
    class PrivateTile(Tile):
        model_config = ConfigDict(hide_input_in_errors=True)

    with pytest.raises(ValidationError) as caught:
        PrivateTile.model_validate({"position": "confidential coordinates"})
    assert "Composition" in str(caught.value)
    assert "confidential coordinates" not in str(caught.value)
