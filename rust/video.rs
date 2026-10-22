use crate::{
    backend::Backend,
    render::{FrameCache, Resources, render_error},
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
    shaders: HashMap<String, Shader>,
    media: fframes::DynamicMediaProvider<'static>,
    timeline: ResolvedRenderingTimeline<'static, AudioTimelineSamples>,
    images: HashMap<String, Arc<usvgr::PreloadedImageData>>,
    clips: Vec<Clip>,
    scenes: Vec<crate::three_d::Binding>,
    lotties: Vec<crate::lottie::Binding>,
    chapters: Vec<crate::timing::SceneRange>,
}

struct Clip {
    name: String,
    source: crate::clips::Source,
    span: crate::values::FrameSpan,
}

impl crate::inspection::Source for SvgVideo {
    fn chapters(&self) -> &[crate::timing::SceneRange] {
        &self.chapters
    }
    fn resources(&self) -> Resources<'_> {
        Resources {
            backend: self.backend,
            width: self.width,
            height: self.height,
            fps: self.fps,
            sample_rate: crate::audio::SAMPLE_RATE,
            media: Some(&self.media),
            timeline: &self.timeline,
        }
    }
    fn size(&self) -> [u32; 2] {
        [self.width, self.height]
    }
    fn fps(&self) -> usize {
        self.fps
    }
    fn count(&self) -> usize {
        self.frames.len()
    }
    fn backend(&self) -> Backend {
        self.backend
    }
    fn fonts(&self) -> &usvgr::fontdb::Database {
        &self.fonts
    }
    fn tree(
        &self,
        index: usize,
        cache: &mut FrameCache,
        rasterizer: &crate::backend::Rasterizer<'_>,
    ) -> PyResult<usvgr::Tree> {
        self.tree(index, cache, rasterizer)
    }
}

struct Shader {
    program: crate::shader::Program,
    first: usize,
    end: usize,
}

impl SvgVideo {
    pub(crate) fn tree(
        &self,
        index: usize,
        cache: &mut FrameCache,
        rasterizer: &crate::backend::Rasterizer<'_>,
    ) -> PyResult<usvgr::Tree> {
        self.tree_at(index, index as f64 / self.fps as f64, cache, rasterizer)
    }

    pub(crate) fn tree_at(
        &self,
        index: usize,
        time: f64,
        cache: &mut FrameCache,
        rasterizer: &crate::backend::Rasterizer<'_>,
    ) -> PyResult<usvgr::Tree> {
        let svg = self
            .frames
            .get(index)
            .ok_or_else(|| PyIndexError::new_err("frame index out of range"))?;
        let index = (time * self.fps as f64 + 1e-9).floor() as usize;
        let mut images = HashMap::new();
        for (name, shader) in &self.shaders {
            if index >= shader.first && index < shader.end {
                images.insert(
                    name.clone(),
                    shader
                        .program
                        .draw(index - shader.first, self.fps, &mut cache.decoders)?,
                );
            }
        }
        images.extend(
            self.images
                .iter()
                .map(|(name, image)| (name.clone(), Arc::clone(image))),
        );
        for scene in &self.scenes {
            if let Some(image) = scene.at(time, cache, rasterizer)? {
                images.insert(scene.name.clone(), image);
            }
        }
        for lottie in &self.lotties {
            if let Some(image) = lottie.at(time, cache, rasterizer)? {
                images.insert(lottie.name.clone(), image);
            }
        }
        for clip in &self.clips {
            if let Some(local_time) = clip.span.local_time(time)
                && let Some(image) = clip
                    .source
                    .image(local_time, self.fps, &mut cache.decoders)?
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
        let device = crate::backend::Device::new(self.backend, self.width, self.height)?;
        let tree = self.tree(index, &mut FrameCache::default(), &device.rasterizer())?;
        device
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

    #[pyo3(signature = (mix=None))]
    fn audio_samples<'py>(
        &self,
        py: Python<'py>,
        mix: Option<&str>,
    ) -> PyResult<Bound<'py, PyBytes>> {
        let mix = crate::audio::Mix::parse(mix)?;
        let bytes = py.detach(|| {
            crate::audio::samples(
                &self.media,
                self.timeline.audio_map.as_ref(),
                self.frames.len(),
                self.fps,
                mix,
            )
        });
        Ok(PyBytes::new(py, &bytes))
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

    /// Encode the selected frames and replace the destination on success.
    #[pyo3(signature = (path, directory, options, control=None))]
    fn render(
        &self,
        py: Python<'_>,
        path: PathBuf,
        directory: PathBuf,
        options: &str,
        control: Option<&crate::progress::RenderControl>,
    ) -> PyResult<()> {
        let encoding = crate::render::Encoding::parse(options)?;
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
                |time, cache, rasterizer| {
                    let index = (time * self.fps as f64 + 1e-9).floor() as usize;
                    self.tree_at(index.min(self.frames.len() - 1), time, cache, rasterizer)
                },
                path,
                directory,
                &encoding,
                control,
            )
        })
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Config {
    pub width: u32,
    pub height: u32,
    pub fps: usize,
    pub load_system_fonts: bool,
    pub fonts: Vec<PathBuf>,
    pub backend: Backend,
}

