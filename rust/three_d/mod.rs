//! Native scene compilation and rendering, shared by SVG and compose layers.

mod animation;
pub(crate) mod assets;
mod camera;
mod environment;
mod geometry;
mod light;
mod material;
mod scene;
mod texture;
mod values;

use crate::render::{FrameCache, render_error};
use fframes::{
    media::ImageData,
    three_d::{self as d, Vec3},
    usvgr,
};
use pyo3::{exceptions::PyValueError, prelude::*, types::PyBytes};
use serde::Deserialize;
use std::sync::Arc;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Input {
    scene: scene::Input,
    camera: camera::Input,
    pub size: [u32; 2],
    fps: usize,
    settings: Settings,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Settings {
    device: Device,
    antialias: bool,
    exposure: f32,
    tone_mapping: Tone,
    bloom: Option<Bloom>,
    motion_samples: usize,
    shutter: f64,
}

#[derive(Deserialize)]
#[serde(rename_all = "lowercase")]
enum Device {
    Cpu,
    Gpu,
    Auto,
}

#[derive(Deserialize)]
#[serde(rename_all = "lowercase")]
enum Tone {
    Aces,
    Neutral,
    Linear,
}

#[derive(Deserialize)]
struct Bloom {
    strength: f32,
    radius: f32,
    threshold: f32,
}

pub(crate) struct Program {
    scene: scene::Program,
    camera: camera::Program,
    renderer: d::Renderer,
    motion_samples: usize,
    shutter_seconds: f64,
}

impl Program {
    pub fn on_timeline(mut input: Input, fps: usize) -> PyResult<Self> {
        // Embedded scenes inherit their output clock for clip sampling and shutter duration.
        input.fps = fps;
        Self::compile(input)
    }
    pub fn compile(input: Input) -> PyResult<Self> {
        let [width, height] = input.size;
        if width == 0
            || height == 0
            || width > i32::MAX as u32
            || height > i32::MAX as u32
            || input.fps == 0
            || input.settings.motion_samples == 0
            || input.settings.motion_samples > 64
        {
            return Err(PyValueError::new_err(
                "invalid 3D resolution, fps or motion sample count",
            ));
        }
        let settings = input.settings;
        let mut renderer = d::Renderer::new(width, height);
        renderer.gpu = !matches!(settings.device, Device::Cpu);
        if matches!(settings.device, Device::Gpu) && !renderer.uses_gpu() {
            return Err(PyValueError::new_err(
                "3D device='gpu' requested but no compatible GPU was found; use 'cpu' or 'auto'",
            ));
        }
        renderer.antialias = settings.antialias;
        renderer.exposure = settings.exposure;
        renderer.tone_mapping = match settings.tone_mapping {
            Tone::Aces => d::ToneMapping::Aces,
            Tone::Neutral => d::ToneMapping::Neutral,
            Tone::Linear => d::ToneMapping::Linear,
        };
        renderer.bloom = settings.bloom.map(|b| d::Bloom {
            strength: b.strength,
            radius: b.radius,
            threshold: b.threshold,
        });
        let scene = input.scene.compile(input.fps)?;
        if let Some(message) = scene.gpu_limits()? {
            match settings.device {
                Device::Gpu => return Err(PyValueError::new_err(message)),
                Device::Auto => renderer.gpu = false,
                Device::Cpu => {}
            }
        }
        Ok(Self {
            scene,
            camera: input.camera.compile()?,
            renderer,
            motion_samples: settings.motion_samples,
            shutter_seconds: settings.shutter / input.fps as f64,
        })
    }

    fn moments(
        &self,
        time: f64,
        cache: &mut FrameCache,
        rasterizer: &crate::backend::Rasterizer<'_>,
    ) -> PyResult<Vec<(d::Scene, d::Camera)>> {
        (0..self.motion_samples)
            .map(|i| {
                let offset = if self.motion_samples == 1 {
                    0.
                } else {
                    (i as f64 + 0.5) / self.motion_samples as f64 - 0.5
                };
                let t = (time + offset * self.shutter_seconds).max(0.);
                Ok((self.scene.at(t, cache, rasterizer)?, self.camera.at(t)?))
            })
            .collect()
    }

    pub fn image(
        &self,
        time: f64,
        cache: &mut FrameCache,
        rasterizer: &crate::backend::Rasterizer<'_>,
    ) -> PyResult<ImageData<'static>> {
        let moments = self.moments(time, cache, rasterizer)?;
        if !rasterizer.gpu_layers {
            return Ok(self.render_pixels(&moments).into_image());
        }
        if let [(scene, camera)] = moments.as_slice() {
            return Ok(self.renderer.render(scene, camera));
        }
        // The upstream callback cannot return errors. Resolve fallible media first;
        // these clones share geometry and texture allocations with the posed moments.
        let mut index = 0;
        Ok(self.renderer.render_motion_blur(moments.len(), |_| {
            let result = moments[index].clone();
            index += 1;
            result
        }))
    }

    fn pixels(&self, time: f64) -> PyResult<d::Pixels> {
        check_time(time)?;
        let moments = self.moments(
            time,
            &mut FrameCache::default(),
            &crate::backend::Rasterizer::cpu(),
        )?;
        Ok(self.render_pixels(&moments))
    }

    fn render_pixels(&self, moments: &[(d::Scene, d::Camera)]) -> d::Pixels {
        if let [(scene, camera)] = moments {
            return self.renderer.render_pixels(scene, camera);
        }
        let mut index = 0;
        self.renderer.render_motion_blur_pixels(moments.len(), |_| {
            let result = moments[index].clone();
            index += 1;
            result
        })
    }
}

