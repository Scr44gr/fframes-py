//! Batched upstream FFT with a bounded smoothing cache and one Python output buffer.

use std::{borrow::Cow, collections::VecDeque, path::PathBuf};

use fframes::{
    AudioData, SampleSize, VisualizeFrameInput, WindowFunction, media::PreloadedAudioData,
};
use pyo3::{exceptions::PyValueError, prelude::*, types::PyBytes};
use serde::Deserialize;

use crate::render::media_error;

#[derive(Clone, Copy, Deserialize)]
#[serde(rename_all = "snake_case")]
enum Window {
    Hann,
    Hamming,
    HammingLegacy,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Settings {
    frames: usize,
    fps: usize,
    sample_size: usize,
    smooth: usize,
    window: Option<Window>,
    center: bool,
}

fn size(value: usize) -> PyResult<SampleSize> {
    Ok(match value {
        2 => SampleSize::S2,
        4 => SampleSize::S4,
        8 => SampleSize::S8,
        16 => SampleSize::S16,
        32 => SampleSize::S32,
        64 => SampleSize::S64,
        128 => SampleSize::S128,
        256 => SampleSize::S256,
        512 => SampleSize::S512,
        1024 => SampleSize::S1024,
        _ => {
            return Err(PyValueError::new_err(
                "sample_size must be a power of two from 2 to 1024",
            ));
        }
    })
}

/// Decoded mono samples owned by the analysis session, independent of the source file.
#[pyclass(frozen, module = "fframes._native")]
pub(crate) struct AudioAnalysis {
    data: AudioData<'static>,
}

impl AudioAnalysis {
    fn fill(
        &self,
        settings: &Settings,
        sample_size: SampleSize,
        output: &mut [u8],
    ) -> PyResult<()> {
        let bins = settings.sample_size / 2;
        // Precompute the corrected symmetric Hamming coefficients once. The
        // explicit legacy mode preserves fframes 1.2.0's misplaced cosine.
        let coefficients: Vec<f32> = if matches!(settings.window, Some(Window::Hamming)) {
            (0..settings.sample_size)
                .map(|i| {
                    0.54 - 0.46
                        * (std::f32::consts::TAU * i as f32 / (settings.sample_size - 1) as f32)
                            .cos()
                })
                .collect()
        } else {
            Vec::new()
        };
        let mut windowed = vec![0.; coefficients.len()];
        let input = VisualizeFrameInput {
            audio: &self.data,
            sample_size,
            smooth_level: settings.smooth,
            window: match settings.window {
                Some(Window::Hann) => Some(WindowFunction::Hann),
                Some(Window::HammingLegacy) => Some(WindowFunction::Hamming),
                _ => None,
            },
        };
        let mut rows: VecDeque<Vec<f32>> = VecDeque::new();
        let (mut first, mut next) = (0, 0);
        for (frame, target) in output.chunks_exact_mut(bins * 4).enumerate() {
            let smooth = settings.smooth > 0 && frame > settings.smooth * 2;
            let start = frame.saturating_sub(settings.smooth);
            let end = if smooth {
                frame + settings.smooth
            } else {
                frame + 1
            };
            while first < start {
                rows.pop_front();
                first += 1;
            }
            while next < end {
                let row = if coefficients.is_empty() {
                    fframes::get_visualization(next, settings.fps, &input)
                } else {
                    let samples =
                        self.data
                            .get_frame_data(settings.sample_size, next, settings.fps as i64);
                    for (i, out) in windowed.iter_mut().enumerate() {
                        *out = samples.get(i).copied().unwrap_or(0.) * coefficients[i];
                    }
                    let data = AudioData::Preloaded(PreloadedAudioData {
                        samples: Cow::Borrowed(&windowed),
                        sample_rate: self.data.sample_rate(),
                        right: None,
                    });
                    fframes::get_visualization(
                        0,
                        settings.fps,
                        &VisualizeFrameInput {
                            audio: &data,
                            sample_size: size(settings.sample_size)?,
                            smooth_level: 0,
                            window: None,
                        },
                    )
                };
                rows.push_back(row);
                next += 1;
            }
            for (bin, bytes) in target.as_chunks_mut::<4>().0.iter_mut().enumerate() {
                let source = if settings.center && bins > 1 {
                    let mid = bins / 2 - 1;
                    if bin <= mid {
                        (mid - bin) * 2
                    } else {
                        (bin - mid) * 2 - 1
                    }
                } else {
                    bin
                };
                let value = if smooth {
                    rows.iter().map(|row| row[source]).sum::<f32>() / rows.len() as f32
                } else {
                    rows[frame - first][source]
                };
                bytes.copy_from_slice(&value.to_le_bytes());
            }
        }
        Ok(())
    }
}

#[pymethods]
impl AudioAnalysis {
    #[getter]
    fn duration(&self) -> f64 {
        self.data.duration_in_samples() as f64 / f64::from(self.data.sample_rate())
    }

    #[getter]
    fn sample_rate(&self) -> u32 {
        self.data.sample_rate()
    }

    fn spectrum<'py>(&self, py: Python<'py>, settings: &str) -> PyResult<Bound<'py, PyBytes>> {
        let settings: Settings =
            serde_json::from_str(settings).map_err(|e| PyValueError::new_err(e.to_string()))?;
        let sample_size = size(settings.sample_size)?;
        if settings.frames == 0
            || settings.frames > i32::MAX as usize
            || settings.fps == 0
            || settings.fps > i32::MAX as usize
            || settings.smooth > 120
        {
            return Err(PyValueError::new_err(
                "invalid spectrum timing or smoothing",
            ));
        }
        let length = settings
            .frames
            .checked_mul(settings.sample_size * 2)
            .filter(|&len| len <= isize::MAX as usize)
            .ok_or_else(|| PyValueError::new_err("spectrum buffer is too large"))?;
        // PyBytes is not published until initialization completes. The safe PyO3
        // initializer grants exclusive buffer access while native work releases the GIL.
        PyBytes::new_with(py, length, |out| {
            py.detach(|| self.fill(&settings, sample_size, out))
        })
    }
}

#[pyfunction]
pub(crate) fn decode_audio(py: Python<'_>, source: PathBuf) -> PyResult<AudioAnalysis> {
    py.detach(|| {
        let data = PreloadedAudioData::decode_raw_file(None, &source.canonicalize()?)
            .map_err(media_error)?;
        if data.sample_rate == 0 || data.samples.is_empty() {
            return Err(PyValueError::new_err("audio contains no samples"));
        }
        Ok(AudioAnalysis {
            data: AudioData::Preloaded(data),
        })
    })
}