#[derive(Deserialize)]
pub(crate) struct Binding {
    name: String,
    shader: crate::shader::Input,
    #[serde(default)]
    start_at: f64,
    duration: Option<f64>,
}

#[derive(Default, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub(crate) struct Media {
    pub chapters: Vec<crate::timing::SceneRange>,
    pub audio: Vec<crate::audio::Input>,
    pub images: Vec<ImageBinding>,
    pub clips: Vec<VideoBinding>,
    pub scenes: Vec<crate::three_d::BindingInput>,
    pub lotties: Vec<crate::lottie::BindingInput>,
}

#[derive(Deserialize)]
pub(crate) struct ImageBinding {
    name: String,
    source: crate::buffers::Source,
}

#[derive(Deserialize)]
pub(crate) struct VideoBinding {
    name: String,
    start_at: f64,
    duration: Option<f64>,
    #[serde(flatten)]
    input: crate::clips::Input,
}

/// Store SVG frames and owned fonts/shaders for subsequent renders.
#[pyfunction]
#[pyo3(signature = (config, frames, shaders="[]", media="{}", buffers=None))]
pub(crate) fn compile_video(
    py: Python<'_>,
    config: &str,
    frames: Vec<String>,
    shaders: &str,
    media: &str,
    buffers: Option<crate::buffers::Buffers>,
) -> PyResult<SvgVideo> {
    let config: Config =
        serde_json::from_str(config).map_err(|err| PyValueError::new_err(err.to_string()))?;
    let shaders =
        serde_json::from_str(shaders).map_err(|err| PyValueError::new_err(err.to_string()))?;
    let media =
        serde_json::from_str(media).map_err(|err| PyValueError::new_err(err.to_string()))?;
    let buffers = buffers.unwrap_or_default();
    py.detach(|| build(config, frames, shaders, media, None, &buffers))
}

pub(crate) fn build(
    config: Config,
    frames: Vec<String>,
    shaders: Vec<Binding>,
    inputs: Media,
    duration: Option<f64>,
    buffers: &crate::buffers::Buffers,
) -> PyResult<SvgVideo> {
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
    if !shaders.is_empty() && config.backend == Backend::Cpu {
        return Err(PyValueError::new_err("shaders require a Skia backend"));
    }
    let duration = duration.unwrap_or(frames.len() as f64 / config.fps as f64);
    let sounds = inputs
        .audio
        .into_iter()
        .map(|input| input.sound(duration))
        .collect::<PyResult<Vec<_>>>()?
        .into_iter()
        .flatten()
        .collect();
    let soundtrack = crate::audio::prepare(sounds, duration, buffers)?;
    let mut images = HashMap::new();
    for binding in inputs.images {
        let image = binding.source.image(buffers)?;
        if images
            .insert(format!("image:{}", binding.name), image)
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
            source: crate::clips::Source::open(binding.input, config.fps, buffers)?,
            span: crate::values::FrameSpan::new(binding.start_at, binding.duration, config.fps)?,
        });
    }
    let mut programs = HashMap::new();
    for binding in shaders {
        if !binding.start_at.is_finite()
            || binding.start_at < 0.
            || binding.start_at > 86400.
            || binding
                .duration
                .is_some_and(|d| !d.is_finite() || d <= 0. || d > 86400.)
        {
            return Err(PyValueError::new_err("invalid shader binding interval"));
        }
        let frame_at = |time: f64| (time * config.fps as f64 - 1e-9).ceil().max(0.) as usize;
        let program = Shader {
            program: crate::shader::Program::compile(binding.shader, config.fps, buffers)?,
            first: frame_at(binding.start_at),
            end: frame_at(
                binding
                    .duration
                    .map_or(duration, |d| (binding.start_at + d).min(duration)),
            ),
        };
        let name = format!("shader:{}", binding.name);
        if programs.insert(name, program).is_some() {
            return Err(PyValueError::new_err("duplicate shader binding"));
        }
    }
    crate::timing::validate(&inputs.chapters, frames.len())?;
    Ok(SvgVideo {
        chapters: inputs.chapters,
        lotties: {
            let mut names = std::collections::HashSet::new();
            inputs
                .lotties
                .into_iter()
                .map(|input| {
                    let binding = input.compile(config.fps)?;
                    if !names.insert(binding.name.clone()) {
                        return Err(PyValueError::new_err("duplicate lottie binding"));
                    }
                    Ok(binding)
                })
                .collect::<PyResult<_>>()?
        },
        scenes: {
            let mut names = std::collections::HashSet::new();
            inputs
                .scenes
                .into_iter()
                .map(|input| {
                    let binding = input.compile(config.fps, buffers)?;
                    if !names.insert(binding.name.clone()) {
                        return Err(PyValueError::new_err("duplicate scene binding"));
                    }
                    Ok(binding)
                })
                .collect::<PyResult<_>>()?
        },
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
}
