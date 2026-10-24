//! Shared native mix analysis; DSP comes from upstream.

use crate::{inspection::Video, render::render_error};
use pyo3::{exceptions::PyValueError, prelude::*};
use serde::{Deserialize, Serialize};

#[derive(Deserialize)]
struct Section {
    name: String,
    start: f64,
    end: f64,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Settings {
    mix: crate::audio::Mix,
    sample_rate: usize,
    frame_range: Option<(usize, usize)>,
    sections: Vec<Section>,
    at: Vec<f64>,
    waveform_bins: usize,
}

#[derive(Serialize)]
struct ActiveTrack {
    file: String,
    file_seconds: f64,
    gain_db: Option<f32>,
    voice: bool,
    ducked_db: f32,
    rate: f32,
    effects: Vec<crate::effects::Effect>,
}

#[derive(Serialize)]
struct Activity {
    seconds: f64,
    tracks: Vec<ActiveTrack>,
}
#[derive(Serialize)]
struct Waveform {
    left: Vec<[f32; 2]>,
    right: Vec<[f32; 2]>,
}
#[derive(Serialize)]
struct Inspection {
    start_seconds: f64,
    report: fframes::AudioReport,
    waveform: Waveform,
    activity: Vec<Activity>,
}

fn envelope(samples: &[f32], bins: usize) -> Vec<[f32; 2]> {
    let bins = bins.min(samples.len());
    (0..bins)
        .map(|i| {
            samples[i * samples.len() / bins..(i + 1) * samples.len() / bins]
                .iter()
                .fold([f32::INFINITY, f32::NEG_INFINITY], |[lo, hi], &value| {
                    [lo.min(value), hi.max(value)]
                })
        })
        .collect()
}

#[pyfunction]
pub(crate) fn analyze_audio(py: Python<'_>, video: Video<'_>, settings: &str) -> PyResult<String> {
    let settings: Settings = serde_json::from_str(settings).map_err(render_error)?;
    let resources = video.source().resources();
    py.detach(|| {
        let (start, end) = settings
            .frame_range
            .unwrap_or((0, resources.timeline.duration_in_frames));
        if start >= end
            || end > resources.timeline.duration_in_frames
            || settings.sample_rate == 0
            || settings.sample_rate > i32::MAX as usize
            || !(1..=65536).contains(&settings.waveform_bins)
        {
            return Err(PyValueError::new_err(
                "invalid audio frame_range, sample_rate or waveform_bins",
            ));
        }
        let sample = |frame: usize| {
            (frame as f64 * settings.sample_rate as f64 / resources.fps as f64).round() as usize
        };
        let (first, last, total) = (
            sample(start),
            sample(end),
            sample(resources.timeline.duration_in_frames),
        );
        let mut mixer = fframes::AudioMixer::new_rescaled(
            resources.timeline.audio_map.as_ref(),
            resources.sample_rate,
            resources.media,
            settings.sample_rate,
            first..last,
            total,
            settings.mix.native()?,
        );
        let activity = settings
            .at
            .iter()
            .map(|&seconds| {
                if !seconds.is_finite()
                    || seconds < 0.
                    || seconds
                        >= resources.timeline.duration_in_frames as f64 / resources.fps as f64
                {
                    return Err(PyValueError::new_err(
                        "audio activity time must lie inside the video",
                    ));
                }
                let tracks = mixer
                    .active_tracks_at((seconds * settings.sample_rate as f64).round() as usize)
                    .into_iter()
                    .map(|mut track| {
                        // Loops materialize only the audible interval. Report positions
                        // in the original source instead of that private repeated buffer.
                        if let Some((file, suffix)) = track.file.split_once('\0')
                            && let Some((offset, _)) = suffix.split_once(':')
                            && let Ok(offset) = offset.parse::<usize>()
                            && let Some(data) =
                                resources.media.and_then(|media| media.resolve_audio(file))
                        {
                            let rate = f64::from(data.sample_rate());
                            let start = offset as f64 / rate;
                            let duration = data.duration_in_samples() as f64 / rate - start;
                            track.file_seconds = start + track.file_seconds.rem_euclid(duration);
                            track.file = file.to_owned();
                        }
                        ActiveTrack {
                            file: track.file,
                            file_seconds: track.file_seconds,
                            gain_db: track.gain_db.is_finite().then_some(track.gain_db),
                            voice: track.voice,
                            ducked_db: track.ducked_db,
                            rate: track.rate,
                            effects: track
                                .effects
                                .into_iter()
                                .map(crate::effects::Effect::from)
                                .collect(),
                        }
                    })
                    .collect();
                Ok(Activity { seconds, tracks })
            })
            .collect::<PyResult<Vec<_>>>()?;
        let mut sections = Vec::with_capacity(settings.sections.len());
        for section in &settings.sections {
            if !section.start.is_finite()
                || !section.end.is_finite()
                || section.start < 0.
                || section.start >= section.end
                || section.end > resources.timeline.duration_in_frames as f64 / resources.fps as f64
            {
                return Err(PyValueError::new_err(
                    "audio section must be a nonempty interval inside the video",
                ));
            }
            let from = (section.start * settings.sample_rate as f64).round() as usize;
            let to = (section.end * settings.sample_rate as f64).round() as usize;
            if from < last && to > first {
                sections.push((
                    section.name.clone(),
                    from.saturating_sub(first)..to.min(last) - first,
                ));
            }
        }
        let (left, right) = mixer.render_all();
        let result = Inspection {
            start_seconds: start as f64 / resources.fps as f64,
            report: fframes::analyze_audio(&left, &right, settings.sample_rate, &sections),
            waveform: Waveform {
                left: envelope(&left, settings.waveform_bins),
                right: envelope(&right, settings.waveform_bins),
            },
            activity,
        };
        serde_json::to_string(&result).map_err(render_error)
    })
}
