//! Batch previews and diagnostics using upstream inspection primitives.

use crate::{
    backend::{Backend, Device, Rasterizer},
    render::{FrameCache, render_error},
};
use fframes::{Color, ReportedDiagnostic, RgbaFrame, usvgr};
use pyo3::{
    exceptions::{PyIndexError, PyValueError},
    prelude::*,
};
use serde::Serialize;
use std::path::{Path, PathBuf};

pub(crate) trait Source: Sync {
    fn size(&self) -> [u32; 2];
    fn fps(&self) -> usize;
    fn count(&self) -> usize;
    fn backend(&self) -> Backend;
    fn fonts(&self) -> &usvgr::fontdb::Database;
    fn tree(
        &self,
        index: usize,
        cache: &mut FrameCache,
        rasterizer: &Rasterizer<'_>,
    ) -> PyResult<usvgr::Tree>;
}

#[derive(Serialize)]
struct Report {
    frame: usize,
    seconds: f64,
    diagnostics: Vec<ReportedDiagnostic>,
    elements: Vec<fframes::element_labels::LabelledElement>,
}

fn size(source: &dyn Source, requested: Option<[u32; 2]>) -> PyResult<[u32; 2]> {
    let [w, h] = requested.unwrap_or_else(|| source.size());
    if w == 0 || h == 0 || w > i32::MAX as u32 || h > i32::MAX as u32 {
        return Err(PyValueError::new_err(
            "preview size must have positive 32-bit dimensions",
        ));
    }
    Ok([w, h])
}

fn inspect(source: &dyn Source, indices: &[usize]) -> PyResult<String> {
    let [w, h] = source.size();
    let device = Device::new(source.backend(), w, h)?;
    let rasterizer = device.rasterizer();
    fframes::diagnostics::install_log_capture();
    // Each worker owns its parser cache and decoders; no Python calls enter the batch.
    use fframes::rayon::prelude::*;
    let reports = indices
        .par_iter()
        .map_init(FrameCache::default, |cache, &index| {
            let (tree, mut diagnostics) =
                fframes::diagnostics::collect(|| source.tree(index, cache, &rasterizer));
            let tree = tree?;
            diagnostics.extend(fframes::diagnostics::inspect_tree(
                &tree, w as f32, h as f32,
            ));
            if !has_graphics(tree.root())
                && !diagnostics
                    .iter()
                    .any(|d| matches!(d, fframes::diagnostics::Diagnostic::EmptyFrame))
            {
                diagnostics.push(fframes::diagnostics::Diagnostic::EmptyFrame);
            }
            Ok(Report {
                frame: index,
                seconds: index as f64 / source.fps() as f64,
                diagnostics: diagnostics
                    .into_iter()
                    .map(ReportedDiagnostic::from)
                    .collect(),
                elements: fframes::element_labels::labelled_elements(&tree),
            })
        })
        .collect::<PyResult<Vec<_>>>()?;
    serde_json::to_string(&reports).map_err(render_error)
}

fn has_graphics(group: &usvgr::Group) -> bool {
    group.opacity().get() > 0.
        && group.children().iter().any(|node| match node {
            usvgr::Node::Group(child) => has_graphics(child),
            _ => true,
        })
}

fn preview(
    source: &dyn Source,
    index: usize,
    path: &Path,
    requested: Option<[u32; 2]>,
    crop: Option<[u32; 4]>,
    labels: bool,
) -> PyResult<()> {
    let [w, h] = size(source, requested)?;
    let device = Device::new(source.backend(), w, h)?;
    let tree = source.tree(index, &mut FrameCache::default(), &device.rasterizer())?;
    let mut frame = device
        .frame()
        .render_tree(&tree, Color::TRANSPARENT, w, h)
        .map_err(render_error)?;
    if labels {
        let elements = fframes::element_labels::labelled_elements(&tree);
        frame = fframes::element_labels::draw_labels(
            &frame,
            &tree,
            &elements,
            source.fonts(),
            "sans-serif",
        )
        .map_err(render_error)?;
    }
    if let Some([x, y, width, height]) = crop {
        if width == 0
            || height == 0
            || x.checked_add(width).is_none_or(|r| r > w)
            || y.checked_add(height).is_none_or(|b| b > h)
        {
            return Err(PyValueError::new_err(
                "crop must be a nonempty rectangle within the preview dimensions",
            ));
        }
        frame = frame.crop(x, y, width, height);
    }
    frame.save_png(path).map_err(render_error)
}

