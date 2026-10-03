//! Safe ownership boundary around upstream FFmpeg decoding; caches stay per worker.

use std::{collections::HashMap, path::PathBuf, sync::Arc};

use fframes::{media::FFmpegDecoder, usvgr::PreloadedImageData};
use pyo3::{exceptions::PyValueError, prelude::*};
use serde::Deserialize;

use crate::render::media_error;

#[derive(Deserialize)]
pub(crate) struct Input {
    pub source: PathBuf,
    pub offset: f64,
    pub r#loop: bool,
}

pub(crate) struct Source {
    path: PathBuf,
    offset: f64,
    looping: bool,
    pub width: u32,
    pub height: u32,
    pub duration: f64,
    pub fps: f64,
}

#[derive(Default)]
pub(crate) struct Decoders(HashMap<PathBuf, FFmpegDecoder>);

impl Source {
    #[expect(
        unsafe_code,
        reason = "upstream exposes decoder construction and metadata through unsafe FFI"
    )]
    pub fn open(input: Input, fps: usize) -> PyResult<Self> {
        if !input.offset.is_finite() || input.offset < 0. || input.offset > 86400. {
            return Err(PyValueError::new_err("invalid video source offset"));
        }
        let path = input.source.canonicalize()?;
        if !path.is_file() {
            return Err(PyValueError::new_err("video source must be a file"));
        }
        // SAFETY: a canonical local file and positive bounded fps are supplied.
        // The decoder is owned and accessed exclusively; the frame is inspected
        // while its decoder is alive and no decoding occurs concurrently.
        let (width, height, duration, stream_fps) = unsafe {
            let mut decoder = FFmpegDecoder::new(&path, fps, 1).map_err(media_error)?;
            if !decoder.decode_up_to(0).map_err(media_error)? {
                return Err(PyValueError::new_err("video contains no decodable frames"));
            }
            let frame = decoder.get_raw_frame();
            (
                frame.get_stream_width(),
                frame.get_stream_height(),
                f64::from(frame.get_stream_duration_in_frames()),
                f64::from(frame.get_stream_fps()),
            )
        };
        if width == 0
            || height == 0
            || !duration.is_finite()
            || duration <= 0.
            || !stream_fps.is_finite()
            || stream_fps <= 0.
            || input.offset >= duration
        {
            return Err(PyValueError::new_err(
                "invalid video metadata or offset beyond EOF",
            ));
        }
        Ok(Self {
            path,
            offset: input.offset,
            looping: input.r#loop,
            width,
            height,
            duration,
            fps: stream_fps,
        })
    }

    #[expect(
        unsafe_code,
        reason = "upstream exposes frame decode/conversion only through unsafe FFI"
    )]
    pub fn image(
        &self,
        seconds: f64,
        fps: usize,
        cache: &mut Decoders,
    ) -> PyResult<Option<Arc<PreloadedImageData>>> {
        if seconds < 0. {
            return Ok(None);
        }
        let mut time = self.offset + seconds;
        if self.looping {
            time = self.offset + seconds % (self.duration - self.offset);
        } else if time >= self.duration {
            return Ok(None);
        }
        // SAFETY: each cache belongs to one rendering worker. No decoder or raw
        // frame crosses workers. Conversion completes before another decode and
        // returns owned pixel storage; only that immutable image is shared by Arc.
        unsafe {
            let decoder = match cache.0.entry(self.path.clone()) {
                std::collections::hash_map::Entry::Occupied(entry) => entry.into_mut(),
                std::collections::hash_map::Entry::Vacant(entry) => {
                    entry.insert(FFmpegDecoder::new(&self.path, fps, 1).map_err(media_error)?)
                }
            };
            let index = (time * fps as f64 + 1e-9).floor() as i64;
            if !decoder.decode_up_to(index).map_err(media_error)? {
                return Ok(None);
            }
            let image = decoder
                .get_raw_frame()
                .convert_last_decoded_frame_into_svg_image(None)
                .map_err(media_error)?;
            Ok(Some(image))
        }
    }
}

#[pyfunction]
pub(crate) fn video_info(py: Python<'_>, source: PathBuf) -> PyResult<(u32, u32, f64, f64)> {
    py.detach(|| {
        let source = Source::open(
            Input {
                source,
                offset: 0.,
                r#loop: false,
            },
            30,
        )?;
        Ok((source.width, source.height, source.duration, source.fps))
    })
}
