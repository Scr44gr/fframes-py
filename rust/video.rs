use std::{path::PathBuf, sync::Arc};

use fframes::{
    AudioMap, AudioTimelineSamples, Color, CpuFrameRenderer, Duration, EncoderOptions,
    FFramesContext, FFramesMode, FFramesRenderBackend, Frame, FrameRenderer, RenderOptions,
    ResolvedRenderingTimeline, Svgr, TimeBase, Video, VideoSize, cpu::CpuRenderingBackend,
    fframes_logger::SilentLogger, usvgr,
};
use pyo3::{
    exceptions::{PyIndexError, PyRuntimeError, PyValueError},
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
}

impl Video for SvgVideo {
    // The backend receives the actual size and time base in FFramesContext below.
    const FPS: usize = 1;
    const WIDTH: usize = 1;
    const HEIGHT: usize = 1;
    const BACKGROUND_COLOR: Color = Color::TRANSPARENT;

    fn duration(&self) -> Duration<'_> {
        Duration::Frames(self.frames.len())
    }

    fn audio(&self) -> AudioMap<'_> {
        AudioMap::none()
    }

    fn render_frame<'a>(&'a self, frame: Frame, _: &FFramesContext<'a, '_>) -> Svgr<'a> {
        Svgr::from(self.frames[frame.index].as_str())
    }
}

impl SvgVideo {
    fn rasterize(&self, index: usize) -> PyResult<fframes::RgbaFrame> {
        let svg = self
            .frames
            .get(index)
            .ok_or_else(|| PyIndexError::new_err("frame index out of range"))?;
        let tree = usvgr::Tree::from_str(svg, &usvgr::Options::default(), &self.fonts)
            .map_err(|error| PyValueError::new_err(error.to_string()))?;
        CpuFrameRenderer::default()
            .render_tree(&tree, Color::TRANSPARENT, self.width, self.height)
            .map_err(render_error)
    }
}

fn render_error(error: fframes::FFramesRendererError) -> PyErr {
    PyRuntimeError::new_err(error.to_string())
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
    fn render(
        &self,
        py: Python<'_>,
        path: PathBuf,
        directory: PathBuf,
        encoder: &str,
        concurrency: usize,
    ) -> PyResult<()> {
        if concurrency == 0 || encoder.is_empty() || encoder.contains('\0') {
            return Err(PyValueError::new_err("invalid encoder or concurrency"));
        }
        if !self.width.is_multiple_of(2) || !self.height.is_multiple_of(2) {
            return Err(PyValueError::new_err(
                "video encoding requires even dimensions",
            ));
        }
        let extension = path
            .extension()
            .and_then(|value| value.to_str())
            .filter(|value| matches!(*value, "mp4" | "mov" | "mkv" | "avi" | "webm"))
            .ok_or_else(|| PyValueError::new_err("unsupported output container"))?;
        // Upstream may dereference a null AVIOContext if opening the output fails.
        // Encode to a verified writable file, then let Rust report destination I/O errors.
        let staged = directory.join("output").with_extension(extension);
        std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&staged)?;
        py.detach(|| {
            let timeline = ResolvedRenderingTimeline::<AudioTimelineSamples> {
                audio_map: None,
                scenes: None,
                duration_in_frames: self.frames.len(),
            };
            let ctx = FFramesContext {
                time_base: TimeBase {
                    fps: self.fps,
                    sample_rate: 44100,
                },
                current_video_size: VideoSize {
                    width: self.width as usize,
                    height: self.height as usize,
                },
                duration_in_frames: self.frames.len(),
                mode: FFramesMode::Renderer,
                scenes: None,
                media_source: None,
                font_source: None,
                abort_signal: None,
            };
            let options = RenderOptions {
                video_encoder_options: EncoderOptions {
                    preferred_encoder: Some(encoder),
                    ..Default::default()
                },
                tmp_files_directory: Some(&directory),
                ..Default::default()
            };
            let info = fframes::VideoEncoderInfo::for_output(
                &staged,
                (self.width as i32, self.height as i32, self.fps as i32),
                &options.video_encoder_options,
            )
            .map_err(|error| PyRuntimeError::new_err(error.to_string()))?;
            if info.name() != encoder {
                return Err(PyRuntimeError::new_err(format!(
                    "encoder {encoder:?} is not available in this FFmpeg build"
                )));
            }
            crate::encoder::check_output(&staged, &info)?;
            CpuRenderingBackend {
                concurrency,
                ..Default::default()
            }
            .render(
                &staged,
                self,
                Arc::new(SilentLogger),
                &usvgr::Options::default(),
                &options,
                &self.fonts,
                &timeline,
                &ctx,
            )
            .map_err(render_error)?;
            std::fs::rename(staged, path)?;
            Ok(())
        })
    }
}

/// Store SVG frames and optionally load system fonts once for subsequent renders.
///
/// # Errors
/// Returns ValueError for invalid dimensions, frame rate or an empty frame sequence.
#[pyfunction]
#[pyo3(signature = (width, height, fps, frames, load_system_fonts, fonts=Vec::new()))]
pub(crate) fn compile_video(
    py: Python<'_>,
    width: u32,
    height: u32,
    fps: usize,
    frames: Vec<String>,
    load_system_fonts: bool,
    fonts: Vec<PathBuf>,
) -> PyResult<SvgVideo> {
    if width == 0
        || height == 0
        || width > i32::MAX as u32
        || height > i32::MAX as u32
        || fps == 0
        || fps > i32::MAX as usize
        || frames.is_empty()
    {
        return Err(PyValueError::new_err(
            "invalid dimensions, fps or empty frames",
        ));
    }
    py.detach(|| {
        Ok(SvgVideo {
            width,
            height,
            fps,
            frames,
            fonts: crate::fonts::load(&fonts, load_system_fonts)?,
        })
    })
}
