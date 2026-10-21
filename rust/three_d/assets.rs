//! Asset metadata and font outlines, without rendering or Python callbacks.

use crate::render::render_error;
use fframes::three_d::{Geometry, Object};
use pyo3::prelude::*;
use serde::Serialize;
use std::path::PathBuf;

#[derive(Serialize)]
struct ClipInfo {
    name: String,
    duration: f32,
    channels: usize,
}

#[derive(Serialize)]
struct ModelInfo {
    nodes: Vec<String>,
    animations: Vec<ClipInfo>,
    meshes: usize,
    bounds: Option<([f32; 3], [f32; 3])>,
}

#[pyfunction]
pub(crate) fn model_info(py: Python<'_>, source: PathBuf) -> PyResult<String> {
    py.detach(|| {
        let model = super::scene::load_model(&source.canonicalize()?)?;
        let bounds = model.bounds();
        let info = ModelInfo {
            nodes: model
                .scene
                .nodes()
                .filter_map(|(_, node)| node.name.as_ref().map(ToString::to_string))
                .collect(),
            meshes: model
                .scene
                .nodes()
                .filter(|(_, node)| matches!(node.object, Object::Mesh(_)))
                .count(),
            bounds: (bounds.min.is_finite() && bounds.max.is_finite())
                .then(|| (bounds.min.to_array(), bounds.max.to_array())),
            animations: model
                .animations
                .into_iter()
                .map(|clip| ClipInfo {
                    name: clip.name,
                    duration: clip.duration,
                    channels: clip.channels.len(),
                })
                .collect(),
        };
        serde_json::to_string(&info).map_err(render_error)
    })
}

#[derive(Serialize)]
struct Polygon {
    outer: Vec<[f32; 2]>,
    holes: Vec<Vec<[f32; 2]>>,
}

#[derive(Serialize)]
struct Glyph {
    character: char,
    origin: [f32; 2],
    advance: f32,
    shapes: Vec<Polygon>,
}

#[pyfunction]
pub(crate) fn text_shapes(
    py: Python<'_>,
    font: PathBuf,
    text: &str,
    size: f32,
    letter_spacing: f32,
) -> PyResult<String> {
    py.detach(|| {
        let glyphs = Geometry::text_shapes(&std::fs::read(font)?, text, size, letter_spacing)
            .map_err(render_error)?;
        let glyphs = glyphs
            .into_iter()
            .map(|glyph| Glyph {
                character: glyph.ch,
                origin: glyph.origin.to_array(),
                advance: glyph.advance,
                shapes: glyph
                    .shapes
                    .into_iter()
                    .map(|shape| Polygon {
                        outer: shape.outer.into_iter().map(|p| p.to_array()).collect(),
                        holes: shape
                            .holes
                            .into_iter()
                            .map(|hole| hole.into_iter().map(|p| p.to_array()).collect())
                            .collect(),
                    })
                    .collect(),
            })
            .collect::<Vec<_>>();
        serde_json::to_string(&glyphs).map_err(render_error)
    })
}
