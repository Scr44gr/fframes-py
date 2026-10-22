//! Encode typed trees with upstream scheduling, rasterization, mixing and muxing.

use std::{
    path::PathBuf,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
};

use fframes::{
    AudioTimelineSamples, Color, EncoderOptions, FFramesContext, FFramesMode, FrameScheduler,
    MediaProvider, RenderOptions, ResolvedRenderingTimeline, SegmentWriter, TimeBase, VideoSize,
    fframes_logger::FFramesLogger, usvgr,
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

#[derive(Default)]
pub(crate) struct FrameCache {
    pub trees: usvgr::Cache,
    pub decoders: crate::clips::Decoders,
    pub textures: std::collections::HashMap<usize, Arc<fframes::three_d::Texture>>,
}

#[derive(serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Encoding {
    pub encoder: String,
    pub concurrency: usize,
    pub bitrate: i64,
    pub color_matrix: String,
    pub frame_range: Option<(usize, usize)>,
    pub pixel_format: Option<String>,
    pub bitrate_tolerance: i32,
    pub qmin: i32,
    pub qmax: i32,
    pub qcompress: f32,
    pub max_qdiff: i32,
    pub gop_size: i32,
    pub tag: Option<String>,
    pub codec_params: Vec<(String, String)>,
    pub audio: crate::encoder::AudioOptions,
    pub audio_mix: crate::audio::Mix,
    pub fps: Option<usize>,
    pub scale: f64,
}

impl Encoding {
    pub fn parse(json: &str) -> PyResult<Self> {
        serde_json::from_str(json).map_err(|error| PyValueError::new_err(error.to_string()))
    }
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
        tree: impl Fn(f64, &mut FrameCache, &crate::backend::Rasterizer<'_>) -> PyResult<usvgr::Tree>
        + Sync,
        path: PathBuf,
        directory: PathBuf,
        encoding: &Encoding,
        control: Option<&crate::progress::RenderControl>,
    ) -> PyResult<()> {
        let progress = control.map_or_else(Arc::default, |c| Arc::clone(&c.state));
        progress.begin()?;
        let result = (|| {
            progress.check()?;
            let staged = directory
                .join("output")
                .with_extension(path.extension().unwrap_or_default());
            self.render_inner(tree, staged.clone(), directory, encoding, &progress)?;
            progress.check()?;
            std::fs::rename(staged, path)?;
            Ok(())
        })();
        progress.finish(&result);
        result
    }

