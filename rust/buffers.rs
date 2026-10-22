//! Binary payloads borrowed from immutable Python bytes during compilation.

use fframes::{media::PreloadedAudioData, usvgr::PreloadedImageData};
use pyo3::{PyResult, exceptions::PyValueError, pybacked::PyBackedBytes};
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, path::PathBuf, sync::Arc};

pub(crate) type Buffers = HashMap<String, PyBackedBytes>;

#[derive(Deserialize, Serialize)]
#[serde(untagged)]
pub(crate) enum Source {
    File(PathBuf),
    Buffer(Buffer),
}

impl From<PathBuf> for Source {
    fn from(path: PathBuf) -> Self {
        Self::File(path)
    }
}

#[derive(Deserialize, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub(crate) enum Buffer {
    Pcm {
        data: String,
        sample_rate: u32,
        channels: usize,
        start: usize,
        end: Option<usize>,
    },
    #[serde(rename = "image_buffer")]
    Image {
        data: String,
        size: Option<[u32; 2]>,
    },
    VideoFrames {
        data: String,
        size: [u32; 2],
        fps: usize,
    },
}

fn data<'a>(buffers: &'a Buffers, key: &str) -> PyResult<&'a [u8]> {
    buffers
        .get(key)
        .map(|bytes| bytes.as_ref())
        .ok_or_else(|| PyValueError::new_err("binary media payload is missing from compilation"))
}

pub(crate) fn frame_bytes(size: [u32; 2]) -> PyResult<usize> {
    let [width, height] = size;
    if width == 0 || height == 0 || width > i32::MAX as u32 || height > i32::MAX as u32 {
        return Err(PyValueError::new_err(
            "buffer size must contain positive 32-bit dimensions",
        ));
    }
    (width as usize)
        .checked_mul(height as usize)
        .and_then(|v| v.checked_mul(4))
        .ok_or_else(|| PyValueError::new_err("buffer dimensions overflow"))
}

impl Source {
    pub fn texture(&self, srgb: bool, buffers: &Buffers) -> PyResult<fframes::three_d::Texture> {
        use fframes::three_d::Texture;
        let decode = |bytes: &[u8]| {
            (if srgb {
                Texture::decode(bytes)
            } else {
                Texture::decode_linear(bytes)
            })
            .map_err(crate::render::render_error)
        };
        match self {
            Self::File(path) => decode(&std::fs::read(path)?),
            Self::Buffer(Buffer::Image { data: key, size }) => {
                let bytes = data(buffers, key)?;
                if let Some(size) = size {
                    if bytes.len() != frame_bytes(*size)? {
                        return Err(PyValueError::new_err(
                            "image buffer length does not match its size",
                        ));
                    }
                    Ok(Texture::from_rgba8(size[0], size[1], bytes, srgb))
                } else {
                    decode(bytes)
                }
            }
            _ => Err(PyValueError::new_err(
                "texture requires a file or ImageBuffer",
            )),
        }
    }
    pub fn key(&self) -> PyResult<String> {
        match self {
            Self::File(path) => Ok(path.canonicalize()?.to_string_lossy().into_owned()),
            Self::Buffer(buffer) => {
                serde_json::to_string(buffer).map_err(crate::render::render_error)
            }
        }
    }

    pub fn image(&self, buffers: &Buffers) -> PyResult<Arc<PreloadedImageData>> {
        match self {
            Self::File(path) => {
                let path = path.canonicalize()?;
                let bytes = std::fs::read(&path)?;
                Ok(Arc::new(
                    fframes::media::decode_image(&path.to_string_lossy(), &bytes)
                        .map_err(crate::render::media_error)?,
                ))
            }
            Self::Buffer(Buffer::Image { data: key, size }) => {
                let bytes = data(buffers, key)?;
                if let Some(size) = size {
                    if bytes.len() != frame_bytes(*size)? {
                        return Err(PyValueError::new_err(
                            "image buffer length does not match its size",
                        ));
                    }
                    Ok(Arc::new(PreloadedImageData::new(
                        self.key()?,
                        size[0],
                        size[1],
                        bytes,
                    )))
                } else {
                    Ok(Arc::new(
                        fframes::media::decode_image(&self.key()?, bytes)
                            .map_err(crate::render::media_error)?,
                    ))
                }
            }
            _ => Err(PyValueError::new_err(
                "an image requires a file or ImageBuffer",
            )),
        }
    }

    pub fn audio(&self, buffers: &Buffers) -> PyResult<PreloadedAudioData<'static>> {
        match self {
            Self::File(path) => PreloadedAudioData::decode_raw_file_stereo(None, path)
                .map_err(crate::render::media_error),
            Self::Buffer(Buffer::Pcm {
                data: key,
                sample_rate,
                channels,
                start,
                end,
            }) => {
                if *sample_rate == 0 || ![1, 2].contains(channels) {
                    return Err(PyValueError::new_err(
                        "PCM requires a positive sample rate and one or two channels",
                    ));
                }
                let bytes = data(buffers, key)?;
                let stride = channels * 4;
                let end = end.unwrap_or(bytes.len() / stride);
                if !bytes.len().is_multiple_of(stride)
                    || start >= &end
                    || end > bytes.len() / stride
                {
                    return Err(PyValueError::new_err(
                        "invalid PCM sample range or incomplete frame",
                    ));
                }
                let mut left = Vec::with_capacity(end - start);
                let mut right = (*channels == 2).then(|| Vec::with_capacity(end - start));
                for frame in bytes[start * stride..end * stride].chunks_exact(stride) {
                    let sample = |offset| {
                        f32::from_le_bytes([
                            frame[offset],
                            frame[offset + 1],
                            frame[offset + 2],
                            frame[offset + 3],
                        ])
                    };
                    let l = sample(0);
                    let r = if *channels == 2 { sample(4) } else { l };
                    if !l.is_finite() || !r.is_finite() {
                        return Err(PyValueError::new_err(
                            "PCM samples must be finite float32 values",
                        ));
                    }
                    left.push(l);
                    if let Some(right) = &mut right {
                        right.push(r);
                    }
                }
                Ok(PreloadedAudioData {
                    samples: left.into(),
                    right: right.map(Into::into),
                    sample_rate: *sample_rate,
                })
            }
            _ => Err(PyValueError::new_err("audio requires a file or Pcm")),
        }
    }
}

pub(crate) struct FrameSequence {
    pub frames: Vec<Arc<PreloadedImageData>>,
    pub size: [u32; 2],
    pub fps: usize,
}

impl Buffer {
    pub fn video(&self, buffers: &Buffers) -> PyResult<FrameSequence> {
        let Self::VideoFrames {
            data: key,
            size,
            fps,
        } = self
        else {
            return Err(PyValueError::new_err(
                "video requires a file or VideoFrames",
            ));
        };
        let bytes = data(buffers, key)?;
        let stride = frame_bytes(*size)?;
        if *fps == 0 || bytes.is_empty() || !bytes.len().is_multiple_of(stride) {
            return Err(PyValueError::new_err(
                "video requires complete frames and positive fps",
            ));
        }
        let frames = bytes
            .chunks_exact(stride)
            .enumerate()
            .map(|(index, frame)| {
                Arc::new(PreloadedImageData::new(
                    format!("{key}:{size:?}:{index}"),
                    size[0],
                    size[1],
                    frame,
                ))
            })
            .collect();
        Ok(FrameSequence {
            frames,
            size: *size,
            fps: *fps,
        })
    }
}
