import os
import shutil
import subprocess
from math import sin, tau
from pathlib import Path
from statistics import mean
from typing import Literal

import numpy as np
import pytest
from pydantic import BaseModel, ConfigDict

import fframes
from fframes import compose
from fframes.models import Backend
from tests.test_composition_audio import RATE, write_audio


def range_video(api: str, backend: Backend, source: Path) -> fframes.Video | compose.Video:
    colors = ("#ff0000", "#00ff00", "#0000ff")
    if api == "native":
        return fframes.Video(
            config=fframes.VideoConfig(width=32, height=32, fps=30, backend=backend),
            frames=tuple(
                f'<svg width="32" height="32"><rect width="32" height="32" fill="{color}"/></svg>'
                for color in colors
                for _ in range(30)
            ),
            audio=(fframes.AudioTrack(source=source),),
        )
    return compose.Video(
        resolution=(32, 32),
        fps=30,
        backend=backend,
        composition=compose.Composition(
            duration=3,
            children=(
                *(
                    compose.Rectangle(size=(32, 32), fill=c).at(i, duration=1)
                    for i, c in enumerate(colors)
                ),
                compose.Audio(source=source),
            ),
        ),
    )


class Stream(BaseModel):
    model_config = ConfigDict(frozen=True)

    codec_type: Literal["video", "audio"]
    codec_name: str
    codec_tag_string: str
    profile: str
    pix_fmt: str | None = None
    width: int | None = None
    height: int | None = None
    nb_read_frames: str
    duration: str
    sample_rate: str | None = None
    color_space: str | None = None
    color_range: str | None = None


class Probe(BaseModel):
    model_config = ConfigDict(frozen=True)

    streams: tuple[Stream, ...]


@pytest.fixture(scope="module")
def media_tools() -> tuple[str, str]:
    ffprobe = shutil.which("ffprobe")
    ffmpeg = shutil.which("ffmpeg")
    assert ffprobe, "Install ffprobe to verify encoded files."
    assert ffmpeg, "Install ffmpeg to verify decoding."
    return ffprobe, ffmpeg


def test_registry_reports_video_encoders_from_the_extension() -> None:
    encoders = fframes.available_encoders()
    assert {"libopenh264", "mpeg4"} <= set(encoders)
    assert "aac" not in encoders
    assert encoders == sorted(set(encoders))


@pytest.mark.parametrize("resolution", [(14, 16), (16, 14)])
def test_openh264_rejects_small_images_without_replacing_output(
    resolution: tuple[int, int], tmp_path: Path
) -> None:
    destination = tmp_path / "small.mp4"
    destination.write_bytes(b"existing output")
    video = compose.Video(
        resolution=resolution,
        composition=compose.Composition(duration=0.1),
    )
    with pytest.raises(ValueError, match="at least 16 pixels"):
        video.render(destination)
    assert destination.read_bytes() == b"existing output"
    video.render(destination, options=fframes.RenderOptions(encoder="mpeg4"))
    assert destination.read_bytes()[4:8] == b"ftyp"


