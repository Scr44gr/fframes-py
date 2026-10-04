//! The Python authoring layer's private native plan, separate from SVG bindings.

mod filters;
mod graphics;
mod input;
mod paint;
pub(crate) mod paths;
mod text;

use std::{borrow::Cow, path::PathBuf};

use fframes::{
    AudioTimelineSamples, Color, ResolvedRenderingTimeline,
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

use crate::audio::{self, SAMPLE_RATE, Soundtrack};
use crate::render::{FrameCache, Resources, render_error};
use crate::values::Value;
use graphics::{Asset, attribute, document, element};
use input::Plan;

struct Layer {
    first: usize,
    end: usize,
    start: f64,
    x: Value,
    y: Value,
    opacity: Value,
    z_index: Value,
    animated_order: bool,
    rotation: Value,
    scale: Value,
    origin: [f64; 2],
    matrix: Option<[Value; 6]>,
    mask: Option<graphics::Mask>,
    blend_mode: input::BlendMode,
    filter: Option<NestedNodeData<'static>>,
    asset: Asset,
    children: Vec<usize>,
    depth: usize,
}

/// Compiled graphics and audio owned entirely by Rust.
#[pyclass(frozen, module = "fframes._native")]
pub(crate) struct SceneVideo {
    backend: crate::backend::Backend,
    width: u32,
    height: u32,
    fps: usize,
    layers: Vec<Layer>,
    roots: Vec<usize>,
    animated_roots: bool,
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
        let fonts = crate::fonts::load(&plan.fonts, plan.load_system_fonts)?;
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
            if matches!(graphic.shape, input::Shape::Shader { .. })
                && plan.backend == crate::backend::Backend::Cpu
            {
                return Err(PyValueError::new_err("shaders require a Skia backend"));
            }
            graphic.opacity.check(0., 1.)?;
            graphic.z_index.check(-f64::MAX, f64::MAX)?;
            graphic.rotation.check(-1e7, 1e7)?;
            graphic.scale.check(f64::MIN_POSITIVE, 1e4)?;
            let asset = graphics::prepare(
                graphic.shape,
                &fonts,
                &mut images,
                plan.fps,
                index,
                &graphic.rendering,
            )?;
            let mask = graphic
                .mask
                .map(|mask| graphics::Mask::compile(mask, index, asset.offset))
                .transpose()?;
            let filter = graphic
                .filter
                .map(|filter| filters::compile(filter, index))
                .transpose()?;
            let origin = graphic.origin.unwrap_or_else(|| asset.size.map(|v| v / 2.));
            if origin.iter().any(|v| !v.is_finite() || v.abs() > 1e7) {
                return Err(PyValueError::new_err("invalid transform origin"));
            }
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
                z_index: graphic.z_index.compile(),
                animated_order: false,
                rotation: graphic.rotation.compile(),
                scale: graphic.scale.compile(),
                origin,
                matrix: crate::values::matrix(graphic.matrix)?,
                mask,
                blend_mode: graphic.blend_mode,
                filter,
                asset,
                children: Vec::new(),
                depth,
            });
        }
        let order = |indices: &mut [usize], layers: &[Layer]| {
            let animated = indices
                .iter()
                .any(|i| !matches!(layers[*i].z_index, Value::Constant(_)));
            if !animated {
                indices.sort_by(|a, b| {
                    layers[*a]
                        .z_index
                        .value(0.)
                        .partial_cmp(&layers[*b].z_index.value(0.))
                        .unwrap_or(std::cmp::Ordering::Equal)
                });
            }
            animated
        };
        for i in 0..layers.len() {
            let mut children = std::mem::take(&mut layers[i].children);
            layers[i].animated_order = order(&mut children, &layers);
            layers[i].children = children;
        }
        let animated_roots = order(&mut roots, &layers);
        let Soundtrack { media, map } = audio::prepare(plan.sounds, duration)?;
        Ok(Self {
            backend: plan.backend,
            width,
            height,
            fps: plan.fps,
            layers,
            roots,
            animated_roots,
            fonts,
            media,
            timeline: ResolvedRenderingTimeline {
                audio_map: map,
                scenes: None,
                duration_in_frames: plan.frames,
            },
        })
    }

    fn node(
        &self,
        index: usize,
        frame: usize,
        cache: &mut crate::clips::Decoders,
    ) -> PyResult<Option<NestedNodeData<'_>>> {
        let layer = &self.layers[index];
        if frame < layer.first || frame >= layer.end {
            return Ok(None);
        }
        let time = frame as f64 / self.fps as f64 - layer.start;
        let opacity = layer.opacity.value(time);
        if opacity == 0. {
            return Ok(None);
        }
        let angle = layer.rotation.value(time).to_radians();
        let scale = layer.scale.value(time);
        let (sin, cos) = angle.sin_cos();
        let (a, b, c, d) = (cos * scale, sin * scale, -sin * scale, cos * scale);
        let [cx, cy] = layer.origin;
        let [ox, oy] = layer.asset.offset;
        let transform = Transform {
            a,
            b,
            c,
            d,
            e: layer.x.value(time) + cx + a * (ox - cx) + c * (oy - cy),
            f: layer.y.value(time) + cy + b * (ox - cx) + d * (oy - cy),
        };
        let transform = if let Some(matrix) = &layer.matrix {
            let [a, b, c, d, e, f] = std::array::from_fn(|i| matrix[i].value(time));
            Transform {
                a: a * transform.a + c * transform.b,
                b: b * transform.a + d * transform.b,
                c: a * transform.c + c * transform.d,
                d: b * transform.c + d * transform.d,
                e: a * transform.e + c * transform.f + e,
                f: b * transform.e + d * transform.f + f,
            }
        } else {
            transform
        };
        let mut children = if layer.asset.node.is_some() {
            vec![
                layer
                    .asset
                    .node_at(time, frame - layer.first, self.fps, cache)?,
            ]
        } else {
            self.nodes(&layer.children, layer.animated_order, frame, cache)?
        };
        let mut attributes = vec![
            attribute(AId::Transform, transform),
            attribute(AId::Opacity, opacity),
            attribute(AId::MixBlendMode, layer.blend_mode.as_svg()),
        ];
        if let Some(mask) = &layer.mask {
            children.push(Some(mask.node_at(time)));
            attributes.push(attribute(AId::ClipPath, format!("url(#clip-{index})")));
        }
        if let Some(filter) = &layer.filter {
            children.push(Some(graphics::borrow_node(filter)));
            attributes.push(attribute(AId::Filter, format!("url(#filter-{index})")));
        }
        Ok(Some(element(EId::G, attributes, children)))
    }

    fn nodes(
        &self,
        indices: &[usize],
        animated: bool,
        frame: usize,
        cache: &mut crate::clips::Decoders,
    ) -> PyResult<Vec<Option<NestedNodeData<'_>>>> {
        let mut indices = Cow::Borrowed(indices);
        if animated {
            let time = frame as f64 / self.fps as f64;
            indices.to_mut().sort_by(|a, b| {
                let (a, b) = (&self.layers[*a], &self.layers[*b]);
                a.z_index
                    .value(time - a.start)
                    .partial_cmp(&b.z_index.value(time - b.start))
                    .unwrap_or(std::cmp::Ordering::Equal)
            });
        }
        indices
            .iter()
            .map(|index| self.node(*index, frame, cache))
            .collect()
    }

    fn tree(&self, index: usize, cache: &mut FrameCache) -> PyResult<usvgr::Tree> {
        if index >= self.timeline.duration_in_frames {
            return Err(PyIndexError::new_err("frame index out of range"));
        }
        let doc = document(
            self.width,
            self.height,
            self.nodes(&self.roots, self.animated_roots, index, &mut cache.decoders)?,
        );
        usvgr::Tree::from_nested_svgtree_with_cache(
            &doc,
            &usvgr::Options::default(),
            &mut cache.trees,
            &self.fonts,
        )
        .map_err(render_error)
    }

    fn rasterize(&self, index: usize) -> PyResult<fframes::RgbaFrame> {
        let tree = self.tree(index, &mut FrameCache::default())?;
        crate::backend::Device::new(self.backend, self.width, self.height)?
            .frame()
            .render_tree(&tree, Color::TRANSPARENT, self.width, self.height)
            .map_err(render_error)
    }

    fn resources(&self) -> Resources<'_> {
        Resources {
            backend: self.backend,
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
            audio::samples(
                &self.media,
                self.timeline.audio_map.as_ref(),
                self.timeline.duration_in_frames,
                self.fps,
            )
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
    use fframes::{CpuFrameRenderer, FrameRenderer};

    fn plan() -> Result<Plan, serde_json::Error> {
        serde_json::from_str(include_str!("../../tests/assets/scene.json"))
    }

    #[test]
    fn cached_rasterization_moves_geometry_when_frames_are_requested_out_of_order() -> PyResult<()>
    {
        let plan = plan().map_err(|error| PyValueError::new_err(error.to_string()))?;
        let scene = SceneVideo::compile(plan)?;
        let mut cache = FrameCache::default();
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

    #[test]
    fn cached_geometry_keeps_animated_gradient_transforms() -> PyResult<()> {
        let mut plan = plan().map_err(|error| PyValueError::new_err(error.to_string()))?;
        plan.layers[0].graphic.position.x =
            input::Coordinate::Value(crate::values::Scalar::Constant(0.));
        if let input::Shape::Rectangle { fill, .. } = &mut plan.layers[0].graphic.shape {
            *fill = Some(serde_json::from_str(r##"{
                "kind":"linear_gradient", "start":[0,0], "end":[4,0], "units":"user", "spread":"pad",
                "stops":[{"offset":0,"color":"#ff0000"},{"offset":1,"color":"#0000ff"}],
                "matrix":[1,0,0,1,{"values":[0,-4,0],"fps":2},0]
            }"##).map_err(|error| PyValueError::new_err(error.to_string()))?);
        }
        let scene = SceneVideo::compile(plan)?;
        let mut cache = FrameCache::default();
        let mut renderer = CpuFrameRenderer::new(20);
        for index in [0, 1, 2, 1, 0] {
            let tree = scene.tree(index, &mut cache)?;
            let frame = renderer
                .render_tree(&tree, Color::TRANSPARENT, 16, 8)
                .map_err(render_error)?;
            if index == 1 {
                assert_eq!(&frame.pixels[..4], &[0, 0, 255, 255]);
            } else {
                assert!(frame.pixels[0] > 200, "gradient cache at frame {index}");
            }
        }
        Ok(())
    }
}
