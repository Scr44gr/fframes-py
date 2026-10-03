use serde::Deserialize;
use std::{borrow::Cow, path::PathBuf};

use fframes::{
    AudioData, AudioMap, AudioTimelineSamples, AudioTimestamp, AudioTrack, DynamicMediaProvider,
    ResolvedAudioMap, TimeBase, TrackMix, media::PreloadedAudioData,
};
use pyo3::{PyResult, exceptions::PyValueError};

use crate::render::{media_error, render_error};

pub(crate) const SAMPLE_RATE: usize = 48000;

#[derive(Deserialize)]
pub(crate) struct Sound {
    pub start: f64,
    pub end: f64,
    pub audio: Audio,
}

#[derive(Deserialize)]
pub(crate) struct Audio {
    pub source: PathBuf,
    pub gain_db: f32,
    pub pan: f32,
    pub offset: f64,
    pub fade_in: f32,
    pub fade_out: f32,
    pub r#loop: bool,
}

#[derive(Deserialize)]
pub(crate) struct Input {
    pub start_at: f64,
    pub duration: Option<f64>,
    #[serde(flatten)]
    pub audio: Audio,
}

impl Input {
    pub fn sound(self, duration: f64) -> PyResult<Option<Sound>> {
        if !self.start_at.is_finite()
            || self.start_at < 0.
            || self.start_at > 86400.
            || self
                .duration
                .is_some_and(|d| !d.is_finite() || d <= 0. || d > 86400.)
        {
            return Err(PyValueError::new_err("invalid audio track interval"));
        }
        Ok((self.start_at < duration).then(|| Sound {
            start: self.start_at,
            end: self
                .duration
                .map_or(duration, |d| (self.start_at + d).min(duration)),
            audio: self.audio,
        }))
    }
}

struct Track {
    file: String,
    start: usize,
    end: usize,
    mix: TrackMix,
}

pub(crate) struct Soundtrack {
    pub media: DynamicMediaProvider<'static>,
    pub map: Option<ResolvedAudioMap<AudioTimelineSamples>>,
}

pub(crate) fn samples(
    media: &DynamicMediaProvider<'_>,
    map: Option<&ResolvedAudioMap<AudioTimelineSamples>>,
    frames: usize,
    fps: usize,
) -> Vec<u8> {
    let count = (frames as f64 / fps as f64 * SAMPLE_RATE as f64).round() as usize;
    let (left, right) = fframes::AudioMixer::new(
        map,
        Some(media),
        SAMPLE_RATE,
        0..count,
        count,
        Default::default(),
    )
    .render_all();
    left.into_iter()
        .zip(right)
        .flat_map(|(left, right)| left.to_le_bytes().into_iter().chain(right.to_le_bytes()))
        .collect()
}

pub(crate) fn prepare(sounds: Vec<Sound>, duration: f64) -> PyResult<Soundtrack> {
    let mut media = DynamicMediaProvider::default();
    let mut tracks = Vec::with_capacity(sounds.len());
    for sound in sounds {
        let audio = sound.audio;
        if !sound.start.is_finite()
            || !sound.end.is_finite()
            || sound.start < 0.
            || sound.end <= sound.start
            || sound.end > duration + 1e-9
            || !(-120. ..=24.).contains(&audio.gain_db)
            || !(-1. ..=1.).contains(&audio.pan)
            || !audio.offset.is_finite()
            || audio.offset < 0.
            || !audio.fade_in.is_finite()
            || audio.fade_in < 0.
            || !audio.fade_out.is_finite()
            || audio.fade_out < 0.
        {
            return Err(PyValueError::new_err(
                "invalid audio interval or mix settings",
            ));
        }
        let source = audio.source.canonicalize()?;
        let file = source.to_string_lossy().into_owned();
        if !media.audio.contains_key(&file) {
            let data =
                PreloadedAudioData::decode_raw_file_stereo(Some(SAMPLE_RATE as u32), &source)
                    .map_err(media_error)?;
            media.audio.insert(file.clone(), AudioData::Preloaded(data));
        }
        let Some(AudioData::Preloaded(data)) = media.audio.get(&file) else {
            return Err(PyValueError::new_err("audio source was not decoded"));
        };
        let offset = (audio.offset * SAMPLE_RATE as f64).round() as usize;
        if offset >= data.samples.len() {
            return Err(PyValueError::new_err(
                "audio offset must precede the end of the source",
            ));
        }
        let start = (sound.start * SAMPLE_RATE as f64).round() as usize;
        let end = (sound.end * SAMPLE_RATE as f64).round() as usize;
        let remaining = data.samples.len() - offset;
        let count = if audio.r#loop {
            end - start
        } else {
            (end - start).min(remaining)
        };
        let key = if offset > 0 || (audio.r#loop && count > remaining) {
            let key = format!("{file}\0{offset}:{count}");
            if !media.audio.contains_key(&key) {
                // Upstream has no loop source: materialize just the audible interval
                // once, and share it across identical occurrences. Fades stay global.
                let extend = |samples: &[f32]| -> Cow<'static, [f32]> {
                    Cow::Owned(
                        samples[offset..]
                            .iter()
                            .copied()
                            .cycle()
                            .take(count)
                            .collect(),
                    )
                };
                let looped = PreloadedAudioData {
                    samples: extend(&data.samples),
                    sample_rate: SAMPLE_RATE as u32,
                    right: data.right.as_ref().map(|right| extend(right)),
                };
                media
                    .audio
                    .insert(key.clone(), AudioData::Preloaded(looped));
            }
            key
        } else {
            file
        };
        tracks.push(Track {
            file: key,
            start,
            end: start + count,
            mix: TrackMix {
                gain_db: audio.gain_db,
                pan: audio.pan,
                fade_in: audio.fade_in,
                fade_out: audio.fade_out,
                ..Default::default()
            },
        });
    }
    // Using sample indices as the resolver's frames avoids f32 Second timestamps.
    let map = AudioMap(if tracks.is_empty() {
        None
    } else {
        Some(
            tracks
                .iter()
                .map(|track| AudioTrack {
                    file: &track.file,
                    range: AudioTimestamp::Frame(track.start)..AudioTimestamp::Frame(track.end),
                    mix: track.mix,
                })
                .collect(),
        )
    });
    let map = map
        .resolve_with_scenes(
            None,
            &TimeBase {
                fps: SAMPLE_RATE,
                sample_rate: SAMPLE_RATE,
            },
            |_| Ok(0.),
        )
        .map_err(render_error)?;
    Ok(Soundtrack { media, map })
}
