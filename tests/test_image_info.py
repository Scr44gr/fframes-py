import struct
import zlib
from pathlib import Path

import pytest

from fframes import Video, VideoConfig, probe_image


def test_image_dimensions_and_original_exif_date_are_read_from_the_container(
    tmp_path: Path,
) -> None:
    path = tmp_path / "image.png"
    Video(
        config=VideoConfig(width=8, height=4),
        frames=('<svg width="8" height="4"><rect width="8" height="4" fill="red"/></svg>',),
    ).save_png(path)
    plain = probe_image(path)
    assert (plain.width, plain.height, plain.exif) == (8, 4, ())
    # TIFF IFD0 points to an EXIF IFD containing DateTimeOriginal (ASCII).
    exif = (
        b"II\x2a\x00"
        + struct.pack("<I", 8)
        + struct.pack("<HHHIII", 1, 0x8769, 4, 1, 26, 0)
        + struct.pack("<HHHIII", 1, 0x9003, 2, 20, 44, 0)
        + b"2020:01:02 03:04:05\x00"
    )
    chunk = b"eXIf" + exif
    container = path.read_bytes()
    path.write_bytes(
        container[:33]
        + struct.pack(">I", len(exif))
        + chunk
        + struct.pack(">I", zlib.crc32(chunk))
        + container[33:]
    )
    result = probe_image(path)
    assert (result.width, result.height) == (8, 4)
    assert [(field.ifd, field.tag, field.value) for field in result.exif] == [
        (0, "DateTimeOriginal", "2020-01-02 03:04:05"),
    ]
    path.write_bytes(b"not an image")
    with pytest.raises(RuntimeError, match="ImageError"):
        probe_image(path)
