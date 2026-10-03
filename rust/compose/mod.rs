//! The Python authoring layer's private native plan, separate from SVG bindings.

mod audio;
mod graphics;
mod input;

use std::{path::PathBuf, sync::Arc};

use fframes::{
    AudioMixer, AudioTimelineSamples, Color, CpuFrameRenderer, FrameRenderer,
    ResolvedRenderingTimeline,
    usvgr::{
        self,
        svgtree::{AId, EId, NestedNodeData, svgrtypes::Transform},
    },
};
use pyo3::{
    exceptions::{PyIndexError, PyValueError},
    prelude::*,
    types::PyBytes,
};

use crate::render::{Resources, render_error};
use audio::{SAMPLE_RATE, Soundtrack};
use graphics::{Asset, attribute, borrow_node, document, element};
use input::{Plan, Value};

struct Layer {
    first: usize,
    end: usize,
    start: f64,
    x: Value,
    y: Value,
    opacity: Value,
    rotation: Value,
    scale: Value,
    asset: Asset,
    children: Vec<usize>,
    depth: usize,
}

/// Compiled graphics and audio owned entirely by Rust.
#[pyclass(frozen, module = "fframes._native")]
pub(crate) struct SceneVideo {
    width: u32,
    height: u32,
    fps: usize,
    layers: Vec<Layer>,
    roots: Vec<usize>,
    fonts: usvgr::fontdb::Database,
    media: fframes::DynamicMediaProvider<'static>,
    timeline: ResolvedRenderingTimeline<'static, AudioTimelineSamples>,
}

impl SceneVideo {
    fn compile(plan: Plan) -> PyResult<Self> {
        let [width, height] = plan.resolution;
        if width == 0
            || height == 0
            || width > i32::MAX as u32
            || height > i32::MAX as u32
            || plan.fps == 0
            || plan.fps > i32::MAX as usize
            || plan.frames == 0
        {
            return Err(PyValueError::new_err(
                "invalid dimensions, fps or frame count",
            ));
        }
        let duration = plan.frames as f64 / plan.fps as f64;
        if duration > 86401. {
            return Err(PyValueError::new_err("composition exceeds 24 hours"));
        }
        let mut fonts = usvgr::fontdb::Database::new();
        if plan.load_system_fonts {
            fonts.load_system_fonts();
        }
        for path in plan.fonts {
            // File sources are reopened by fontdb during shaping. Own explicit
            // font bytes so a compiled session is independent of later file edits.
            let bytes = std::fs::read(&path)?;
            if fonts
                .load_font_source(usvgr::fontdb::Source::Binary(Arc::new(bytes)))
                .is_empty()
            {
                return Err(PyValueError::new_err(format!(
                    "invalid font file: {}",
                    path.display()
                )));
            }
        }
        if fonts
            .query(&usvgr::fontdb::Query {
                families: &[usvgr::fontdb::Family::SansSerif],
                ..Default::default()
            })
            .is_none()
        {
            // Preserve system generic-family choices; explicit-only databases need
            // a fallback for the default sans-serif family.
            let family = fonts
                .faces()
                .next()
                .and_then(|face| face.families.first())
                .map(|family| family.0.clone());
            if let Some(family) = family {
                fonts.set_sans_serif_family(family);
            }
        }
        let mut layers: Vec<Layer> = Vec::with_capacity(plan.layers.len());
        let mut roots = Vec::new();
        let mut images = graphics::Images::new();
        for layer in plan.layers {
            if !layer.start.is_finite()
                || !layer.end.is_finite()
                || layer.start < 0.
                || layer.end <= layer.start
                || layer.end > duration + 1e-9
            {
                return Err(PyValueError::new_err("invalid layer interval"));
            }
            let index = layers.len();
            let (parent_size, depth) = if let Some(parent) = layer.parent {
                let parent = layers
                    .get_mut(parent)
                    .ok_or_else(|| PyValueError::new_err("parent must precede its children"))?;
                if parent.asset.node.is_some() || parent.depth >= 64 {
                    return Err(PyValueError::new_err(
                        "invalid group parent or nesting exceeds 64 levels",
                    ));
                }
                parent.children.push(index);
                (parent.asset.size, parent.depth + 1)
            } else {
                roots.push(index);
                ([f64::from(width), f64::from(height)], 0)
            };
            let graphic = layer.graphic;
            graphic.opacity.check(0., 1.)?;
            graphic.rotation.check(-1e7, 1e7)?;
            graphic.scale.check(f64::MIN_POSITIVE, 1e4)?;
            let asset = graphics::prepare(graphic.shape, &fonts, &mut images)?;
            let x = graphic
                .position
                .x
                .resolve(parent_size[0], asset.size[0], true)?;
            let y = graphic
                .position
                .y
                .resolve(parent_size[1], asset.size[1], false)?;
            let frame_at = |time: f64| (time * plan.fps as f64 - 1e-9).ceil().max(0.) as usize;
            layers.push(Layer {
                first: frame_at(layer.start),
                end: frame_at(layer.end),
                start: layer.start,
                x: x.compile(),
                y: y.compile(),
                opacity: graphic.opacity.compile(),
                rotation: graphic.rotation.compile(),
                scale: graphic.scale.compile(),
                asset,
                children: Vec::new(),
                depth,
            });
        }
        let Soundtrack { media, map } = audio::prepare(plan.sounds, duration)?;
        Ok(Self {
            width,
            height,
            fps: plan.fps,
            layers,
            roots,
            fonts,
            media,
            timeline: ResolvedRenderingTimeline {
                audio_map: map,
                scenes: None,
                duration_in_frames: plan.frames,
            },
        })
    }

