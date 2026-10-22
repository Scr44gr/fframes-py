from typing import TYPE_CHECKING

import numpy as np
import pytest

import fframes as f
from fframes import compose as c

if TYPE_CHECKING:
    from fframes.inspection import NativeVideo


def tone(amplitude: float = 0.25, rate: int = 48000) -> f.Pcm:
    time = np.arange(rate * 2, dtype=np.float64) / rate
    values = (amplitude * np.sin(2 * np.pi * 1000 * time)).astype("<f4")
    return f.Pcm(data=values.tobytes(), sample_rate=rate, channels=1)


@pytest.mark.parametrize("api", ["native", "compose"])
def test_master_gain_limiter_and_audio_report_agree_with_samples(api: str) -> None:
    source = tone()
    if api == "native":
        video: NativeVideo = f.Video(
            config=f.VideoConfig(width=16, height=16, fps=10),
            frames=('<svg width="16" height="16"/>',) * 20,
            audio=(f.AudioTrack(source=source),),
        ).native
    else:
        video = (
            c.Video(
                resolution=(16, 16),
                fps=10,
                composition=c.Composition(
                    duration=2,
                    children=(c.Audio(source=source),),
                ),
            )
            .compile()
            .native
        )
    options = f.AudioAnalysisOptions(
        mix=f.AudioMixOptions(master_gain_db=6.020599913, limiter=None, declick=False),
        waveform_bins=31,
        at=(0.5,),
        sections=(f.AudioSection(name="middle", start=0.5, end=1.5),),
    )
    inspection = f.analyze_audio(video, options=options)
    assert inspection.report.duration_seconds == 2
    assert inspection.report.sample_peak_dbfs == pytest.approx(-6.0206, abs=0.01)
    assert inspection.report.integrated_lufs is not None
    assert inspection.report.clipped_samples == 0
    assert inspection.report.sections[0].name == "middle"
    assert inspection.activity[0].tracks[0].file_seconds == pytest.approx(0.5)
    assert len(inspection.waveform.left) == 31
    assert inspection.waveform.left[-1] == pytest.approx((-0.5, 0.5))
    samples = np.frombuffer(video.audio_samples(options.mix.model_dump_json()), dtype="<f4")
    assert samples.max() == pytest.approx(0.5)
    loud = f.analyze_audio(
        video,
        options=f.AudioAnalysisOptions(
            mix=f.AudioMixOptions(master_gain_db=24, limiter=None, declick=False)
        ),
    )
    limited = f.analyze_audio(
        video,
        options=f.AudioAnalysisOptions(
            mix=f.AudioMixOptions(master_gain_db=24, limiter=f.LimiterOptions(ceiling_db=-3))
        ),
    )
    assert loud.report.clipped_samples > 0
    assert limited.report.sample_peak_dbfs is not None
    assert limited.report.sample_peak_dbfs <= -2.99
    assert limited.report.clipped_samples == 0


def test_silence_range_resampling_and_loop_activity() -> None:
    silent = c.Video(resolution=(16, 16), fps=10, composition=c.Composition(duration=2)).compile()
    report = f.analyze_audio(silent.native)
    assert report.report.integrated_lufs is None
    assert report.report.sample_peak_dbfs is None
    assert report.report.silent_ranges == ((0.0, 2.0),)
    source = tone(rate=24000).slice(0, 12000)
    scene = c.Video(
        resolution=(16, 16),
        fps=10,
        composition=c.Composition(
            duration=2,
            children=(c.Audio(source=source, offset=0.1, loop=True).at(0.2),),
        ),
    ).compile()
    view = f.analyze_audio(
        scene.native,
        options=f.AudioAnalysisOptions(
            sample_rate=44100,
            frame_range=(5, 15),
            at=(0.1, 0.95),
            sections=(f.AudioSection(name="cut", start=0.2, end=1.8),),
        ),
    )
    assert view.start_seconds == 0.5
    assert view.report.duration_seconds == 1
    assert view.report.sample_rate == 44100
    assert view.report.sections[0].start_seconds == 0
    assert view.report.sections[0].end_seconds == 1
    assert view.activity[0].tracks == ()
    assert view.activity[1].tracks[0].file_seconds == pytest.approx(0.45, abs=1e-4)
    assert "\x00" not in view.activity[1].tracks[0].file
    with pytest.raises(ValueError, match="inside"):
        f.analyze_audio(scene.native, options=f.AudioAnalysisOptions(at=(2,)))
