import shutil
import subprocess
from pathlib import Path
from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict

import fframes
from fframes import compose
from tests.test_composition_audio import RATE, write_audio


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
@pytest.mark.parametrize("encoder", [None, "mpeg4"])
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
    assert picture.codec_name == ("h264" if encoder is None else "mpeg4")
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
    subprocess.run(  # noqa: S603 -- Decode the entire test output with the resolved tool.
        [ffmpeg, "-v", "error", "-xerror", "-i", str(destination), "-f", "null", "-"],
        check=True,
        capture_output=True,
    )