    fn render_inner(
        &self,
        tree: impl Fn(f64, &mut FrameCache, &crate::backend::Rasterizer<'_>) -> PyResult<usvgr::Tree>
        + Sync,
        path: PathBuf,
        directory: PathBuf,
        encoding: &Encoding,
        progress: &Arc<crate::progress::Progress>,
    ) -> PyResult<()> {
        let encoder = encoding.encoder.as_str();
        let concurrency = encoding.concurrency;
        let bitrate = encoding.bitrate;
        let color_matrix = crate::encoder::color_matrix(&encoding.color_matrix)?;
        let frame_range = encoding.frame_range;
        let fps = encoding.fps.unwrap_or(self.fps);
        if fps == 0
            || fps > i32::MAX as usize
            || !encoding.scale.is_finite()
            || !(f64::MIN_POSITIVE..=64.).contains(&encoding.scale)
        {
            return Err(PyValueError::new_err(
                "fps must be positive and scale must be in (0, 64]",
            ));
        }
        let width = (f64::from(self.width) * encoding.scale).round();
        let height = (f64::from(self.height) * encoding.scale).round();
        if width < 1. || height < 1. || width > i32::MAX as f64 || height > i32::MAX as f64 {
            return Err(PyValueError::new_err(
                "scaled dimensions exceed the encoder range",
            ));
        }
        let (width, height) = (width as u32, height as u32);
        let (start, end) = frame_range.unwrap_or((0, self.timeline.duration_in_frames));
        if start >= end || end > self.timeline.duration_in_frames {
            return Err(PyValueError::new_err(format!(
                "frame_range must satisfy 0 <= start < end <= {}; end is exclusive",
                self.timeline.duration_in_frames
            )));
        }
        if bitrate <= 0 || bitrate > i64::from(i32::MAX) {
            return Err(PyValueError::new_err("invalid bitrate"));
        }
        if concurrency == 0 || encoder.is_empty() || encoder.contains('\0') {
            return Err(PyValueError::new_err("invalid encoder or concurrency"));
        }
        if encoding.pixel_format.is_none()
            && (!width.is_multiple_of(2) || !height.is_multiple_of(2))
        {
            return Err(PyValueError::new_err(
                "video encoding requires even dimensions",
            ));
        }
        if encoder == "libopenh264" && (width < 16 || height < 16) {
            return Err(PyValueError::new_err(
                "libopenh264 requires width and height of at least 16 pixels",
            ));
        }
        let extension = path
            .extension()
            .and_then(|value| value.to_str())
            .filter(|value| matches!(*value, "mp4" | "mov" | "mkv" | "avi" | "webm"))
            .ok_or_else(|| PyValueError::new_err("unsupported output container"))?;
        let video_params: Vec<_> = encoding
            .codec_params
            .iter()
            .map(|(k, v)| (k.as_str(), v.as_str()))
            .collect();
        let audio_params: Vec<_> = encoding
            .audio
            .codec_params
            .iter()
            .map(|(k, v)| (k.as_str(), v.as_str()))
            .collect();
        let pixel_format = encoding
            .pixel_format
            .as_deref()
            .map(crate::encoder::pixel_format)
            .transpose()?;
        let tag = encoding
            .tag
            .as_ref()
            .map(|tag| -> PyResult<isize> {
                let bytes: [u8; 4] = tag
                    .as_bytes()
                    .try_into()
                    .map_err(|_| PyValueError::new_err("tag requires four ASCII characters"))?;
                Ok(u32::from_le_bytes(bytes) as isize)
            })
            .transpose()?;
        if encoding.qmin < 0
            || encoding.qmax < encoding.qmin
            || encoding.gop_size < 0
            || !(0. ..=1.).contains(&encoding.qcompress)
        {
            return Err(PyValueError::new_err(
                "invalid quantizer bounds, qcompress or gop_size",
            ));
        }
        crate::encoder::validate_parameters(encoder, &video_params, false, &path)?;
        if self.timeline.audio_map.is_some() {
            crate::encoder::validate_parameters(
                &encoding.audio.encoder,
                &audio_params,
                true,
                &path,
            )?;
        }
        // Upstream opens native output handles; establish a writable staged path first.
        std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&path)?;
        let options = RenderOptions {
            video_encoder_options: EncoderOptions {
                preferred_encoder: Some(encoder),
                bitrate: Some(bitrate),
                color_matrix,
                pixel_format: pixel_format
                    .unwrap_or(fframes::ffmpeg_sys_fframes::AVPixelFormat::AV_PIX_FMT_YUV420P),
                bitrate_tolerance: encoding.bitrate_tolerance,
                qmin: encoding.qmin,
                qmax: encoding.qmax,
                qcompress: encoding.qcompress,
                max_qdiff: encoding.max_qdiff,
                gop_size: encoding.gop_size,
                tag,
                codec_params: Some(&video_params),
                ..Default::default()
            },
            audio_encoder_options: encoding.audio.native(&audio_params)?,
            audio_mix: encoding.audio_mix.native()?,
            tmp_files_directory: Some(&directory),
            frame_range: Some(start..end),
            ..Default::default()
        };
        let info = fframes::VideoEncoderInfo::for_output(
            &path,
            (width as i32, height as i32, fps as i32),
            &options.video_encoder_options,
        )
        .map_err(render_error)?;
        if info.name() != encoder {
            return Err(PyRuntimeError::new_err(format!(
                "encoder {encoder:?} is not available in this FFmpeg build; \
                 use fframes.available_encoders() to inspect the linked library"
            )));
        }
        let input = crate::encoder::check_output(&path, &info, pixel_format)?;
        let logger: Arc<dyn FFramesLogger> = progress.clone();
        let count = ((end - start) as u128 * fps as u128).div_ceil(self.fps as u128) as usize;
        logger.init_frames_rendering(count).map_err(render_error)?;
        let scheduler = FrameScheduler::new(
            count,
            concurrency,
            options.video_encoder_options.min_segment_frames(fps),
        );
        let writer = SegmentWriter::new(
            &directory,
            extension,
            (width as i32, height as i32, fps as i32),
            &options,
            &logger,
        )
        .with_encoder_input(input);
        let failed = AtomicBool::new(false);
        let device = crate::backend::Device::new(self.backend, width, height)?;
        let rasterizer = device.rasterizer();
        // Adapt the upstream scheduler to typed trees. Its Video trait only accepts
        // SVG strings unless a global feature changes the semantics of the raw API.
        std::thread::scope(|scope| -> PyResult<()> {
            let workers: Vec<_> = (0..scheduler.workers())
                .map(|worker| {
                    let (tree, writer, scheduler, failed, device, rasterizer, logger) = (
                        &tree,
                        &writer,
                        &scheduler,
                        &failed,
                        &device,
                        &rasterizer,
                        &logger,
                    );
                    scope.spawn(move || -> PyResult<()> {
                        let result = (|| {
                            let mut cache = FrameCache::default();
                            let mut renderer =
                                device.encoder(writer.encoder_input(), width, height)?;
                            while let Some(claim) = scheduler.claim(worker) {
                                if failed.load(Ordering::Relaxed) {
                                    break;
                                }
                                progress.check()?;
                                let frame = renderer
                                    .render_tree(
                                        &tree(
                                            start as f64 / self.fps as f64
                                                + claim.frame as f64 / fps as f64,
                                            &mut cache,
                                            rasterizer,
                                        )
                                        .map_err(render_error)?,
                                        Color::TRANSPARENT,
                                    )
                                    .map_err(render_error)?;
                                writer.submit_frame(claim, frame).map_err(render_error)?;
                                logger.log_frame(claim.frame, worker);
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
        progress.check()?;
        progress.muxing();
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