fn check_time(time: f64) -> PyResult<()> {
    if !time.is_finite() || !(0. ..=86400.).contains(&time) {
        return Err(PyValueError::new_err(
            "3D time must be finite and between 0 and 86400 seconds",
        ));
    }
    Ok(())
}

#[derive(Deserialize)]
pub(crate) struct BindingInput {
    name: String,
    renderer: Input,
    start_at: f64,
    duration: Option<f64>,
}

pub(crate) struct Binding {
    pub name: String,
    program: Program,
    span: crate::values::FrameSpan,
}

impl BindingInput {
    pub fn compile(self, fps: usize) -> PyResult<Binding> {
        Ok(Binding {
            name: format!("scene:{}", self.name),
            program: Program::on_timeline(self.renderer, fps)?,
            span: crate::values::FrameSpan::new(self.start_at, self.duration, fps)?,
        })
    }
}

impl Binding {
    pub fn at(
        &self,
        time: f64,
        cache: &mut FrameCache,
        rasterizer: &crate::backend::Rasterizer<'_>,
    ) -> PyResult<Option<Arc<usvgr::PreloadedImageData>>> {
        let Some(time) = self.span.local_time(time) else {
            return Ok(None);
        };
        Ok(Some(self.program.image(time, cache, rasterizer)?.href()))
    }
}

/// Compiled 3D descriptions with no Python callbacks in the rendering loop.
#[pyclass(frozen, module = "fframes._native")]
pub(crate) struct Renderer3D {
    program: Program,
}

#[pymethods]
impl Renderer3D {
    fn rgba<'py>(&self, py: Python<'py>, time: f64) -> PyResult<Bound<'py, PyBytes>> {
        let pixels = py.detach(|| self.program.pixels(time).map(|p| p.to_straight_rgba()))?;
        Ok(PyBytes::new(py, &pixels))
    }

    fn uses_gpu(&self, py: Python<'_>) -> bool {
        py.detach(|| self.program.renderer.uses_gpu())
    }

    fn project(
        &self,
        py: Python<'_>,
        point: [f32; 3],
        time: f64,
    ) -> PyResult<Option<(f32, f32, f32)>> {
        check_time(time)?;
        py.detach(|| {
            Ok(self
                .program
                .camera
                .at(time)?
                .project(
                    Vec3::from(point),
                    self.program.renderer.width as f32,
                    self.program.renderer.height as f32,
                )
                .map(|v| (v.x, v.y, v.z)))
        })
    }

    fn world_position(&self, py: Python<'_>, name: &str, time: f64) -> PyResult<(f32, f32, f32)> {
        check_time(time)?;
        py.detach(|| {
            let node = self.program.scene.node(name)?;
            let scene = self.program.scene.pose(time)?;
            let v = scene.world_position(node);
            Ok((v.x, v.y, v.z))
        })
    }

    fn local_to_world(
        &self,
        py: Python<'_>,
        name: &str,
        point: [f32; 3],
        time: f64,
    ) -> PyResult<(f32, f32, f32)> {
        check_time(time)?;
        py.detach(|| {
            let node = self.program.scene.node(name)?;
            let scene = self.program.scene.pose(time)?;
            let p = scene.local_to_world(node, point.into());
            Ok((p.x, p.y, p.z))
        })
    }

    fn world_matrix(&self, py: Python<'_>, name: &str, time: f64) -> PyResult<Vec<f32>> {
        check_time(time)?;
        py.detach(|| {
            let node = self.program.scene.node(name)?;
            Ok(self
                .program
                .scene
                .pose(time)?
                .world_matrix(node)
                .to_cols_array()
                .to_vec())
        })
    }

    fn bounds(
        &self,
        py: Python<'_>,
        name: &str,
        time: f64,
    ) -> PyResult<Option<([f32; 3], [f32; 3])>> {
        check_time(time)?;
        py.detach(|| {
            let node = self.program.scene.node(name)?;
            let bounds = self.program.scene.pose(time)?.bounds(node);
            Ok((bounds.min.is_finite() && bounds.max.is_finite())
                .then(|| (bounds.min.to_array(), bounds.max.to_array())))
        })
    }

    fn pixel_size(&self, py: Python<'_>, point: [f32; 3], size: f32, time: f64) -> PyResult<f32> {
        check_time(time)?;
        py.detach(|| {
            Ok(self.program.camera.at(time)?.pixel_size(
                point.into(),
                size,
                self.program.renderer.height as f32,
            ))
        })
    }
}

#[pyfunction]
pub(crate) fn compile_3d(py: Python<'_>, plan: &str) -> PyResult<Renderer3D> {
    py.detach(|| {
        let input = serde_json::from_str(plan).map_err(render_error)?;
        Ok(Renderer3D {
            program: Program::compile(input)?,
        })
    })
}
