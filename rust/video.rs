use crate::{
    backend::Backend,
    render::{FrameCache, Resources, media_error, render_error},
};
use serde::Deserialize;
use std::{collections::HashMap, path::PathBuf, sync::Arc};

use fframes::{AudioTimelineSamples, Color, ResolvedRenderingTimeline, usvgr};
use pyo3::{
    exceptions::{PyIndexError, PyValueError},
    prelude::*,
    types::PyBytes,
};

/// Owned SVG frames and font data, reusable for CPU image or video output.
#[pyclass(frozen, module = "fframes._native")]
pub(crate) struct SvgVideo {
    width: u32,
    height: u32,
    fps: usize,
    frames: Vec<String>,
    fonts: usvgr::fontdb::Database,
    backend: Backend,
    shaders: HashMap<String, crate::shader::Program>,
    media: fframes::DynamicMediaProvider<'static>,
    timeline: ResolvedRenderingTimeline<'static, AudioTimelineSamples>,
    images: HashMap<String, Arc<usvgr::PreloadedImageData>>,
    clips: Vec<Clip>,
}

struct Clip {
    name: String,
    source: crate::clips::Source,
    start: f64,
    end: f64,
}

impl SvgVideo {
    fn tree(&self, index: usize, cache: &mut FrameCache) -> PyResult<usvgr::Tree> {
        let svg = self
            .frames
            .get(index)
            .ok_or_else(|| PyIndexError::new_err("frame index out of range"))?;
        let mut images: HashMap<_, _> = self
            .shaders
            .iter()
            .map(|(name, shader)| (name.clone(), shader.draw(index, self.fps)))
            .collect();
        images.extend(
            self.images
                .iter()
                .map(|(name, image)| (name.clone(), Arc::clone(image))),
        );
        let time = index as f64 / self.fps as f64;
        for clip in &self.clips {
            if time >= clip.start
                && time < clip.end
                && let Some(image) =
                    clip.source
                        .image(time - clip.start, self.fps, &mut cache.decoders)?
            {
                images.insert(clip.name.clone(), image);
            }
        }
        let options = usvgr::Options {
            image_data: Some(&images),
            ..Default::default()
        };
        usvgr::Tree::from_str(svg, &options, &self.fonts)
            .map_err(|error| PyValueError::new_err(error.to_string()))
    }

    fn rasterize(&self, index: usize) -> PyResult<fframes::RgbaFrame> {
        let tree = self.tree(index, &mut FrameCache::default())?;
        crate::backend::Device::new(self.backend, self.width, self.height)?
            .frame()
            .render_tree(&tree, Color::TRANSPARENT, self.width, self.height)
            .map_err(render_error)
    }
}

#[pymethods]
impl SvgVideo {
    fn __len__(&self) -> usize {
        self.frames.len()
    }

    fn audio_samples<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        let bytes = py.detach(|| {
            crate::audio::samples(
                &self.media,
                self.timeline.audio_map.as_ref(),
                self.frames.len(),
                self.fps,
            )
        });
        PyBytes::new(py, &bytes)
    }

    /// Rasterize one frame to straight-alpha RGBA bytes.
    fn rgba<'py>(&self, py: Python<'py>, index: usize) -> PyResult<Bound<'py, PyBytes>> {
        let frame = py.detach(|| self.rasterize(index))?;
        Ok(PyBytes::new(py, &frame.pixels))
    }

    /// Rasterize one frame and save it as PNG, releasing the GIL during I/O.
    fn save_png(&self, py: Python<'_>, index: usize, path: PathBuf) -> PyResult<()> {
        py.detach(|| self.rasterize(index)?.save_png(path).map_err(render_error))
    }

    /// Encode all frames into a temporary file and replace the destination on success.
    #[pyo3(signature = (path, directory, encoder, concurrency, bitrate=8_000_000))]
    fn render(
        &self,
        py: Python<'_>,
        path: PathBuf,
        directory: PathBuf,
        encoder: &str,
        concurrency: usize,
        bitrate: i64,
    ) -> PyResult<()> {
        let staged = directory
            .join("output")
            .with_extension(path.extension().unwrap_or_default());
        py.detach(|| {
            Resources {
                width: self.width,
                height: self.height,
                fps: self.fps,
                sample_rate: 48000,
                media: Some(&self.media),
                timeline: &self.timeline,
                backend: self.backend,
            }
            .render(
                |index, cache| self.tree(index, cache).map_err(render_error),
                staged.clone(),
                directory,
                encoder,
                concurrency,
                bitrate,
            )?;
            std::fs::rename(staged, path)?;
            Ok(())
        })
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    width: u32,
    height: u32,
    fps: usize,
    load_system_fonts: bool,
    fonts: Vec<PathBuf>,
    backend: Backend,
}

