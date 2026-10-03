from pathlib import Path
from typing import ClassVar

import pytest
from pydantic import ValidationError

from fframes import Video as RawVideo
from fframes import VideoConfig
from fframes.compose import (
    Circle,
    Close,
    Component,
    Composition,
    CubicTo,
    Image,
    LineTo,
    MoveTo,
    Position,
    Rectangle,
    RenderOptions,
    Stroke,
    Text,
    Tween,
    VectorPath,
    Video,
)
from fframes.compose.components import Item
from tests.container import box

FONT = Path(__file__).parent / "assets" / "Tuffy.ttf"


def pixel(data: bytes, x: int, y: int, width: int = 32) -> bytes:
    offset = (y * width + x) * 4
    return data[offset : offset + 4]


def video(*children: Item, duration: float = 3, fps: int = 10) -> Video:
    return Video(
        resolution=(32, 24),
        fps=fps,
        composition=Composition(duration=duration, children=children),
        load_system_fonts=False,
    )


def test_layer_order_alignment_and_inherited_duration() -> None:
    scene = video(
        Rectangle(size=(32, 24), fill="#FF0000"),
        Rectangle(size=(8, 4), position=Position(x="center", y="bottom"), fill="#0000FF"),
    ).compile()
    first, last = scene.rgba(), scene.rgba(len(scene) - 1)
    assert first == last
    assert pixel(first, 12, 20) == b"\x00\x00\xff\xff"
    assert pixel(first, 11, 20) == b"\xff\x00\x00\xff"
    assert pixel(first, 20, 20) == b"\xff\x00\x00\xff"


def test_nested_clips_rebase_animation_and_cap_the_parent_interval() -> None:
    moving = Rectangle(
        size=(4, 4),
        fill="#FF0000",
        position=Position(x=Tween(from_value=0, to_value=8, duration=1)),
    )
    group = Composition(
        size=(16, 8), position=Position(x=4, y=4), children=(moving.at(0.5, duration=2),)
    )
    scene = video(group.at(1, duration=1), group.at(2, duration=0.8)).compile()
    assert not any(scene.rgba(14))
    assert pixel(scene.rgba(15), 4, 4) == b"\xff\x00\x00\xff"
    assert pixel(scene.rgba(19), 8, 4) == b"\xff\x00\x00\xff"
    assert not any(scene.rgba(20))
    assert scene.rgba(15) == scene.rgba(25)
    assert not any(scene.rgba(28))


def test_adjacent_decimal_intervals_have_no_extra_or_missing_frame() -> None:
    scene = video(
        Rectangle(size=(32, 24), fill="#FF0000").at(0.1 + 0.2, duration=0.3),
        Rectangle(size=(32, 24), fill="#0000FF").at(0.6, duration=0.2),
        duration=0.8,
    ).compile()
    colors = [scene.rgba(index)[:4] for index in range(len(scene))]
    assert colors == [bytes(4)] * 3 + [b"\xff\x00\x00\xff"] * 3 + [b"\x00\x00\xff\xff"] * 2


def test_group_opacity_is_applied_after_children_overlap() -> None:
    scene = video(
        Composition(
            opacity=0.5,
            children=(
                Rectangle(size=(12, 8), fill="#FF0000"),
                Rectangle(size=(12, 8), position=Position(x=4), fill="#FF0000"),
            ),
        )
    ).compile()
    pixels = scene.rgba()
    assert pixel(pixels, 2, 2) == pixel(pixels, 6, 2) == b"\xff\x00\x00\x80"


def test_nested_transforms_use_local_coordinates_and_group_centers() -> None:
    scene = video(
        Composition(
            size=(8, 4),
            position=Position(x=8, y=8),
            rotation=90,
            scale=2,
            children=(Rectangle(size=(8, 4), fill="#0000FF"),),
        )
    ).compile()
    pixels = scene.rgba()
    assert pixel(pixels, 12, 3) == pixel(pixels, 12, 17) == b"\x00\x00\xff\xff"
    assert pixel(pixels, 7, 10) == pixel(pixels, 16, 10) == bytes(4)


