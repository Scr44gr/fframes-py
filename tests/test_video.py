import struct
from pathlib import Path

import pytest
from fframes import RenderOptions, Video, VideoConfig, _native, lowlevel
from pydantic import ValidationError

SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="12">'
    '<rect width="8" height="12" fill="red"/></svg>'
)


def box(data: bytes, kind: bytes) -> bytes:
    offset = 0
    while offset + 8 <= len(data):
        size = int.from_bytes(data[offset : offset + 4], "big")
        assert size >= 8
        if data[offset + 4 : offset + 8] == kind:
            return data[offset + 8 : offset + size]
        offset += size
    raise AssertionError(f"Missing MP4 box: {kind!r}")


@pytest.fixture
def video() -> Video:
    return Video(config=VideoConfig(width=16, height=12, fps=24), frames=(SVG,) * 24)


def test_real_rasterization_and_alpha(video: Video) -> None:
    pixels = video.rgba()
    assert len(pixels) == 16 * 12 * 4
    assert pixels[:4] == bytes((255, 0, 0, 255))
    assert pixels[8 * 4 : 9 * 4] == bytes(4)
    assert len(video) == len(video.native) == 24
    assert video.duration == 1
    assert video.native is video.native


def test_straight_rgba_unpremultiplies_alpha() -> None:
    video = Video(
        config=VideoConfig(width=16, height=12),
        frames=(SVG.replace('fill="red"', 'fill="red" opacity="0.5"'),),
    )
    assert video.rgba()[:4] == bytes((255, 0, 0, 128))


def test_png_contains_requested_dimensions(video: Video, tmp_path: Path) -> None:
    path = tmp_path / "frame.png"
    assert video.save_png(str(path), index=12) == path
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", data[16:24]) == (16, 12)


def test_render_encodes_real_video(video: Video, tmp_path: Path) -> None:
    path = tmp_path / "movie.mp4"
    assert video.render(path, options=RenderOptions(concurrency=2)) == path
    data = path.read_bytes()
    assert data[4:8] == b"ftyp"
    assert b"moov" in data
    assert b"mdat" in data
    assert len(data) > 500
    track = box(box(data, b"moov"), b"trak")
    header = box(track, b"tkhd")
    assert int.from_bytes(header[-8:-4], "big") >> 16 == 16
    assert int.from_bytes(header[-4:], "big") >> 16 == 12
    media = box(track, b"mdia")
    timing = box(media, b"mdhd")
    assert timing[0] == 0  # Version 0 stores 32-bit time fields.
    timescale = int.from_bytes(timing[12:16], "big")
    duration = int.from_bytes(timing[16:20], "big") / timescale
    samples = box(box(box(media, b"minf"), b"stbl"), b"stsz")
    count = int.from_bytes(samples[8:12], "big")
    assert count == len(video)
    assert duration == pytest.approx(video.duration)
    assert count / duration == video.config.fps


def test_lowlevel_video_uses_validated_inputs(tmp_path: Path) -> None:
    native = lowlevel.compile_video(VideoConfig(width=16, height=12), (SVG,))
    assert native.rgba(0)[:4] == bytes((255, 0, 0, 255))
    assert lowlevel.render(native, tmp_path / "lowlevel.mp4").is_file()


@pytest.mark.parametrize("index", [24, 25, 2**40])
def test_frame_index_outside_video(video: Video, index: int) -> None:
    with pytest.raises(IndexError, match="out of range"):
        video.rgba(index)


def test_invalid_svg_is_reported() -> None:
    video = Video(frames=("<svg>",))
    with pytest.raises(ValueError, match=r".+"):
        video.rgba()


@pytest.mark.parametrize("path", ["", "no-extension", "file\0.png"])
def test_invalid_paths(video: Video, path: str) -> None:
    with pytest.raises(ValidationError):
        video.save_png(path)
    with pytest.raises(ValidationError):
        video.render(path)


def test_wrong_image_extension(video: Video, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"\.png"):
        video.save_png(tmp_path / "image.jpg")


def test_write_errors_are_propagated(video: Video, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        video.save_png(tmp_path / "missing" / "frame.png")
    with pytest.raises(FileNotFoundError):
        video.render(tmp_path / "missing" / "movie.mp4")


def test_encoder_errors_are_propagated(video: Video, tmp_path: Path) -> None:
    path = tmp_path / "movie.mp4"
    path.write_bytes(b"existing file")
    with pytest.raises(RuntimeError):
        video.render(path, options=RenderOptions(encoder="no_such_encoder"))
    assert path.read_bytes() == b"existing file"
    assert not list(tmp_path.glob("fframes-py-*"))


def test_unsupported_container(video: Video, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="container"):
        video.render(tmp_path / "video.invalid")


def test_incompatible_encoder_does_not_leak_files(video: Video, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="incompatible"):
        video.render(tmp_path / "video.webm")
    assert not list(tmp_path.iterdir())


def test_invalid_svg_mid_render_cleans_up(tmp_path: Path) -> None:
    video = Video(config=VideoConfig(width=16, height=12), frames=(SVG, "<svg>"))
    with pytest.raises(RuntimeError):
        video.render(tmp_path / "video.mp4")
    assert not list(tmp_path.iterdir())


def test_native_destination_failure_does_not_crash(video: Video, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        video.native.render(tmp_path / "missing" / "movie.mp4", tmp_path, "mpeg4", 1)


def test_successful_render_replaces_existing_file(video: Video, tmp_path: Path) -> None:
    path = tmp_path / "movie.mp4"
    path.write_bytes(b"old")
    video.render(path)
    assert path.read_bytes()[4:8] == b"ftyp"
    assert not list(tmp_path.glob("fframes-py-*"))


def test_odd_dimensions_can_rasterize_but_not_encode(tmp_path: Path) -> None:
    video = Video(config=VideoConfig(width=15, height=11), frames=(SVG,))
    assert len(video.rgba()) == 15 * 11 * 4
    with pytest.raises(ValueError, match="even"):
        video.render(tmp_path / "odd.mp4")


def test_native_boundary_rejects_invalid_inputs(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="dimensions"):
        _native.compile_video(0, 1, 30, [SVG], False)
    with pytest.raises(ValueError, match="dimensions"):
        _native.compile_video(1, 1, 30, [], False)
    native = lowlevel.compile_video(VideoConfig(width=16, height=12), (SVG,))
    with pytest.raises(ValueError, match="concurrency"):
        native.render(tmp_path / "movie.mp4", tmp_path, "mpeg4", 0)


def test_system_font_loading_is_optional() -> None:
    video = Video(config=VideoConfig(width=16, height=12, load_system_fonts=True), frames=(SVG,))
    assert video.rgba()[:4] == bytes((255, 0, 0, 255))
