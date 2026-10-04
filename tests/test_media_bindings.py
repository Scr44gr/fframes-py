from pathlib import Path
from typing import Literal

import pytest

import fframes
from fframes import compose
from tests.test_composition_audio import RATE, write_audio


def colored_clip(path: Path, colors: tuple[str, ...], fps: int = 4) -> Path:
    video = fframes.Video(
        config=fframes.VideoConfig(width=16, height=16, fps=fps),
        frames=tuple(
            '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">'
            f'<rect width="16" height="16" fill="{color}"/></svg>'
            for color in colors
        ),
    )
    return video.render(path, options=fframes.RenderOptions(concurrency=2))


@pytest.mark.parametrize("fit", ["contain", "cover"])
def test_media_fitting_preserves_aspect_ratio_for_images_and_clips(
    tmp_path: Path,
    fit: Literal["contain", "cover"],
) -> None:
    clip = colored_clip(tmp_path / "source.mp4", ("red", "blue"))
    image = compose.Video(
        resolution=(16, 16),
        load_system_fonts=False,
        composition=compose.Composition(
            duration=1, children=(compose.Rectangle(size=(16, 16), fill="#ff0000"),)
        ),
    ).save_png(tmp_path / "source.png")
    for visual in (
        compose.Image(source=image, size=(32, 16), fit=fit),
        compose.VideoClip(source=clip, size=(32, 16), fit=fit),
    ):
        scene = compose.Video(
            resolution=(32, 16),
            load_system_fonts=False,
            composition=compose.Composition(duration=1, children=(visual,)),
        ).compile()
        pixels = scene.rgba(0)
        assert pixels[(8 * 32 + 16) * 4] >= 250
        assert pixels[(8 * 32) * 4 + 3] == (0 if fit == "contain" else 255)


def test_video_clips_keep_local_time_loop_offset_and_seek_order(tmp_path: Path) -> None:
    source = colored_clip(tmp_path / "source.mp4", ("red", "lime", "blue", "yellow"))
    info = fframes.probe_video(source)
    assert (info.width, info.height, info.fps, info.duration) == (16, 16, 4, 1)
    native = fframes.Video(
        config=fframes.VideoConfig(width=16, height=16, fps=4),
        frames=(
            '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">'
            '<image href="video:clip" width="16" height="16"/></svg>',
        )
        * 8,
        clips=(
            fframes.VideoBinding(
                name="clip", source=source, offset=0.25, loop=True, start_at=0.25, duration=1.5
            ),
        ),
    )
    composed = compose.Video(
        resolution=(16, 16),
        fps=4,
        load_system_fonts=False,
        composition=compose.Composition(
            duration=2,
            children=(
                compose.VideoClip(source=source, size=(16, 16), offset=0.25, loop=True).at(
                    0.25, duration=1.5
                ),
            ),
        ),
    ).compile()
    for i, rgb in (
        (0, (0, 0, 0)),
        (1, (0, 255, 0)),
        (3, (255, 255, 0)),
        (4, (0, 255, 0)),
        (2, (0, 0, 255)),
        (6, (255, 255, 0)),
        (7, (0, 0, 0)),
    ):
        a, b = native.rgba(i), composed.rgba(i)
        assert a == b
        assert a[:3] == pytest.approx(rgb, abs=3)
    # Exercise persistent worker-local decoder caches and mux all frames.
    for result in (
        native.render(tmp_path / "native.mp4", options=fframes.RenderOptions(concurrency=2)),
        composed.render(tmp_path / "compose.mp4", options=fframes.RenderOptions(concurrency=2)),
    ):
        assert fframes.probe_video(result).duration == 2


def test_equal_video_filenames_remain_independent_and_stop_at_eof(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    red = colored_clip(tmp_path / "a/clip.mp4", ("red",))
    blue = colored_clip(tmp_path / "b/clip.mp4", ("blue",))
    scene = compose.Video(
        resolution=(32, 16),
        fps=4,
        load_system_fonts=False,
        composition=compose.Composition(
            duration=1,
            children=(
                compose.VideoClip(source=red, size=(16, 16)),
                compose.VideoClip(source=blue, size=(16, 16), position=compose.Position(x=16)),
            ),
        ),
    )
    pixels = scene.rgba(0)
    assert pixels[:3] == pytest.approx((255, 0, 0), abs=3)
    assert pixels[16 * 4 : 16 * 4 + 3] == pytest.approx((0, 0, 255), abs=3)
    assert not any(scene.rgba(1))
    with pytest.raises(ValueError, match="offset beyond EOF"):
        compose.Video(
            resolution=(16, 16),
            composition=compose.Composition(
                duration=1, children=(compose.VideoClip(source=red, size=(16, 16), offset=1),)
            ),
        ).compile()


def test_explicit_image_binding_owns_pixels_and_rejects_duplicates(tmp_path: Path) -> None:
    source = tmp_path / "image.png"
    compose.Video(
        resolution=(16, 16),
        composition=compose.Composition(
            duration=1, children=(compose.Rectangle(size=(16, 16), fill="#ff0000"),)
        ),
    ).save_png(source)
    binding = fframes.ImageBinding(name="photo", source=source)
    config = fframes.VideoConfig(width=16, height=16)
    frames = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">'
        '<image href="image:photo" width="16" height="16"/></svg>',
    )
    with pytest.raises(ValueError, match="duplicate image"):
        fframes.compile_video(config, frames, images=(binding, binding))
    video = fframes.compile_video(config, frames, images=(binding,))
    source.unlink()
    assert video.rgba(0) == b"\xff\0\0\xff" * 256


def test_native_and_compose_audio_share_sample_accurate_mixing(tmp_path: Path) -> None:
    source = write_audio(tmp_path / "tone.wav", (2000, 1000) * (RATE // 10), channels=2)
    settings = fframes.AudioTrack(
        source=source,
        start_at=0.02002,
        duration=0.15,
        loop=True,
        offset=0.01,
        fade_in=0.02,
        fade_out=0.03,
        pan=0.25,
    )
    native = fframes.Video(
        config=fframes.VideoConfig(width=16, height=16, fps=10),
        frames=('<svg xmlns="http://www.w3.org/2000/svg"/>',) * 2,
        audio=(settings,),
    )
    composed = compose.Video(
        resolution=(16, 16),
        fps=10,
        composition=compose.Composition(
            duration=0.2,
            children=(
                compose.Audio(
                    source=source, loop=True, offset=0.01, fade_in=0.02, fade_out=0.03, pan=0.25
                ).at(0.02002, duration=0.15),
            ),
        ),
    )
    assert native.audio_samples() == composed.compile().audio_samples()
    path = native.render(tmp_path / "mixed.mp4", options=fframes.RenderOptions(concurrency=2))
    assert path.stat().st_size > 0