@pytest.mark.parametrize("api", ["native", "compose"])
@pytest.mark.parametrize(
    "encoder",
    [
        None,
        "mpeg4",
        pytest.param(
            os.environ.get("FFRAMES_TEST_ENCODER"),
            marks=pytest.mark.skipif(
                "FFRAMES_TEST_ENCODER" not in os.environ,
                reason="Set FFRAMES_TEST_ENCODER to test an installed hardware encoder",
            ),
            id="hardware",
        ),
    ],
)
def test_mp4_codecs_and_decoding(
    api: str, encoder: str | None, tmp_path: Path, media_tools: tuple[str, str]
) -> None:
    # More than one scheduler segment, with a visible change across the midpoint.
    source = write_audio(tmp_path / "audio.wav", (2000, -2000) * RATE)
    destination = tmp_path / "video.mp4"
    options = (
        fframes.RenderOptions(concurrency=2)
        if encoder is None
        else fframes.RenderOptions(encoder=encoder, concurrency=2)
    )
    if api == "native":
        frames = tuple(
            '<svg xmlns="http://www.w3.org/2000/svg" width="96" height="64">'
            f'<rect width="96" height="64" fill="{color}"/></svg>'
            for color in ("red",) * 30 + ("blue",) * 30
        )
        video = fframes.compile_video(
            fframes.VideoConfig(width=96, height=64, fps=30),
            frames,
            audio=(fframes.AudioTrack(source=source),),
        )
        fframes.render(video, destination, options)
    else:
        compose.Video(
            resolution=(96, 64),
            fps=30,
            composition=compose.Composition(
                duration=2,
                children=(
                    compose.Rectangle(size=(96, 64), fill="#FF0000").at(0, duration=1),
                    compose.Rectangle(size=(96, 64), fill="#0000FF").at(1, duration=1),
                    compose.Audio(source=source),
                ),
            ),
        ).render(destination, options=options)

    ffprobe, ffmpeg = media_tools
    result = subprocess.run(  # noqa: S603 -- Resolved test tool, no shell or user arguments.
        [ffprobe, "-v", "error", "-show_streams", "-count_frames", "-of", "json", str(destination)],
        check=True,
        capture_output=True,
    )
    assert not result.stderr
    streams = Probe.model_validate_json(result.stdout).streams
    assert len(streams) == 2
    picture = next(stream for stream in streams if stream.codec_type == "video")
    assert picture.codec_name == ("mpeg4" if encoder == "mpeg4" else "h264")
    if encoder is None:
        assert picture.profile == "Constrained Baseline"
        assert picture.codec_tag_string == "avc1"
    assert picture.pix_fmt == "yuv420p"
    assert (picture.width, picture.height) == (96, 64)
    assert int(picture.nb_read_frames) == 60
    assert float(picture.duration) == pytest.approx(2)
    sound = next(stream for stream in streams if stream.codec_type == "audio")
    assert (sound.codec_name, sound.profile, sound.sample_rate) == ("aac", "LC", "48000")
    assert sound.codec_tag_string == "mp4a"
    encoded = destination.read_bytes()
    assert encoded.index(b"moov") < encoded.index(b"mdat")  # MP4 fast start.
    decoded = subprocess.run(  # noqa: S603 -- Check color planes and ordering across segments.
        [
            ffmpeg,
            "-v",
            "error",
            "-xerror",
            "-i",
            str(destination),
            "-an",
            "-vf",
            r"select=eq(n\,0)+eq(n\,59),format=rgb24",
            "-fps_mode",
            "passthrough",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        check=True,
        capture_output=True,
    )
    frame_bytes = 96 * 64 * 3
    assert len(decoded.stdout) == frame_bytes * 2
    # Lossy encoders can shift flat colors; detect swapped or missing chroma planes.
    colors = tuple(
        tuple(
            mean(decoded.stdout[start + channel : start + frame_bytes : 3]) for channel in range(3)
        )
        for start in (0, frame_bytes)
    )
    assert colors[0] == pytest.approx((255, 0, 0), abs=16)
    assert colors[1] == pytest.approx((0, 0, 255), abs=16)


@pytest.mark.parametrize(("matrix", "expected"), [("bt601", "smpte170m"), ("bt709", "bt709")])
@pytest.mark.parametrize("backend", ["cpu", "skia"])
def test_color_matrix_metadata_matches_actual_yuv_conversion(
    matrix: Literal["bt601", "bt709"],
    expected: str,
    backend: Backend,
    tmp_path: Path,
    media_tools: tuple[str, str],
) -> None:
    destination = tmp_path / "matrix.mp4"
    compose.Video(
        resolution=(64, 64),
        fps=10,
        backend=backend,
        composition=compose.Composition(
            duration=0.2, children=(compose.Rectangle(size=(64, 64), fill="#c050a0"),)
        ),
    ).render(destination, options=fframes.RenderOptions(color_matrix=matrix))
    ffprobe, ffmpeg = media_tools
    result = subprocess.run(  # noqa: S603 -- Fixed probe executable, no shell.
        [ffprobe, "-v", "error", "-show_streams", "-count_frames", "-of", "json", str(destination)],
        check=True,
        capture_output=True,
    )
    picture = Probe.model_validate_json(result.stdout).streams[0]
    assert picture.color_space == expected
    assert picture.color_range == "tv"
    assert picture.pix_fmt == "yuv420p"
    decoded = subprocess.run(  # noqa: S603 -- Verify decoded colors, not only the metadata.
        [
            ffmpeg,
            "-v",
            "error",
            "-i",
            str(destination),
            "-frames:v",
            "1",
            "-pix_fmt",
            "rgb24",
            "-f",
            "rawvideo",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
    ).stdout
    assert len(decoded) == 64 * 64 * 3
    assert tuple(mean(decoded[c::3]) for c in range(3)) == pytest.approx((192, 80, 160), abs=5)


@pytest.mark.parametrize("api", ["native", "compose"])
@pytest.mark.parametrize("backend", ["cpu", "skia"])
def test_range_export_preserves_original_clocks_and_trims_audio(
    api: str, backend: Backend, tmp_path: Path, media_tools: tuple[str, str]
) -> None:
    # Left, right, left: an incorrect audio offset changes the channel at each checkpoint.
    source = write_audio(
        tmp_path / "source.wav",
        tuple(
            round(6000 * sin(tau * 440 * sample / RATE)) if sample // RATE % 2 == channel else 0
            for sample in range(3 * RATE)
            for channel in range(2)
        ),
        channels=2,
    )
    video = range_video(api, backend, source)
    destination = video.render(
        tmp_path / "range.mp4",
        options=fframes.RenderOptions(frame_range=(15, 75), concurrency=2),
    )
    assert len(video) == 90
    ffprobe, ffmpeg = media_tools
    metadata = subprocess.run(  # noqa: S603 -- Fixed test tool, no shell.
        [ffprobe, "-v", "error", "-show_streams", "-count_frames", "-of", "json", str(destination)],
        check=True,
        capture_output=True,
    )
    streams = Probe.model_validate_json(metadata.stdout).streams
    picture = next(s for s in streams if s.codec_type == "video")
    sound = next(s for s in streams if s.codec_type == "audio")
    assert (picture.codec_name, picture.pix_fmt, picture.nb_read_frames) == (
        "h264",
        "yuv420p",
        "60",
    )
    assert float(picture.duration) == pytest.approx(2)
    assert float(sound.duration) == pytest.approx(2, abs=0.03)
    images = subprocess.run(  # noqa: S603 -- Decode the complete export, including segment boundaries.
        [
            ffmpeg,
            "-v",
            "error",
            "-xerror",
            "-i",
            str(destination),
            "-an",
            "-pix_fmt",
            "rgb24",
            "-f",
            "rawvideo",
            "-",
        ],
        check=True,
        capture_output=True,
    ).stdout
    pixels = np.frombuffer(images, dtype=np.uint8).reshape(60, 32, 32, 3)
    for frame, expected in (
        (0, (255, 0, 0)),
        (15, (0, 255, 0)),
        (45, (0, 0, 255)),
        (59, (0, 0, 255)),
    ):
        assert tuple(pixels[frame].mean(axis=(0, 1))) == pytest.approx(expected, abs=10)
    audio = subprocess.run(  # noqa: S603 -- Compare delivered AAC timing and channels.
        [
            ffmpeg,
            "-v",
            "error",
            "-xerror",
            "-i",
            str(destination),
            "-vn",
            "-f",
            "f32le",
            "-acodec",
            "pcm_f32le",
            "-",
        ],
        check=True,
        capture_output=True,
    ).stdout
    samples = np.frombuffer(audio, dtype="<f4").reshape(-1, 2)
    for time, channel in ((0.25, 0), (1.0, 1), (1.75, 0)):
        window = samples[round(time * RATE) : round((time + 0.05) * RATE)]
        energy = np.square(window).mean(axis=0)
        assert energy[channel] > 0.01
        assert energy[1 - channel] < 0.0001


@pytest.mark.parametrize("api", ["native", "compose"])
def test_out_of_bounds_export_preserves_destination_and_cleans_segments(
    api: str, tmp_path: Path
) -> None:
    source = write_audio(tmp_path / "source.wav", (0,) * RATE)
    video = range_video(api, "cpu", source)
    destination = tmp_path / "existing.mp4"
    destination.write_bytes(b"previous export")
    with pytest.raises(ValueError, match=r"frame_range.*end <= 90"):
        video.render(destination, options=fframes.RenderOptions(frame_range=(60, 91)))
    assert destination.read_bytes() == b"previous export"
    assert not list(tmp_path.glob("fframes-py-*"))
