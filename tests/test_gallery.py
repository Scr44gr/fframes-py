from functools import cache
from pathlib import Path

import numpy as np
import pytest

from examples.pixel_memory import FPS, Gallery, Kind, curve
from fframes import ExifField, ImageInfo


class GalleryFixture(Gallery):
    @staticmethod
    @cache
    def info(path: Path) -> ImageInfo:
        return ImageInfo(
            width=640 if int(path.stem) % 2 else 480,
            height=480,
            exif=(ExifField(ifd=0, tag="DateTimeOriginal", value="2022-01-02 03:04:05"),),
        )


def test_seeded_gallery_consumes_each_photo_once_and_keeps_valid_frame_ranges() -> None:
    assets = {str(i): Path(f"{i:03}.jpg") for i in range(100, 180)}
    kinds: tuple[Kind, ...] = ("float", "fibonacci", "polaroid", "spiral", "parallax")
    a, b = GalleryFixture(assets, 48), GalleryFixture(dict(reversed(assets.items())), 48)
    used: set[Path] = set()
    for kind in kinds:
        first, second = a.shot(kind, 1.05), b.shot(kind, 1.05)
        assert first is not None
        assert second is not None
        assert first.duration > first.overlap >= 0
        assert [p.source for p in first.photos] == [p.source for p in second.photos]
        for photo, repeated in zip(first.photos, second.photos, strict=True):
            assert photo.source not in used
            used.add(photo.source)
            np.testing.assert_array_equal(photo.x, repeated.x)
            for values in (photo.x, photo.y, photo.scale, photo.rotation, photo.opacity):
                assert len(values) >= int(first.duration * FPS)
                assert np.isfinite(values).all()
            assert (photo.scale > 0).all()
            assert ((photo.opacity >= 0) & (photo.opacity <= 1)).all()
            if photo.development is not None:
                assert photo.year == "2022"
                assert photo.development[0] == 0
                assert photo.development[-1] == 1
        assert len(a.images) == len(assets) - len(used)
    with pytest.raises(ValueError, match="unused photos"):
        a.choose(len(a.images) + 1)


def test_negative_photo_preroll_is_sampled_at_the_scene_clock() -> None:
    values = curve(1, (-0.5, 0.5, 0, 10, "linear"))
    assert len(values) == FPS
    assert values[0] == 5
    assert values[FPS // 2] == values[-1] == 10
