//! Evaluate Lottie with upstream velato/SVGr support and the active rasterizer.

use crate::render::{FrameCache, render_error};
use fframes::{SvgrRasterizer, usvgr};
use pyo3::{
    exceptions::{PyRuntimeError, PyValueError},
    prelude::*,
};
use serde::Deserialize;
use std::{path::PathBuf, sync::Arc};

#[derive(Deserialize)]
pub(crate) struct Input {
    source: PathBuf,
    offset: f64,
    speed: f64,
    r#loop: bool,
}

pub(crate) struct Program {
    animation: fframes::Lottie,
    offset: f64,
    speed: f64,
    looping: bool,
    size: [u32; 2],
    fonts: usvgr::fontdb::Database,
}

impl Program {
    pub fn compile(input: Input, size: [u32; 2]) -> PyResult<Self> {
        let animation = load(&input.source)?;
        if input.offset >= f64::from(animation.seconds()) || input.offset < 0. || input.speed <= 0.
        {
            return Err(PyValueError::new_err(
                "Lottie offset must precede EOF and speed must be positive",
            ));
        }
        Ok(Self {
            animation,
            offset: input.offset,
            speed: input.speed,
            looping: input.r#loop,
            size,
            fonts: usvgr::fontdb::Database::new(),
        })
    }

    pub fn image(
        &self,
        time: f64,
        cache: &mut FrameCache,
        rasterizer: &crate::backend::Rasterizer<'_>,
    ) -> PyResult<Arc<usvgr::PreloadedImageData>> {
        let duration = f64::from(self.animation.seconds()) - self.offset;
        let seconds = time.max(0.) * self.speed;
        let seconds = self.offset
            + if self.looping {
                seconds.rem_euclid(duration)
            } else {
                seconds
            };
        let content = self.animation.render_at(seconds as f32);
        let width = self.animation.width();
        let height = self.animation.height();
        let tree = fframes::svgr!(<svg width={width} height={height}>{content}</svg>)
            .into_svg_tree(&usvgr::Options::default(), &mut cache.trees, &self.fonts)
            .map_err(render_error)?;
        rasterizer
            .rasterize(&tree, self.size[0], self.size[1])
            .map(|image| image.href())
            .ok_or_else(|| PyRuntimeError::new_err("Lottie rasterization failed"))
    }
}

fn load(source: &std::path::Path) -> PyResult<fframes::Lottie> {
    let animation = fframes::Lottie::parse(std::fs::read(source)?).map_err(render_error)?;
    if animation.width() == 0
        || animation.height() == 0
        || !animation.seconds().is_finite()
        || animation.seconds() <= 0.
    {
        return Err(PyValueError::new_err(
            "Lottie requires a positive canvas size, frame rate and duration",
        ));
    }
    Ok(animation)
}

#[derive(Deserialize)]
pub(crate) struct BindingInput {
    name: String,
    animation: Input,
    size: [u32; 2],
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
            name: format!("lottie:{}", self.name),
            program: Program::compile(self.animation, self.size)?,
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
        self.program.image(time, cache, rasterizer).map(Some)
    }
}

#[pyfunction]
pub(crate) fn lottie_info(py: Python<'_>, source: PathBuf) -> PyResult<(usize, usize, f32)> {
    py.detach(|| load(&source).map(|l| (l.width(), l.height(), l.seconds())))
}