    fn node(&self, index: usize, frame: usize) -> Option<NestedNodeData<'_>> {
        let layer = &self.layers[index];
        if frame < layer.first || frame >= layer.end {
            return None;
        }
        let time = frame as f64 / self.fps as f64 - layer.start;
        let opacity = layer.opacity.value(time);
        if opacity == 0. {
            return None;
        }
        let angle = layer.rotation.value(time).to_radians();
        let scale = layer.scale.value(time);
        let (sin, cos) = angle.sin_cos();
        let (a, b, c, d) = (cos * scale, sin * scale, -sin * scale, cos * scale);
        let [cx, cy] = layer.asset.size.map(|extent| extent / 2.);
        let [ox, oy] = layer.asset.offset;
        let transform = Transform {
            a,
            b,
            c,
            d,
            e: layer.x.value(time) + cx + a * (ox - cx) + c * (oy - cy),
            f: layer.y.value(time) + cy + b * (ox - cx) + d * (oy - cy),
        };
        let children = if let Some(node) = &layer.asset.node {
            vec![Some(borrow_node(node))]
        } else {
            layer
                .children
                .iter()
                .map(|index| self.node(*index, frame))
                .collect()
        };
        Some(element(
            EId::G,
            vec![
                attribute(AId::Transform, transform),
                attribute(AId::Opacity, opacity),
            ],
            children,
        ))
    }

    fn tree(&self, index: usize, cache: &mut usvgr::Cache) -> PyResult<usvgr::Tree> {
        if index >= self.timeline.duration_in_frames {
            return Err(PyIndexError::new_err("frame index out of range"));
        }
        let doc = document(
            self.width,
            self.height,
            self.roots
                .iter()
                .map(|root| self.node(*root, index))
                .collect(),
        );
        usvgr::Tree::from_nested_svgtree_with_cache(
            &doc,
            &usvgr::Options::default(),
            cache,
            &self.fonts,
        )
        .map_err(render_error)
    }

    fn rasterize(&self, index: usize) -> PyResult<fframes::RgbaFrame> {
        let tree = self.tree(index, &mut usvgr::Cache::default())?;
        CpuFrameRenderer::default()
            .render_tree(&tree, Color::TRANSPARENT, self.width, self.height)
            .map_err(render_error)
    }

    fn resources(&self) -> Resources<'_> {
        Resources {
            width: self.width,
            height: self.height,
            fps: self.fps,
            sample_rate: SAMPLE_RATE,
            media: Some(&self.media),
            timeline: &self.timeline,
        }
    }
}