def test_custom_component_expands_once_and_compiled_session_is_independent(tmp_path: Path) -> None:
    class Badge(Component):
        calls: ClassVar[list[str]] = []
        color: str

        def compose(self) -> Composition:
            self.calls.append(self.color)
            return Composition(children=(Circle(radius=4, fill=self.color),))

    badge = Badge(color="#00FF00")
    first, second = badge.at(0, duration=0.5), badge.at(1, duration=0.5)
    description = video(first, second, duration=1.5)
    compiled = description.compile()
    assert first.content is second.content is badge
    assert compiled.rgba(0) == compiled.rgba(10)
    compiled.render(tmp_path / "reuse.mp4", options=RenderOptions(concurrency=2))
    assert Badge.calls == ["#00FF00"]
    # A fresh compilation re-evaluates authoring code; compiled sessions never do.
    description.compile()
    assert Badge.calls == ["#00FF00", "#00FF00"]


def test_component_cycle_fails_before_native_rendering() -> None:
    class Recursive(Component):
        def compose(self) -> Composition:
            return Composition(children=(self,))

    with pytest.raises(ValueError, match="cycle"):
        video(Recursive()).compile()


def test_unsupported_base_item_is_not_silently_dropped() -> None:
    with pytest.raises(TypeError, match="subclass Component"):
        video(Item()).compile()


def test_clips_outside_parent_do_not_load_invisible_assets(tmp_path: Path) -> None:
    scene = video(Image(source=tmp_path / "absent.png", size=(4, 4)).at(3)).compile()
    assert not any(scene.rgba())


def test_typed_path_paints_curves_and_strokes() -> None:
    path = VectorPath(
        size=(8, 8),
        position=Position(x=4, y=4),
        fill="#00FF00",
        stroke=Stroke(color="#FF0000", width=2),
        segments=(
            MoveTo(x=0, y=0),
            LineTo(x=8, y=0),
            CubicTo(control1=(8, 2), control2=(8, 6), end=(8, 8)),
            LineTo(x=0, y=8),
            Close(),
        ),
    )
    pixels = video(path).rgba()
    assert pixel(pixels, 8, 8) == b"\x00\xff\x00\xff"
    assert pixel(pixels, 4, 8) == b"\xff\x00\x00\xff"


def test_unfilled_shape_keeps_its_interior_transparent() -> None:
    pixels = video(Circle(radius=8, fill=None, stroke=Stroke(color="#00FF00", width=2))).rgba()
    assert pixel(pixels, 8, 8) == bytes(4)
    assert pixel(pixels, 8, 0)[3] > 200


