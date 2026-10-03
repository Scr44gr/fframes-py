//! Backend selection shared by raw SVG and component rendering.

use crate::render::render_error;
use fframes::{
    CpuFrameRenderer, EncoderFrameRenderer, EncoderInput, FrameRenderer,
    cpu::CpuEncoderFrameRenderer,
};
use fframes_skia_renderer::{
    SkiaCpuCtx, SkiaEncoderFrameRenderer, SkiaFrameExport, SkiaFrameRenderer,
};
use pyo3::{PyResult, exceptions::PyValueError};
use serde::Deserialize;

#[derive(Clone, Copy, Default, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub(crate) enum Backend {
    #[default]
    Cpu,
    Skia,
    Vulkan,
    Metal,
}

pub(crate) enum Device {
    Cpu,
    Skia(SkiaCpuCtx),
    #[cfg(not(target_os = "macos"))]
    Vulkan(Box<fframes_skia_renderer::vulkan::SkiaVulkanCtx>),
    #[cfg(target_os = "macos")]
    Metal(Box<fframes_skia_renderer::metal::SkiaMetalCtx>),
}

impl Device {
    pub fn new(backend: Backend, width: u32, height: u32) -> PyResult<Self> {
        Ok(match backend {
            Backend::Cpu => Self::Cpu,
            Backend::Skia => Self::Skia(SkiaCpuCtx::new(width as usize, height as usize)),
            #[cfg(not(target_os = "macos"))]
            Backend::Vulkan => Self::Vulkan(Box::new(
                fframes_skia_renderer::vulkan::SkiaVulkanCtx::new(width as usize, height as usize)
                    .map_err(render_error)?,
            )),
            #[cfg(target_os = "macos")]
            Backend::Metal => Self::Metal(Box::new(
                fframes_skia_renderer::metal::SkiaMetalCtx::new(width as usize, height as usize)
                    .map_err(render_error)?,
            )),
            _ => {
                return Err(PyValueError::new_err(
                    "backend is not available on this platform",
                ));
            }
        })
    }

    pub fn frame(&self) -> Box<dyn FrameRenderer + '_> {
        match self {
            Self::Cpu => Box::new(CpuFrameRenderer::default()),
            Self::Skia(ctx) => Box::new(SkiaFrameRenderer::new(ctx)),
            #[cfg(not(target_os = "macos"))]
            Self::Vulkan(ctx) => Box::new(SkiaFrameRenderer::new(ctx.as_ref())),
            #[cfg(target_os = "macos")]
            Self::Metal(ctx) => Box::new(SkiaFrameRenderer::new(ctx.as_ref())),
        }
    }

    pub fn encoder(
        &self,
        input: &EncoderInput,
        width: u32,
        height: u32,
    ) -> PyResult<Box<dyn EncoderFrameRenderer + '_>> {
        let renderer: Box<dyn EncoderFrameRenderer> = match self {
            Self::Cpu => Box::new(
                CpuEncoderFrameRenderer::new(20, input, width, height).map_err(render_error)?,
            ),
            Self::Skia(ctx) => Box::new(
                SkiaEncoderFrameRenderer::new(ctx, SkiaFrameExport::Auto, input, width, height)
                    .map_err(render_error)?,
            ),
            #[cfg(not(target_os = "macos"))]
            Self::Vulkan(ctx) => Box::new(
                SkiaEncoderFrameRenderer::new(
                    ctx.as_ref(),
                    SkiaFrameExport::Auto,
                    input,
                    width,
                    height,
                )
                .map_err(render_error)?,
            ),
            #[cfg(target_os = "macos")]
            Self::Metal(ctx) => Box::new(
                SkiaEncoderFrameRenderer::new(
                    ctx.as_ref(),
                    SkiaFrameExport::Auto,
                    input,
                    width,
                    height,
                )
                .map_err(render_error)?,
            ),
        };
        Ok(renderer)
    }
}
