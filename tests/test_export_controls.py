import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import monotonic, sleep

import numpy as np
import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

import fframes as f
from fframes import compose as c
from fframes.models import Backend
from tests.backends import BACKENDS
from tests.test_encoding import media_tools as media_tools


class Stream(BaseModel):
    model_config = ConfigDict(frozen=True)
    codec_type: str
    codec_name: str
    pix_fmt: str | None = None
    sample_rate: str | None = None
    width: int | None = None
    height: int | None = None
    nb_read_frames: str
    r_frame_rate: str
    duration: str


class Probe(BaseModel):
    streams: tuple[Stream, ...]


@pytest.mark.parametrize("api", ["native", "compose"])
@pytest.mark.parametrize("backend", BACKENDS)
def test_export_overrides_deliver_requested_streams_and_preserve_time(
    api: str,
    backend: Backend,
    tmp_path: Path,
    media_tools: tuple[str, str],
) -> None:
    source = f.Pcm(
        data=(0.2 * np.sin(np.arange(48000) * 2 * np.pi * 440 / 24000)).astype("<f4").tobytes(),
        channels=1,
        sample_rate=24000,
    )
    if api == "native":
        video: f.Video | c.Video = f.Video(
            config=f.VideoConfig(width=64, height=64, fps=24, backend=backend),
            frames=tuple(
                '<svg width="64" height="64">'
                f'<rect width="64" height="64" fill="rgb({i * 4},0,0)"/>'
                '<rect x="48" y="48" width="16" height="16" fill="white"/></svg>'
                for i in range(48)
            ),
            audio=(f.AudioTrack(source=source),),
        )
    else:
        video = c.Video(
            resolution=(64, 64),
            fps=24,
            backend=backend,
            composition=c.Composition(
                duration=2,
                children=(
                    c.Rectangle(
                        size=(64, 64),
                        fill=c.ColorTween(from_value="#000000", to_value="#c00000", duration=2),
                    ),
                    c.Rectangle(size=(16, 16), position=c.Position(x=48, y=48), fill="#ffffff"),
                    c.Audio(source=source),
                ),
            ),
        )
    control = f.RenderControl()
    path = video.render(
        tmp_path / "overrides.mp4",
        control=control,
        options=f.RenderOptions(
            encoder="mpeg4",
            concurrency=1,
            fps=15,
            scale=0.5,
            frame_range=(12, 36),
            pixel_format="yuv420p",
            gop_size=3,
            qmin=2,
            qmax=15,
            codec_params=(("bf", "0"),),
            audio=f.AudioEncoderOptions(sample_rate=44100),
            audio_mix=f.AudioMixOptions(master_gain_db=-6.020599913, limiter=None),
        ),
    )
    ffprobe, ffmpeg = media_tools
    metadata = subprocess.run(  # noqa: S603 -- Inspect a generated file with a fixed executable.
        [ffprobe, "-v", "error", "-show_streams", "-count_frames", "-of", "json", str(path)],
        check=True,
        capture_output=True,
    )
    streams = Probe.model_validate_json(metadata.stdout).streams
    picture = next(s for s in streams if s.codec_type == "video")
    sound = next(s for s in streams if s.codec_type == "audio")
    assert (
        picture.codec_name,
        picture.pix_fmt,
        picture.width,
        picture.height,
        picture.nb_read_frames,
        picture.r_frame_rate,
    ) == ("mpeg4", "yuv420p", 32, 32, "15", "15/1")
    assert sound.sample_rate == "44100"
    assert float(picture.duration) == pytest.approx(1)
    assert float(sound.duration) == pytest.approx(1, abs=0.03)
    decoded = subprocess.run(  # noqa: S603 -- Check scaling and authored clocks in delivered pixels.
        [ffmpeg, "-v", "error", "-i", str(path), "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        check=True,
        capture_output=True,
    ).stdout
    pictures = np.frombuffer(decoded, dtype="u1").reshape(15, 32, 32, 3)
    for index in (0, 7, 14):
        source_frame = 12 + index * 24 / 15
        red = (int(source_frame) if api == "native" else source_frame) * 4
        assert tuple(pictures[index, 8, 8]) == pytest.approx((red, 0, 0), abs=4)
        assert pictures[index, 28, 28].min() >= 245
    audio = subprocess.run(  # noqa: S603 -- Decode actual encoded samples to verify gain and playback speed.
        [ffmpeg, "-v", "error", "-i", str(path), "-vn", "-f", "f32le", "-acodec", "pcm_f32le", "-"],
        check=True,
        capture_output=True,
    ).stdout
    samples = np.frombuffer(audio, dtype="<f4").reshape(-1, 2)[4410:22050, 0]
    assert float(np.sqrt(np.square(samples).mean())) == pytest.approx(0.1 / np.sqrt(2), abs=0.006)
    frequency = int(np.argmax(np.abs(np.fft.rfft(samples)))) * 44100 / len(samples)
    assert frequency == pytest.approx(440, abs=3)
    status = control.progress
    assert (status.state, status.frames, status.total_frames) == ("complete", 15, 15)
    assert status.audio_frames > 0
    assert len(video) == 48
    assert not list(tmp_path.glob("fframes-py-*"))
    with pytest.raises(ValueError, match="one export"):
        video.render(tmp_path / "reuse.mp4", control=control)


def test_cancel_before_export_preserves_destination(tmp_path: Path) -> None:
    video = c.Video(resolution=(16, 16), composition=c.Composition(duration=1)).compile()
    path = tmp_path / "movie.mp4"
    path.write_bytes(b"original")
    control = f.RenderControl()
    initial = control.progress
    assert initial.state == "idle"
    control.cancel()
    with pytest.raises(RuntimeError, match="cancelled"):
        video.render(path, control=control)
    assert control.progress.state == "cancelled"
    assert path.read_bytes() == b"original"
    assert not list(tmp_path.glob("fframes-py-*"))


def test_cancel_during_native_render_can_be_polled_from_python(tmp_path: Path) -> None:
    video = c.Video(
        resolution=(128, 128),
        fps=60,
        composition=c.Composition(
            duration=120,
            children=(
                c.Circle(radius=c.Tween(from_value=1, to_value=60, duration=120), fill="#ffffff"),
            ),
        ),
    ).compile()
    control = f.RenderControl()
    path = tmp_path / "cancelled.mp4"
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            video.render, path, control=control, options=f.RenderOptions(concurrency=2)
        )
        deadline = monotonic() + 15
        while control.progress.frames == 0 and not future.done() and monotonic() < deadline:
            sleep(0.005)
        observed = control.progress
        control.cancel()
        with pytest.raises(RuntimeError, match="cancelled"):
            future.result(timeout=15)
    assert 0 < observed.frames < observed.total_frames
    assert control.progress.state == "cancelled"
    assert not path.exists()
    assert not list(tmp_path.glob("fframes-py-*"))


