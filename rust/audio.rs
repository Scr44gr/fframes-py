use serde::Deserialize;
use std::borrow::Cow;

use fframes::{
    AudioData, AudioMap, AudioTimelineSamples, AudioTimestamp, AudioTrack, DynamicMediaProvider,
    ResolvedAudioMap, TimeBase, TrackMix, media::PreloadedAudioData,
};
use pyo3::{PyResult, exceptions::PyValueError};

use crate::render::render_error;

pub(crate) const SAMPLE_RATE: usize = 48000;

#[derive(serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Limiter {
    ceiling_db: f32,
    lookahead_ms: f32,
    release_ms: f32,
}

#[derive(serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Mix {
    master_gain_db: f32,
    limiter: Option<Limiter>,
    declick: bool,
}

impl Mix {
    pub fn parse(json: Option<&str>) -> PyResult<fframes::AudioMixOptions> {
        json.map_or(Ok(fframes::AudioMixOptions::default()), |json| {
            let settings: Self = serde_json::from_str(json).map_err(render_error)?;
            settings.native()
        })
    }
    pub fn native(&self) -> PyResult<fframes::AudioMixOptions> {
        if !(-120. ..=24.).contains(&self.master_gain_db) {
            return Err(PyValueError::new_err(
                "master_gain_db must be between -120 and 24",
            ));
        }
        let limiter = self
            .limiter
            .as_ref()
            .map(|limit| {
                if !(-120. ..=0.).contains(&limit.ceiling_db)
                    || !(0. ..=1000.).contains(&limit.lookahead_ms)
                    || !(f32::MIN_POSITIVE..=60000.).contains(&limit.release_ms)
                {
                    return Err(PyValueError::new_err("invalid limiter ceiling or timing"));
                }
                Ok(fframes::LimiterOptions {
                    ceiling_db: limit.ceiling_db,
                    lookahead_ms: limit.lookahead_ms,
                    release_ms: limit.release_ms,
                })
            })
            .transpose()?;
        Ok(fframes::AudioMixOptions {
            master_gain_db: self.master_gain_db,
            limiter,
            declick: self.declick,
        })
    }
}

#[derive(Deserialize)]
pub(crate) struct Sound {
    pub start: f64,
    pub end: f64,
    pub audio: Audio,
}

#[derive(Deserialize)]
pub(crate) struct Audio {
    pub source: crate::buffers::Source,
    pub gain_db: f32,
    pub pan: f32,
    pub offset: f64,
    pub fade_in: f32,
    pub fade_out: f32,
    pub r#loop: bool,
    #[serde(default = "normal_rate")]
    pub rate: f32,
    #[serde(default)]
    pub effects: Vec<crate::effects::Effect>,
    #[serde(default)]
    pub fade_curve: crate::effects::FadeCurve,
    #[serde(default)]
    pub voice: bool,
    pub duck: Option<crate::effects::Ducking>,
}

fn normal_rate() -> f32 {
    1.
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
    mix: fframes::AudioMixOptions,
) -> Vec<u8> {
    let count = (frames as f64 / fps as f64 * SAMPLE_RATE as f64).round() as usize;
    let (left, right) =
        fframes::AudioMixer::new(map, Some(media), SAMPLE_RATE, 0..count, count, mix).render_all();
    left.into_iter()
        .zip(right)
        .flat_map(|(left, right)| left.to_le_bytes().into_iter().chain(right.to_le_bytes()))
        .collect()
}

pub(crate) fn prepare(
    sounds: Vec<Sound>,
    duration: f64,
    buffers: &crate::buffers::Buffers,
) -> PyResult<Soundtrack> {
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
            || !audio.rate.is_finite()
            || !(0.05..=20.).contains(&audio.rate)
        {
            return Err(PyValueError::new_err(
                "invalid audio interval or mix settings",
            ));
        }
        let file = audio.source.key()?;
        if !media.audio.contains_key(&file) {
            let data = audio.source.audio(buffers)?;
            media.audio.insert(file.clone(), AudioData::Preloaded(data));
        }
        let Some(AudioData::Preloaded(data)) = media.audio.get(&file) else {
            return Err(PyValueError::new_err("audio source was not decoded"));
        };
        let source_rate = data.sample_rate;
        let ratio = f64::from(audio.rate) * f64::from(source_rate) / SAMPLE_RATE as f64;
        let offset = (audio.offset * f64::from(source_rate)).round() as usize;
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
            (end - start).min((remaining as f64 / ratio).ceil() as usize)
        };
        let source_count = (count as f64 * ratio).ceil() as usize;
        let repeated = audio.r#loop && source_count > remaining;
        let key = if repeated {
            let key = format!("{file}\0{offset}:{source_count}");
            if !media.audio.contains_key(&key) {
                // Upstream has no loop source: materialize just the audible interval
                // once, and share it across identical occurrences. Fades stay global.
                let extend = |samples: &[f32]| -> Cow<'static, [f32]> {
                    Cow::Owned(
                        samples[offset..]
                            .iter()
                            .copied()
                            .cycle()
                            .take(source_count)
                            .collect(),
                    )
                };
                let looped = PreloadedAudioData {
                    samples: extend(&data.samples),
                    sample_rate: source_rate,
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
                offset: if repeated { 0. } else { audio.offset as f32 },
                gain_db: audio.gain_db,
                pan: audio.pan,
                fade_in: audio.fade_in,
                fade_out: audio.fade_out,
                rate: audio.rate,
                effects: audio
                    .effects
                    .into_iter()
                    .map(crate::effects::Effect::native)
                    .collect(),
                fade_curve: audio.fade_curve.native(),
                voice: audio.voice,
                duck: audio.duck.map(crate::effects::Ducking::native),
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
                    mix: track.mix.clone(),
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