#[pymethods]
impl SceneVideo {
    fn __len__(&self) -> usize {
        self.timeline.duration_in_frames
    }

    fn rgba<'py>(&self, py: Python<'py>, index: usize) -> PyResult<Bound<'py, PyBytes>> {
        let frame = py.detach(|| self.rasterize(index))?;
        Ok(PyBytes::new(py, &frame.pixels))
    }

    fn save_png(&self, py: Python<'_>, index: usize, path: PathBuf) -> PyResult<()> {
        py.detach(|| self.rasterize(index)?.save_png(path).map_err(render_error))
    }

    fn audio_samples<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        let bytes = py.detach(|| {
            let count = (self.timeline.duration_in_frames as f64 / self.fps as f64
                * SAMPLE_RATE as f64)
                .round() as usize;
            let (left, right) = AudioMixer::new(
                self.timeline.audio_map.as_ref(),
                Some(&self.media),
                SAMPLE_RATE,
                0..count,
                count,
                Default::default(),
            )
            .render_all();
            left.into_iter()
                .zip(right)
                .flat_map(|(left, right)| left.to_le_bytes().into_iter().chain(right.to_le_bytes()))
                .collect::<Vec<_>>()
        });
        PyBytes::new(py, &bytes)
    }

    fn render(
        &self,
        py: Python<'_>,
        path: PathBuf,
        directory: PathBuf,
        encoder: &str,
        concurrency: usize,
        bitrate: i64,
    ) -> PyResult<()> {
        if bitrate <= 0 || bitrate > i64::from(i32::MAX) {
            return Err(PyValueError::new_err("invalid bitrate"));
        }
        py.detach(|| {
            self.resources().render(
                |index, cache| self.tree(index, cache),
                path,
                directory,
                encoder,
                concurrency,
                bitrate,
            )
        })
    }
}

/// Load a validated authoring description into a reusable native session.
#[pyfunction]
pub(crate) fn compile_scene(py: Python<'_>, plan: String) -> PyResult<SceneVideo> {
    py.detach(|| {
        let plan = serde_json::from_str(&plan)
            .map_err(|error| PyValueError::new_err(error.to_string()))?;
        SceneVideo::compile(plan)
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn plan() -> Result<Plan, serde_json::Error> {
        serde_json::from_str(include_str!("../../tests/assets/scene.json"))
    }

    #[test]
    fn cached_rasterization_moves_geometry_when_frames_are_requested_out_of_order() -> PyResult<()>
    {
        let plan = plan().map_err(|error| PyValueError::new_err(error.to_string()))?;
        let scene = SceneVideo::compile(plan)?;
        let mut cache = usvgr::Cache::default();
        let mut renderer = CpuFrameRenderer::new(20);
        for index in [2, 0, 1, 2] {
            let tree = scene.tree(index, &mut cache)?;
            let rgba = renderer
                .render_tree(&tree, Color::TRANSPARENT, 16, 8)
                .map_err(render_error)?;
            let opaque: Vec<_> = rgba
                .pixels
                .as_chunks::<4>()
                .0
                .iter()
                .enumerate()
                .filter_map(|(index, pixel)| (pixel[3] == 255).then_some(index))
                .collect();
            let expected: Vec<_> = (0..4)
                .flat_map(|y| (index * 4..index * 4 + 4).map(move |x| y * 16 + x))
                .collect();
            assert_eq!(opaque, expected, "cached frame {index}");
        }
        Ok(())
    }

    #[test]
    fn native_plan_rejects_parent_cycles() -> Result<(), serde_json::Error> {
        let mut plan = plan()?;
        plan.layers[0].parent = Some(0);
        assert!(SceneVideo::compile(plan).is_err());
        Ok(())
    }
}
