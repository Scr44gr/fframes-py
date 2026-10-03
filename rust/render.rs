//! Encode typed trees with upstream scheduling, rasterization, mixing and muxing.

use std::{
    path::PathBuf,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
};

use fframes::{
    AudioTimelineSamples, Color, EncoderInput, EncoderOptions, FFramesContext, FFramesMode,
    FrameScheduler, MediaProvider, RenderOptions, ResolvedRenderingTimeline, SegmentWriter,
    TimeBase, VideoSize,
    fframes_logger::{FFramesLogger, SilentLogger},
    usvgr,
};
use pyo3::{
    exceptions::{PyRuntimeError, PyValueError},
    prelude::*,
};

pub(crate) struct Resources<'a> {
    pub backend: crate::backend::Backend,
    pub width: u32,
    pub height: u32,
    pub fps: usize,
    pub sample_rate: usize,
    pub media: Option<&'a dyn MediaProvider<'a>>,
    pub timeline: &'a ResolvedRenderingTimeline<'a, AudioTimelineSamples>,
}

impl<'a> Resources<'a> {
    pub fn context(&self) -> FFramesContext<'a, 'a> {
        FFramesContext {
            time_base: TimeBase {
                fps: self.fps,
                sample_rate: self.sample_rate,
            },
            current_video_size: VideoSize {
                width: self.width as usize,
                height: self.height as usize,
            },
            duration_in_frames: self.timeline.duration_in_frames,
            mode: FFramesMode::Renderer,
            scenes: None,
            media_source: self.media,
            font_source: None,
            abort_signal: None,
        }
    }

    pub fn render(
        &self,
        tree: impl Fn(usize, &mut usvgr::Cache) -> PyResult<usvgr::Tree> + Sync,
        path: PathBuf,
        directory: PathBuf,
        encoder: &str,
        concurrency: usize,
        bitrate: i64,
    ) -> PyResult<()> {
        if bitrate <= 0 || bitrate > i64::from(i32::MAX) {
            return Err(PyValueError::new_err("invalid bitrate"));
        }
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
        // fframes 1.2.0 does not check every AVIO open before dereferencing its context.
        std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&path)?;
        let options = RenderOptions {
            video_encoder_options: EncoderOptions {
                preferred_encoder: Some(encoder),
                bitrate: Some(bitrate),
                ..Default::default()
            },
            audio_encoder_options: EncoderOptions {
                sample_rate: self.sample_rate,
                ..Default::default()
            },
            tmp_files_directory: Some(&directory),
            ..Default::default()
        };
        let info = fframes::VideoEncoderInfo::for_output(
            &path,
            (self.width as i32, self.height as i32, self.fps as i32),
            &options.video_encoder_options,
        )
        .map_err(render_error)?;
        if info.name() != encoder {
            return Err(PyRuntimeError::new_err(format!(
                "encoder {encoder:?} is not available in this FFmpeg build"
            )));
        }
        crate::encoder::check_output(&path, &info)?;
        let logger: Arc<dyn FFramesLogger> = Arc::new(SilentLogger);
        let input = EncoderInput::requested(&info).map_err(render_error)?;
        let scheduler = FrameScheduler::new(
            self.timeline.duration_in_frames,
            concurrency,
            options.video_encoder_options.min_segment_frames(self.fps),
        );
        let writer = SegmentWriter::new(
            &directory,
            extension,
            (self.width as i32, self.height as i32, self.fps as i32),
            &options,
            &logger,
        )
        .with_encoder_input(input);
        let failed = AtomicBool::new(false);
        let device = crate::backend::Device::new(self.backend, self.width, self.height)?;
        // Adapt the upstream scheduler to typed trees. Its Video trait only accepts
        // SVG strings unless a global feature changes the semantics of the raw API.
        std::thread::scope(|scope| -> PyResult<()> {
            let workers: Vec<_> = (0..scheduler.workers())
                .map(|worker| {
                    let (tree, writer, scheduler, failed, device) =
                        (&tree, &writer, &scheduler, &failed, &device);
                    scope.spawn(move || -> PyResult<()> {
                        let result = (|| {
                            let mut cache = usvgr::Cache::default();
                            let mut renderer =
                                device.encoder(writer.encoder_input(), self.width, self.height)?;
                            while let Some(claim) = scheduler.claim(worker) {
                                if failed.load(Ordering::Relaxed) {
                                    break;
                                }
                                let frame = renderer
                                    .render_tree(
                                        &tree(claim.frame, &mut cache)?,
                                        Color::TRANSPARENT,
                                    )
                                    .map_err(render_error)?;
                                writer.submit_frame(claim, frame).map_err(render_error)?;
                            }
                            Ok(())
                        })();
                        if result.is_err() {
                            failed.store(true, Ordering::Relaxed);
                        }
                        result
                    })
                })
                .collect();
            for worker in workers {
                worker
                    .join()
                    .map_err(|_| PyRuntimeError::new_err("rendering worker panicked"))??;
            }
            Ok(())
        })?;
        let files = writer.finish().map_err(render_error)?;
        #[expect(
            unsafe_code,
            reason = "fframes exposes native muxing only through this unsafe entry point"
        )]
        // SAFETY: files are completed encoder segments; the writable destination,
        // codec, dimensions and lifetimes were checked above. All media and sample
        // ranges are owned by this session and outlive the synchronous mux operation.
        unsafe {
            fframes::concatenator::concat_video_files_with_audio(
                &files,
                &path,
                self.timeline.audio_map.as_ref(),
                &options,
                &self.context(),
                &logger,
            )
            .map_err(render_error)?;
        }
        Ok(())
    }
}

pub(crate) fn render_error(error: impl std::fmt::Display) -> PyErr {
    PyRuntimeError::new_err(error.to_string())
}

pub(crate) fn media_error(error: fframes::media::FFramesMediaError) -> PyErr {
    render_error(fframes::FFramesRendererError::from(error))
}