def test_explicit_font_centers_shaped_text_and_accepts_xml_characters() -> None:
    text = Text(
        content="<Rust> & Python",
        font_family="Tuffy",
        font_size=12,
        position=Position(x="center", y="center"),
    )
    scene = Video(
        composition=Composition(duration=1, children=(text,)),
        resolution=(128, 48),
        fonts=(FONT,),
        load_system_fonts=False,
    ).compile()
    pixels = scene.rgba()
    points = [(i % 128, i // 128) for i, alpha in enumerate(pixels[3::4]) if alpha]
    assert len(points) > 150
    xs, ys = zip(*points, strict=True)
    assert (min(xs) + max(xs) + 1) / 2 == pytest.approx(64, abs=1)
    assert (min(ys) + max(ys) + 1) / 2 == pytest.approx(24, abs=1)


def test_missing_fonts_and_media_are_reported_at_compile_time(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires a font"):
        video(Text(content="Hello")).compile()
    with pytest.raises(FileNotFoundError):
        video(Image(source=tmp_path / "missing.png", size=(4, 4))).compile()


def test_explicit_fonts_are_owned_after_compilation(tmp_path: Path) -> None:
    font = tmp_path / "font.ttf"
    font.write_bytes(FONT.read_bytes())
    scene = Video(
        composition=Composition(duration=1, children=(Text(content="Rust", font_size=12),)),
        resolution=(64, 32),
        fonts=(font,),
        load_system_fonts=False,
    ).compile()
    font.unlink()
    assert any(scene.rgba())


def test_invalid_explicit_font_is_not_silently_ignored(tmp_path: Path) -> None:
    font = tmp_path / "invalid.ttf"
    font.write_bytes(b"not a font")
    with pytest.raises(ValueError, match="invalid font file"):
        Video(composition=Composition(duration=1), fonts=(font,), load_system_fonts=False).compile()


def test_parallel_export_keeps_frame_count_and_timestamps(tmp_path: Path) -> None:
    destination = tmp_path / "output.mp4"
    destination.write_bytes(b"old")
    description = video(
        Circle(radius=4, position=Position(x=Tween(from_value=0, to_value=20, duration=3))),
        duration=3,
        fps=30,
    )
    description.render(destination, options=RenderOptions(concurrency=4))
    media = box(box(box(destination.read_bytes(), b"moov"), b"trak"), b"mdia")
    timing = box(media, b"mdhd")
    duration = int.from_bytes(timing[16:20], "big") / int.from_bytes(timing[12:16], "big")
    samples = box(box(box(media, b"minf"), b"stbl"), b"stsz")
    assert int.from_bytes(samples[8:12], "big") == 90
    assert duration == pytest.approx(3)
    assert not list(tmp_path.glob("fframes-py-*"))


def test_image_assets_are_owned_after_compile_and_preserve_alpha(tmp_path: Path) -> None:
    source = tmp_path / "image.png"
    RawVideo(
        config=VideoConfig(width=8, height=8),
        frames=('<svg width="8" height="8"><rect width="4" height="8" fill="red"/></svg>',),
    ).save_png(source)
    image = Image(source=source, size=(8, 8))
    scene = video(
        image,
        Composition(position=Position(x=16), children=(image,)),
    ).compile()
    source.unlink()
    pixels = scene.rgba()
    assert pixel(pixels, 1, 4) == pixel(pixels, 17, 4) == b"\xff\x00\x00\xff"
    assert pixel(pixels, 6, 4) == pixel(pixels, 22, 4) == bytes(4)


@pytest.mark.parametrize("easing", ["linear", "ease_in", "ease_out", "ease_in_out"])
def test_animated_opacity_holds_its_endpoint(easing: str) -> None:
    # Validate external configuration through the public schema, preserving strict typing.
    tween = Tween.model_validate(
        {"from_value": 0.0, "to_value": 1.0, "duration": 1.0, "easing": easing}
    )
    scene = video(Rectangle(size=(4, 4), opacity=tween)).compile()
    assert scene.rgba(0)[:4] == bytes(4)
    assert 0 < scene.rgba(5)[3] < 255
    assert scene.rgba(10)[:4] == scene.rgba(20)[:4] == b"\x00\x00\x00\xff"


def test_root_duration_rounding_and_png_preview(tmp_path: Path) -> None:
    description = video(Rectangle(size=(4, 4)), duration=0.26)
    assert len(description) == 3
    assert description.duration == 0.3
    path = description.save_png(tmp_path / "frame.png", index=2)
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    compiled = description.compile()
    with pytest.raises(IndexError, match="out of range"):
        compiled.rgba(3)
    with pytest.raises(ValidationError):
        compiled.rgba(-1)
    with pytest.raises(ValueError, match=r"\.png"):
        compiled.save_png(tmp_path / "frame.jpg")


@pytest.mark.parametrize("encoder", ["no_such_encoder", "mpeg4"])
def test_failed_export_preserves_destination_and_cleans_segments(
    tmp_path: Path, encoder: str
) -> None:
    path = tmp_path / "existing.webm"
    path.write_bytes(b"original")
    with pytest.raises(RuntimeError):
        video(Rectangle(size=(4, 4)), duration=0.1).render(
            path, options=RenderOptions(encoder=encoder, concurrency=1)
        )
    assert path.read_bytes() == b"original"
    assert sorted(tmp_path.iterdir()) == [path]


def test_invalid_composition_contracts_fail_during_construction() -> None:
    with pytest.raises(ValidationError, match="root composition requires duration"):
        Video(composition=Composition())
    with pytest.raises(ValidationError, match="opacity"):
        Rectangle(size=(4, 4), opacity=Tween(from_value=0, to_value=2, duration=1))
    with pytest.raises(ValidationError, match="scale"):
        Composition(scale=Tween(from_value=1, to_value=0, duration=1))
    with pytest.raises(ValidationError, match="MoveTo"):
        VectorPath(size=(8, 8), segments=(LineTo(x=0, y=0), Close()))
    with pytest.raises(ValidationError, match="duration"):
        Circle(radius=4).at(0, duration=0)