fn sheet(
    source: &dyn Source,
    indices: &[usize],
    path: &Path,
    columns: usize,
    requested: Option<[u32; 2]>,
    onion: bool,
) -> PyResult<()> {
    if indices.is_empty() || columns == 0 {
        return Err(PyValueError::new_err(
            "a sheet needs frames and a positive column count",
        ));
    }
    let [w, h] = size(source, requested)?;
    let device = Device::new(source.backend(), w, h)?;
    let rasterizer = device.rasterizer();
    let mut renderer = device.frame();
    let mut cache = FrameCache::default();
    let frames = indices
        .iter()
        .map(|&i| {
            renderer
                .render_tree(
                    &source.tree(i, &mut cache, &rasterizer)?,
                    Color::TRANSPARENT,
                    w,
                    h,
                )
                .map_err(render_error)
        })
        .collect::<PyResult<Vec<_>>>()?;
    let frame = if onion {
        fframes::sheet::onion_skin(&frames).map_err(render_error)?
    } else {
        let cells = frames
            .into_iter()
            .zip(indices)
            .map(|(frame, &i)| fframes::sheet::SheetCell {
                frame,
                label: format!("#{i}  {:.3}s", i as f64 / source.fps() as f64),
            })
            .collect::<Vec<_>>();
        let mut fonts = source.fonts().clone();
        if fonts.faces().next().is_none() {
            fonts.load_system_fonts();
        }
        fframes::sheet::contact_sheet(&cells, columns, &fonts, "sans-serif")
            .map_err(render_error)?
    };
    frame.save_png(path).map_err(render_error)
}

fn pops(
    source: &dyn Source,
    start: usize,
    end: usize,
    requested: Option<[u32; 2]>,
) -> PyResult<String> {
    if start >= end || end > source.count() {
        return Err(PyIndexError::new_err(
            "pop detection needs 0 <= start < end <= frame count",
        ));
    }
    let [w, h] = size(source, requested)?;
    let device = Device::new(source.backend(), w, h)?;
    let rasterizer = device.rasterizer();
    let mut renderer = device.frame();
    let mut cache = FrameCache::default();
    let mut detector = fframes::continuity::PopDetector::new(w, h);
    for i in start..end {
        let frame: RgbaFrame = renderer
            .render_tree(
                &source.tree(i, &mut cache, &rasterizer)?,
                Color::TRANSPARENT,
                w,
                h,
            )
            .map_err(render_error)?;
        detector.push(frame);
    }
    let mut pops = detector.finish();
    for pop in &mut pops {
        pop.frame += start;
    }
    serde_json::to_string(&pops).map_err(render_error)
}

#[derive(FromPyObject)]
pub(crate) enum Video<'py> {
    Svg(PyRef<'py, crate::video::SvgVideo>),
    Scene(PyRef<'py, crate::compose::SceneVideo>),
}

impl Video<'_> {
    fn source(&self) -> &dyn Source {
        match self {
            Self::Svg(video) => &**video,
            Self::Scene(video) => &**video,
        }
    }
}

#[pyfunction]
pub(crate) fn inspect_video(
    py: Python<'_>,
    video: Video<'_>,
    indices: Vec<usize>,
) -> PyResult<String> {
    let source = video.source();
    py.detach(|| inspect(source, &indices))
}

#[pyfunction]
pub(crate) fn preview_video(
    py: Python<'_>,
    video: Video<'_>,
    index: usize,
    path: PathBuf,
    size: Option<[u32; 2]>,
    crop: Option<[u32; 4]>,
    labels: bool,
) -> PyResult<()> {
    let source = video.source();
    py.detach(|| preview(source, index, &path, size, crop, labels))
}

#[pyfunction]
pub(crate) fn sheet_video(
    py: Python<'_>,
    video: Video<'_>,
    indices: Vec<usize>,
    path: PathBuf,
    columns: usize,
    size: Option<[u32; 2]>,
    onion: bool,
) -> PyResult<()> {
    let source = video.source();
    py.detach(|| sheet(source, &indices, &path, columns, size, onion))
}

#[pyfunction]
pub(crate) fn detect_pops(
    py: Python<'_>,
    video: Video<'_>,
    start: usize,
    end: usize,
    size: Option<[u32; 2]>,
) -> PyResult<String> {
    let source = video.source();
    py.detach(|| pops(source, start, end, size))
}
