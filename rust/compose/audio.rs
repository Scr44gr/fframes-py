use std::borrow::Cow;

use fframes::{
    AudioData, AudioMap, AudioTimelineSamples, AudioTimestamp, AudioTrack, DynamicMediaProvider,
    ResolvedAudioMap, TimeBase, TrackMix, media::PreloadedAudioData,
};
use pyo3::{PyResult, exceptions::PyValueError};

use super::input::Sound;
use crate::render::{media_error, render_error};

pub(super) const SAMPLE_RATE: usize = 48000;

struct Track {
    file: String,
    start: usize,
    end: usize,
    mix: TrackMix,
}

pub(super) struct Soundtrack {
    pub media: DynamicMediaProvider<'static>,
    pub map: Option<ResolvedAudioMap<AudioTimelineSamples>>,
}

pub(super) fn prepare(sounds: Vec<Sound>, duration: f64) -> PyResult<Soundtrack> {
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