@pytest.mark.parametrize(
    "options",
    [
        f.RenderOptions(codec_params=(("not_an_encoder_option", "1"),)),
        f.RenderOptions(codec_params=(("ar", "44100"),)),
        f.RenderOptions(audio=f.AudioEncoderOptions(codec_params=(("sample_fmt", "s16"),))),
        f.RenderOptions(audio=f.AudioEncoderOptions(codec_params=(("channel_layout", "mono"),))),
        f.RenderOptions(pixel_format="not_a_pixel_format"),
        f.RenderOptions(audio=f.AudioEncoderOptions(sample_rate=12345)),
        f.RenderOptions(audio=f.AudioEncoderOptions(sample_format="s16")),
    ],
)
def test_invalid_encoder_settings_fail_without_replacing_existing_output(
    options: f.RenderOptions, tmp_path: Path
) -> None:
    source = f.Pcm(data=bytes(4800 * 4), channels=1)
    scene = c.Video(
        resolution=(16, 16),
        fps=10,
        composition=c.Composition(duration=0.1, children=(c.Audio(source=source),)),
    ).compile()
    control = f.RenderControl()
    path = tmp_path / "existing.mp4"
    path.write_bytes(b"original")
    with pytest.raises(ValueError, match=r"(codec_params|pixel_format|sample_rate|sample_format)"):
        scene.render(path, options=options, control=control)
    assert control.progress.state == "failed"
    assert path.read_bytes() == b"original"


def test_render_options_reject_ambiguous_parameters() -> None:
    with pytest.raises(ValidationError, match="unique"):
        f.RenderOptions(codec_params=(("bf", "0"), ("bf", "1")))
    with pytest.raises(ValidationError, match="qmin"):
        f.RenderOptions(qmin=20, qmax=10)


def test_encoder_inventory_distinguishes_audio_from_video() -> None:
    audio = f.available_encoders("audio")
    video = f.available_encoders()
    assert "aac" in audio
    assert "libopenh264" in video
    assert not set(audio) & set(video)


@pytest.mark.parametrize("backend", BACKENDS)
def test_explicit_ten_bit_pixel_format_and_codec_tag_reach_container(
    backend: Backend, tmp_path: Path, media_tools: tuple[str, str]
) -> None:
    video = c.Video(
        resolution=(32, 32),
        fps=2,
        backend=backend,
        composition=c.Composition(
            duration=1, children=(c.Rectangle(size=(32, 32), fill="#804020"),)
        ),
    )
    path = video.render(
        tmp_path / "prores.mov",
        options=f.RenderOptions(
            encoder="prores_ks",
            pixel_format="yuv422p10le",
            tag="apcn",
            gop_size=0,
            concurrency=1,
            codec_params=(("profile", "2"),),
        ),
    )
    ffprobe, ffmpeg = media_tools
    metadata = subprocess.run(  # noqa: S603 -- Verify the delivered codec, not encoder option names.
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,pix_fmt,codec_tag_string",
            "-of",
            "csv=p=0",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert metadata.strip() == "prores,apcn,yuv422p10le"
    subprocess.run(  # noqa: S603 -- Decode every delivered frame.
        [ffmpeg, "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"],
        check=True,
        capture_output=True,
    )
