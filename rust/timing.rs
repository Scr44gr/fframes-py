//! Upstream timeline selectors over explicit or compiled composition names.

use pyo3::{exceptions::PyValueError, prelude::*};
use serde::{Deserialize, Serialize};

#[derive(Clone, Deserialize, Serialize)]
pub(crate) struct SceneRange {
    pub name: String,
    pub frames: [usize; 2],
}

#[derive(Deserialize, Serialize)]
struct Description {
    fps: usize,
    duration_in_frames: usize,
    scenes: Vec<SceneRange>,
}

pub(crate) fn validate(scenes: &[SceneRange], frames: usize) -> PyResult<()> {
    if scenes
        .iter()
        .any(|s| s.name.is_empty() || s.frames[0] >= s.frames[1] || s.frames[1] > frames)
    {
        return Err(PyValueError::new_err(
            "named scene ranges must satisfy 0 <= start < end <= video length",
        ));
    }
    Ok(())
}

/// Immutable upstream index with named-scene disambiguation and time syntax.
#[pyclass(frozen, module = "fframes._native")]
pub(crate) struct TimelineIndex {
    inner: fframes::TimelineIndex,
}

#[pymethods]
impl TimelineIndex {
    #[new]
    fn new(description: &str) -> PyResult<Self> {
        let description: Description =
            serde_json::from_str(description).map_err(crate::render::render_error)?;
        if description.fps == 0 || description.duration_in_frames == 0 {
            return Err(PyValueError::new_err(
                "timeline fps and frame count must be positive",
            ));
        }
        validate(&description.scenes, description.duration_in_frames)?;
        Ok(Self {
            inner: fframes::TimelineIndex {
                fps: description.fps,
                duration_in_frames: description.duration_in_frames,
                scenes: description
                    .scenes
                    .into_iter()
                    .enumerate()
                    .map(|(index, scene)| fframes::TimelineScene {
                        index,
                        name: fframes::short_scene_name(&scene.name).to_owned(),
                        full_name: scene.name,
                        frames: scene.frames[0]..scene.frames[1],
                    })
                    .collect(),
            },
        })
    }
    fn resolve_frame(&self, spec: &str) -> PyResult<usize> {
        self.inner
            .resolve_frame(spec)
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }
    fn resolve_range(&self, spec: &str) -> PyResult<(usize, usize)> {
        self.inner
            .resolve_range(spec)
            .map(|r| (r.start, r.end))
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }
    fn scenes_at(&self, frame: usize) -> PyResult<Vec<usize>> {
        if frame >= self.inner.duration_in_frames {
            return Err(PyValueError::new_err("frame lies outside the timeline"));
        }
        Ok(self.inner.scenes_at(frame).map(|s| s.index).collect())
    }
}

#[pyfunction]
pub(crate) fn inspect_timeline(video: crate::inspection::Video<'_>) -> PyResult<String> {
    let source = video.source();
    serde_json::to_string(&Description {
        fps: source.fps(),
        duration_in_frames: source.count(),
        scenes: source.chapters().to_vec(),
    })
    .map_err(crate::render::render_error)
}
