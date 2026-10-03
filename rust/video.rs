use crate::{
    backend::Backend,
    render::{Resources, render_error},
};
use serde::Deserialize;
use std::{collections::HashMap, path::PathBuf};

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
}

impl SvgVideo {
    fn tree(&self, index: usize) -> PyResult<usvgr::Tree> {
        let svg = self
            .frames
            .get(index)
            .ok_or_else(|| PyIndexError::new_err("frame index out of range"))?;
        let images = self
            .shaders
            .iter()
            .map(|(name, shader)| (name.clone(), shader.draw(index, self.fps)))
            .collect();
        let options = usvgr::Options {
            image_data: Some(&images),
            ..Default::default()
        };
        usvgr::Tree::from_str(svg, &options, &self.fonts)
            .map_err(|error| PyValueError::new_err(error.to_string()))
    }

    fn rasterize(&self, index: usize) -> PyResult<fframes::RgbaFrame> {
        let tree = self.tree(index)?;
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
            let timeline = ResolvedRenderingTimeline::<AudioTimelineSamples> {
                audio_map: None,
                scenes: None,
                duration_in_frames: self.frames.len(),
            };
            Resources {
                width: self.width,
                height: self.height,
                fps: self.fps,
                sample_rate: 48000,
                media: None,
                timeline: &timeline,
                backend: self.backend,
            }
            .render(
                |index, _| self.tree(index).map_err(render_error),
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

/// Store SVG frames and owned fonts/shaders for subsequent renders.
#[pyfunction]
#[pyo3(signature = (config, frames, shaders="[]"))]
pub(crate) fn compile_video(
    py: Python<'_>,
    config: &str,
    frames: Vec<String>,
    shaders: &str,
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