#[derive(Deserialize)]
struct Binding {
    name: String,
    shader: crate::shader::Input,
}

#[derive(Default, Deserialize)]
#[serde(default, deny_unknown_fields)]
struct Media {
    audio: Vec<crate::audio::Input>,
    images: Vec<ImageBinding>,
    clips: Vec<VideoBinding>,
}

#[derive(Deserialize)]
struct ImageBinding {
    name: String,
    source: PathBuf,
}

#[derive(Deserialize)]
struct VideoBinding {
    name: String,
    start_at: f64,
    duration: Option<f64>,
    #[serde(flatten)]
    input: crate::clips::Input,
}

/// Store SVG frames and owned fonts/shaders for subsequent renders.
#[pyfunction]
#[pyo3(signature = (config, frames, shaders="[]", media="{}"))]
pub(crate) fn compile_video(
    py: Python<'_>,
    config: &str,
    frames: Vec<String>,
    shaders: &str,
    media: &str,
) -> PyResult<SvgVideo> {
    let config: Config =
        serde_json::from_str(config).map_err(|err| PyValueError::new_err(err.to_string()))?;
    if config.width == 0
        || config.height == 0
        || config.width > i32::MAX as u32
        || config.height > i32::MAX as u32
        || config.fps == 0
        || config.fps > i32::MAX as usize
        || frames.is_empty()
    {
        return Err(PyValueError::new_err(
            "invalid dimensions, fps or empty frames",
        ));
    }
    let shaders: Vec<Binding> =
        serde_json::from_str(shaders).map_err(|err| PyValueError::new_err(err.to_string()))?;
    if !shaders.is_empty() && config.backend == Backend::Cpu {
        return Err(PyValueError::new_err("shaders require a Skia backend"));
    }
    py.detach(|| {
        let duration = frames.len() as f64 / config.fps as f64;
        let inputs: Media =
            serde_json::from_str(media).map_err(|err| PyValueError::new_err(err.to_string()))?;
        let sounds = inputs
            .audio
            .into_iter()
            .map(|input| input.sound(duration))
            .collect::<PyResult<Vec<_>>>()?
            .into_iter()
            .flatten()
            .collect();
        let soundtrack = crate::audio::prepare(sounds, duration)?;
        let mut images = HashMap::new();
        for binding in inputs.images {
            let path = binding.source.canonicalize()?;
            let bytes = std::fs::read(&path)?;
            let image = fframes::media::decode_image(&path.to_string_lossy(), &bytes)
                .map_err(media_error)?;
            if images
                .insert(format!("image:{}", binding.name), Arc::new(image))
                .is_some()
            {
                return Err(PyValueError::new_err("duplicate image binding"));
            }
        }
        let mut names = std::collections::HashSet::new();
        let mut clips = Vec::new();
        for binding in inputs.clips {
            if !names.insert(binding.name.clone()) {
                return Err(PyValueError::new_err("duplicate video binding"));
            }
            if !binding.start_at.is_finite()
                || binding.start_at < 0.
                || binding.start_at > 86400.
                || binding
                    .duration
                    .is_some_and(|d| !d.is_finite() || d <= 0. || d > 86400.)
            {
                return Err(PyValueError::new_err("invalid video binding interval"));
            }
            if binding.start_at >= duration {
                continue;
            }
            clips.push(Clip {
                name: format!("video:{}", binding.name),
                source: crate::clips::Source::open(binding.input, config.fps)?,
                start: binding.start_at,
                end: binding
                    .duration
                    .map_or(duration, |d| (binding.start_at + d).min(duration)),
            });
        }
        let mut programs = HashMap::new();
        for binding in shaders {
            let name = format!("shader:{}", binding.name);
            if programs
                .insert(name, crate::shader::Program::compile(binding.shader)?)
                .is_some()
            {
                return Err(PyValueError::new_err("duplicate shader binding"));
            }
        }
        Ok(SvgVideo {
            images,
            clips,
            media: soundtrack.media,
            timeline: ResolvedRenderingTimeline {
                audio_map: soundtrack.map,
                scenes: None,
                duration_in_frames: frames.len(),
            },
            width: config.width,
            height: config.height,
            fps: config.fps,
            frames,
            fonts: crate::fonts::load(&config.fonts, config.load_system_fonts)?,
            backend: config.backend,
            shaders: programs,
        })
    })
}
