//! Safe ownership boundary around upstream FFmpeg decoding; caches stay per worker.

use std::{collections::HashMap, path::PathBuf, sync::Arc};

use fframes::{media::FFmpegDecoder, usvgr::PreloadedImageData};
use pyo3::{exceptions::PyValueError, prelude::*};
use serde::Deserialize;

use crate::render::media_error;

#[derive(Deserialize)]
pub(crate) struct Input {
    pub source: crate::buffers::Source,
    pub offset: f64,
    pub r#loop: bool,
}

pub(crate) struct Source {
    path: PathBuf,
    frames: Option<crate::buffers::FrameSequence>,
    offset: f64,
    looping: bool,
    pub width: u32,
    pub height: u32,
    pub duration: f64,
    pub fps: f64,
}

#[derive(Default)]
pub(crate) struct Decoders(HashMap<(PathBuf, usize), FFmpegDecoder>);

impl Source {
    pub fn resize_buffers(mut self, size: Option<[u32; 2]>) -> PyResult<Self> {
        if let (Some(sequence), Some([width, height])) = (&mut self.frames, size) {
            crate::buffers::frame_bytes([width, height])?;
            if sequence.size != [width, height] {
                use fframes_skia_renderer::skia_safe::{
                    AlphaType, ColorType, FilterMode, ImageInfo, Pixmap,
                };
                let info = ImageInfo::new(
                    (width as i32, height as i32),
                    ColorType::RGBA8888,
                    AlphaType::Premul,
                    None,
                );
                for frame in &mut sequence.frames {
                    let source_info = ImageInfo::new(
                        (frame.width as i32, frame.height as i32),
                        ColorType::RGBA8888,
                        AlphaType::Premul,
                        None,
                    );
                    let mut pixels = frame.data.to_vec();
                    let source =
                        Pixmap::new(&source_info, &mut pixels, frame.width as usize * 4)
                            .ok_or_else(|| PyValueError::new_err("invalid video pixel buffer"))?;
                    let mut resized = vec![0; crate::buffers::frame_bytes([width, height])?];
                    let mut target = Pixmap::new(&info, &mut resized, width as usize * 4)
                        .ok_or_else(|| PyValueError::new_err("invalid resize dimensions"))?;
                    if !source.scale_pixels(&mut target, FilterMode::Linear) {
                        return Err(PyValueError::new_err("video buffer resize failed"));
                    }
                    *frame = Arc::new(PreloadedImageData {
                        id: format!("{}:{width}x{height}", frame.id),
                        data: resized.into(),
                        width,
                        height,
                    });
                }
                sequence.size = [width, height];
            }
        }
        Ok(self)
    }
    #[expect(
        unsafe_code,
        reason = "upstream exposes decoder construction and metadata through unsafe FFI"
    )]
    pub fn open(input: Input, fps: usize, buffers: &crate::buffers::Buffers) -> PyResult<Self> {
        if !input.offset.is_finite() || input.offset < 0. || input.offset > 86400. {
            return Err(PyValueError::new_err("invalid video source offset"));
        }
        let path = match input.source {
            crate::buffers::Source::File(path) => path.canonicalize()?,
            crate::buffers::Source::Buffer(buffer) => {
                let sequence = buffer.video(buffers)?;
                let duration = sequence.frames.len() as f64 / sequence.fps as f64;
                if input.offset >= duration {
                    return Err(PyValueError::new_err("video offset must precede EOF"));
                }
                return Ok(Self {
                    path: PathBuf::new(),
                    width: sequence.size[0],
                    height: sequence.size[1],
                    fps: sequence.fps as f64,
                    duration,
                    frames: Some(sequence),
                    offset: input.offset,
                    looping: input.r#loop,
                });
            }
        };
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
            frames: None,
            offset: input.offset,
            looping: input.r#loop,
            width,
            height,
            duration,
            fps: stream_fps,
        })
    }

    pub fn image(
        &self,
        seconds: f64,
        fps: usize,
        cache: &mut Decoders,
    ) -> PyResult<Option<Arc<PreloadedImageData>>> {
        self.image_resized(seconds, fps, cache, None)
    }

    #[expect(
        unsafe_code,
        reason = "upstream decoding and conversion require owned FFmpeg FFI access"
    )]
    pub fn image_resized(
        &self,
        seconds: f64,
        fps: usize,
        cache: &mut Decoders,
        options: Option<&fframes::media::FrameConvertOptions>,
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
        if let Some(sequence) = &self.frames {
            let index = ((time * sequence.fps as f64 - 1e-9).ceil().max(0.) as usize)
                .min(sequence.frames.len() - 1);
            return Ok(Some(Arc::clone(&sequence.frames[index])));
        }
        // SAFETY: each cache belongs to one rendering worker. No decoder or raw
        // frame crosses workers. Conversion completes before another decode and
        // returns owned pixel storage; only that immutable image is shared by Arc.
        unsafe {
            let index = (time * fps as f64 + 1e-9).floor() as i64;
            let decoder = match cache.0.entry((self.path.clone(), fps)) {
                std::collections::hash_map::Entry::Occupied(entry) => entry.into_mut(),
                std::collections::hash_map::Entry::Vacant(entry) => {
                    let mut decoder =
                        FFmpegDecoder::new(&self.path, fps, 1).map_err(media_error)?;
                    // Upstream only seeks large jumps after the first request.
                    // A worker or preview can begin minutes into the source.
                    if index > 2 * fps as i64 {
                        decoder.seek_to_offset(index).map_err(media_error)?;
                    }
                    entry.insert(decoder)
                }
            };
            if !decoder.decode_up_to(index).map_err(media_error)? {
                return Ok(None);
            }
            let image = decoder
                .get_raw_frame()
                .convert_last_decoded_frame_into_svg_image(options)
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
                source: source.into(),
                offset: 0.,
                r#loop: false,
            },
            30,
            &crate::buffers::Buffers::default(),
        )?;
        Ok((source.width, source.height, source.duration, source.fps))
    })
}
