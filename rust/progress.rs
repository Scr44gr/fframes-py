//! Native progress and cancellation, independent of Python's GIL.

use fframes::fframes_logger::FFramesLogger;
use pyo3::{
    exceptions::{PyRuntimeError, PyValueError},
    prelude::*,
};
use serde::Serialize;
use std::{
    path::{Path, PathBuf},
    sync::{
        Arc, Mutex,
        atomic::{AtomicBool, AtomicUsize, Ordering},
    },
};

#[derive(Default)]
pub(crate) struct Progress {
    pub abort: fframes::AbortSignal,
    started: AtomicBool,
    state: AtomicUsize,
    frames: AtomicUsize,
    total: AtomicUsize,
    audio: AtomicUsize,
    audio_total: AtomicUsize,
    warnings: Mutex<Vec<String>>,
}

#[derive(Serialize)]
struct Snapshot<'a> {
    state: &'static str,
    frames: usize,
    total_frames: usize,
    audio_frames: usize,
    total_audio_frames: usize,
    warnings: &'a [String],
}

impl Progress {
    pub fn begin(&self) -> PyResult<()> {
        if self.started.swap(true, Ordering::AcqRel) {
            return Err(PyValueError::new_err(
                "RenderControl belongs to one export; create a new control",
            ));
        }
        self.state.store(1, Ordering::Release);
        Ok(())
    }

    pub fn check(&self) -> PyResult<()> {
        if self.abort.is_aborted() {
            Err(PyRuntimeError::new_err("render cancelled"))
        } else {
            Ok(())
        }
    }

    pub fn muxing(&self) {
        self.state.store(2, Ordering::Release);
    }
    pub fn finish(&self, result: &PyResult<()>) {
        self.state.store(
            if result.is_ok() {
                3
            } else if self.abort.is_aborted() {
                4
            } else {
                5
            },
            Ordering::Release,
        );
    }
}

impl FFramesLogger for Progress {
    fn init_frames_rendering(&self, count: usize) -> fframes::FFramesRendererResult<()> {
        self.total.store(count, Ordering::Relaxed);
        Ok(())
    }
    fn log_frame(&self, _index: usize, _worker: usize) {
        self.frames.fetch_add(1, Ordering::Relaxed);
    }
    fn init_audio_encoding(&self, count: usize) -> fframes::FFramesRendererResult<()> {
        self.audio_total.store(count, Ordering::Relaxed);
        Ok(())
    }
    fn log_audio_frame(&self) {
        self.audio.fetch_add(1, Ordering::Relaxed);
    }
    fn success(&self, _output: &Path, _directory: Option<&PathBuf>) {}
    fn warn(&self, warning: &str) {
        if let Ok(mut warnings) = self.warnings.lock() {
            warnings.push(warning.to_owned());
        }
    }
}

/// One export's native progress counters and cancellation signal.
#[pyclass(frozen, module = "fframes._native")]
pub(crate) struct RenderControl {
    pub state: Arc<Progress>,
}

#[pymethods]
impl RenderControl {
    #[new]
    fn new() -> Self {
        Self {
            state: Arc::default(),
        }
    }
    fn cancel(&self) {
        self.state.abort.abort();
    }
    fn snapshot(&self) -> PyResult<String> {
        let progress = &self.state;
        let warnings = progress
            .warnings
            .lock()
            .map_err(crate::render::render_error)?;
        let snapshot = Snapshot {
            state: match progress.state.load(Ordering::Acquire) {
                0 => "idle",
                1 => "rendering",
                2 => "muxing",
                3 => "complete",
                4 => "cancelled",
                _ => "failed",
            },
            frames: progress.frames.load(Ordering::Relaxed),
            total_frames: progress.total.load(Ordering::Relaxed),
            audio_frames: progress.audio.load(Ordering::Relaxed),
            total_audio_frames: progress.audio_total.load(Ordering::Relaxed),
            warnings: &warnings,
        };
        serde_json::to_string(&snapshot).map_err(crate::render::render_error)
    }
}
