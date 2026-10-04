use std::{borrow::Cow, collections::HashMap, path::PathBuf, sync::Arc};

use fframes::usvgr::{
    self,
    svgtree::{
        AId, Attribute, EId, NestedNodeData, NestedNodeKind, NestedSvgDocument, StringStorage,
        SvgAttributeValue,
    },
};
use pyo3::{PyResult, exceptions::PyValueError};

use super::input::{Shape, TextAnchor, TextContent};
use super::paint::Paints;
use super::text::Template;
use crate::render::{media_error, render_error};
use crate::values::{Scalar, Value};

pub(super) struct Asset {
    pub node: Option<NestedNodeData<'static>>,
    pub size: [f64; 2],
    pub offset: [f64; 2],
    paints: Paints,
    template: Option<Template>,
    text_frames: Vec<String>,
    shader: Option<crate::shader::Program>,
    numbers: Vec<(usize, Value)>,
    clip: Option<crate::clips::Source>,
    path_animation: Vec<(usize, super::paths::Command)>,
    radius: Option<Value>,
}

impl Asset {
    pub fn node_at(
        &self,
        time: f64,
        frame: usize,
        fps: usize,
        cache: &mut crate::clips::Decoders,
    ) -> PyResult<Option<NestedNodeData<'_>>> {
        let Some(source) = self.node.as_ref() else {
            return Ok(None);
        };
        let mut node = borrow_node(source);
        if let Some(radius) = &self.radius {
            let value = radius.value(time);
            for attr in &mut node.attrs[..3] {
                attr.value = value.into();
            }
        }
        if !self.path_animation.is_empty()
            && let SvgAttributeValue::PathData(segments) = &mut node.attrs[0].value
        {
            let segments = segments.to_mut();
            for (index, command) in &self.path_animation {
                segments[*index] = command.sample(time);
            }
        }
        if let Some(clip) = &self.clip {
            let Some(image) = clip.image(time, fps, cache)? else {
                return Ok(None);
            };
            node.attrs[0].value = image.into();
        }
        if let Some(shader) = &self.shader {
            node.attrs[0].value = shader.draw(frame, fps, cache)?.into();
        }
        for (index, value) in &self.numbers {
            node.attrs[*index].value = value.value(time).into();
        }
        if let Some(template) = &self.template
            && let Some(Some(text)) = node.children.first_mut()
        {
            text.kind =
                NestedNodeKind::Text(StringStorage::new_owned(template.render(frame, time)));
        }
        if !self.text_frames.is_empty()
            && let Some(Some(text)) = node.children.first_mut()
        {
            let content = &self.text_frames[frame.min(self.text_frames.len() - 1)];
            text.kind = NestedNodeKind::Text(StringStorage::Borrowed(content));
        }
        Ok(Some(self.paints.wrap(node, time)))
    }
}

pub(super) type Images = HashMap<PathBuf, Arc<usvgr::PreloadedImageData>>;

pub(super) fn attribute<'a>(name: AId, value: impl Into<SvgAttributeValue<'a>>) -> Attribute<'a> {
    Attribute {
        name,
        value: value.into(),
    }
}

pub(super) fn element<'a>(
    tag_name: EId,
    attrs: Vec<Attribute<'a>>,
    children: Vec<Option<NestedNodeData<'a>>>,
) -> NestedNodeData<'a> {
    NestedNodeData {
        kind: NestedNodeKind::Element { tag_name },
        attrs: attrs.into_boxed_slice(),
        children,
        static_hash: None,
    }
}

pub(super) fn document(
    width: u32,
    height: u32,
    children: Vec<Option<NestedNodeData<'_>>>,
) -> NestedSvgDocument<'_> {
    NestedSvgDocument::from_nodes(vec![Some(element(
        EId::Svg,
        vec![attribute(AId::Width, width), attribute(AId::Height, height)],
        children,
    ))])
}

pub(super) fn length(value: f64) -> PyResult<()> {
    if !value.is_finite() || value <= 0. || value > 1e7 {
        return Err(PyValueError::new_err("invalid graphic size"));
    }
    Ok(())
}

pub(super) struct Mask {
    index: usize,
    values: [Value; 5],
    offset: [f64; 2],
}

impl Mask {
    pub fn compile(input: super::input::Mask, index: usize, offset: [f64; 2]) -> PyResult<Self> {
        for value in &input.size {
            value.check(f64::MIN_POSITIVE, 1e7)?;
        }
        input.radius.check(0., 1e7)?;
        for value in &input.position {
            value.check(-1e7, 1e7)?;
        }
        let [width, height] = input.size;
        let [x, y] = input.position;
        Ok(Self {
            index,
            values: [width, height, input.radius, x, y].map(Scalar::compile),
            offset,
        })
    }

    pub fn node_at(&self, time: f64) -> NestedNodeData<'static> {
        let [width, height, radius, x, y] = std::array::from_fn(|i| self.values[i].value(time));
        element(
            EId::Defs,
            vec![],
            vec![Some(element(
                EId::ClipPath,
                vec![attribute(AId::Id, format!("clip-{}", self.index))],
                vec![Some(element(
                    EId::Rect,
                    vec![
                        attribute(AId::Width, width),
                        attribute(AId::Height, height),
                        attribute(AId::Rx, radius),
                        attribute(AId::X, x - self.offset[0]),
                        attribute(AId::Y, y - self.offset[1]),
                    ],
                    vec![],
                ))],
            ))],
        )
    }
}

pub(super) fn prepare(
    shape: Shape,
    fonts: &usvgr::fontdb::Database,
    images: &mut Images,
    fps: usize,
    index: usize,
    rendering: &str,
) -> PyResult<Asset> {
    let mut offset = [0., 0.];
    let mut paints = Paints::default();
    let mut template = None;
    let mut text_frames = Vec::new();
    let mut shader = None;
    let mut numbers = Vec::new();
    let mut clip = None;
    let mut path_animation = Vec::new();
    let mut animated_radius = None;
    let (mut node, size) = match shape {
        Shape::Video {
            source,
            offset,
            r#loop,
            size,
            fit,
        } => {
            clip = Some(crate::clips::Source::open(
                crate::clips::Input {
                    source,
                    offset,
                    r#loop,
                },
                fps,
            )?);
            (
                Some(element(
                    EId::Image,
                    vec![
                        attribute(AId::Href, ""),
                        attribute(AId::Width, size[0]),
                        attribute(AId::Height, size[1]),
                        attribute(AId::PreserveAspectRatio, fit.as_svg()),
                    ],
                    vec![],
                )),
                size,
            )
        }
        Shape::Shader {
            shader: input,
            size,
        } => {
            shader = Some(crate::shader::Program::compile(input, fps)?);
            let mut extent = [0., 0.];
            for (i, value) in size.into_iter().enumerate() {
                value.check(f64::MIN_POSITIVE, 1e7)?;
                let animated = !matches!(value, Scalar::Constant(_));
                let value = value.compile();
                extent[i] = value.value(0.);
                if animated {
                    numbers.push((i + 1, value));
                }
            }
            (
                Some(element(
                    EId::Image,
                    vec![
                        attribute(AId::Href, ""),
                        attribute(AId::Width, extent[0]),
                        attribute(AId::Height, extent[1]),
                        attribute(AId::PreserveAspectRatio, "none"),
                    ],
                    vec![],
                )),
                extent,
            )
        }
        Shape::Group { size } => (None, size),
        Shape::Rectangle {
            size,
            radius,
            fill,
            stroke,
        } => {
            radius.check(0., 1e7)?;
            let animated = !matches!(radius, Scalar::Constant(_));
            let value = radius.compile();
            let radius = value.value(0.);
            if animated {
                numbers.push((2, value));
            }
            let mut extent = [0., 0.];
            for (index, value) in size.into_iter().enumerate() {
                value.check(f64::MIN_POSITIVE, 1e7)?;
                let animated = !matches!(value, Scalar::Constant(_));
                let value = value.compile();
                extent[index] = value.value(0.);
                if animated {
                    numbers.push((index, value));
                }
            }
            let mut attrs = vec![
                attribute(AId::Width, extent[0]),
                attribute(AId::Height, extent[1]),
                attribute(AId::Rx, radius),
            ];
            paints.apply(&mut attrs, fill, stroke, &mut numbers, images, index)?;
            (Some(element(EId::Rect, attrs, vec![])), extent)
        }
        Shape::Circle {
            radius,
            fill,
            stroke,
        } => {
            radius.check(0., 1e7)?;
            let animated = !matches!(radius, Scalar::Constant(_));
            let value = radius.compile();
            let radius = value.value(0.);
            if animated {
                animated_radius = Some(value);
            }
            let mut attrs = vec![
                attribute(AId::Cx, radius),
                attribute(AId::Cy, radius),
                attribute(AId::R, radius),
            ];
            paints.apply(&mut attrs, fill, stroke, &mut numbers, images, index)?;
            (
                Some(element(EId::Circle, attrs, vec![])),
                [if radius == 0. { 1. } else { radius * 2. }; 2],
            )
        }
        Shape::Ellipse { size, fill, stroke } => {
            let [rx, ry] = size.map(|v| v / 2.);
            let mut attrs = vec![
                attribute(AId::Cx, rx),
                attribute(AId::Cy, ry),
                attribute(AId::Rx, rx),
                attribute(AId::Ry, ry),
            ];
            paints.apply(&mut attrs, fill, stroke, &mut numbers, images, index)?;
            (Some(element(EId::Ellipse, attrs, vec![])), size)
        }
        Shape::Path {
            size,
            segments,
            fill,
            stroke,
        } => {
            let path = super::paths::Path::compile(segments)?;
            path_animation = path.animations;
            let segments = path.segments;
            let mut attrs = vec![attribute(AId::D, segments)];
            paints.apply(&mut attrs, fill, stroke, &mut numbers, images, index)?;
            (Some(element(EId::Path, attrs, vec![])), size)
        }
        Shape::Text {
            content,
            fill,
            stroke,
            font_family,
            font_size,
            font_weight,
            anchor,
            letter_spacing,
            text_anchor,
            baseline,
            font_style,
        } => {
            length(font_size)?;
            if !letter_spacing.is_finite() {
                return Err(PyValueError::new_err("letter spacing must be finite"));
            }
            if fonts.is_empty() {
                return Err(PyValueError::new_err(
                    "text requires a font; supply fonts or enable system fonts",
                ));
            }
            if matches!(
                &content,
                TextContent::Template { .. } | TextContent::Frames { .. }
            ) && !matches!(anchor, TextAnchor::Baseline)
            {
                return Err(PyValueError::new_err(
                    "dynamic text requires baseline anchoring",
                ));
            }
            let mut runs = Vec::new();
            let content = match content {
                TextContent::Constant(content) => content,
                TextContent::Runs(input) => {
                    if input.is_empty() {
                        return Err(PyValueError::new_err("text runs must not be empty"));
                    }
                    for run in input {
                        if run.content.is_empty() || run.content.contains(['\0', '\r', '\n']) {
                            return Err(PyValueError::new_err("text runs require single lines"));
                        }
                        if !run.dx.is_finite() || !run.dy.is_finite() {
                            return Err(PyValueError::new_err("text offsets must be finite"));
                        }
                        let mut attrs =
                            vec![attribute(AId::Dx, run.dx), attribute(AId::Dy, run.dy)];
                        if let Some(family) = run.font_family {
                            attrs.push(attribute(AId::FontFamily, family));
                        }
                        if let Some(size) = run.font_size {
                            length(size)?;
                            attrs.push(attribute(AId::FontSize, size));
                        }
                        if let Some(weight) = run.font_weight {
                            attrs.push(attribute(AId::FontWeight, weight.to_string()));
                        }
                        if let Some(fill) = run.fill {
                            attrs.push(attribute(AId::Fill, crate::color::parse(&fill)?));
                        }
                        runs.push(Some(element(
                            EId::Tspan,
                            attrs,
                            vec![Some(text_node(run.content))],
                        )));
                    }
                    String::new()
                }
                TextContent::Template { template: source } => {
                    let compiled = Template::compile(&source)?;
                    let content = compiled.render(0, 0.);
                    template = Some(compiled);
                    content
                }
                TextContent::Frames { frames } => {
                    if frames.is_empty()
                        || frames.iter().any(|line| line.contains(['\0', '\r', '\n']))
                    {
                        return Err(PyValueError::new_err("text frames require single lines"));
                    }
                    let first = frames[0].clone();
                    text_frames = frames;
                    first
                }
            };
            if runs.is_empty() {
                runs.push(Some(text_node(content)));
            }
            let mut attrs = vec![
                attribute(AId::FontFamily, font_family),
                attribute(AId::FontSize, font_size),
                attribute(AId::FontWeight, font_weight.to_string()),
                attribute(AId::LetterSpacing, letter_spacing),
                attribute(AId::TextAnchor, text_anchor),
                attribute(AId::DominantBaseline, baseline),
                attribute(AId::FontStyle, font_style),
            ];
            paints.apply(&mut attrs, fill, stroke, &mut numbers, images, index)?;
            let node = element(EId::Text, attrs, runs);
            let doc = document(1, 1, vec![Some(paints.wrap(borrow_node(&node), 0.))]);
            let tree = usvgr::Tree::from_nested_svgtree(&doc, &usvgr::Options::default(), fonts)
                .map_err(render_error)?;
            let bounds = tree.root().bounding_box();
            if matches!(anchor, TextAnchor::Bounds) {
                offset = [-f64::from(bounds.x()), -f64::from(bounds.y())];
            }
            // Whitespace has no ink but remains a valid text component.
            let size = [
                f64::from(bounds.width()).max(1.),
                f64::from(bounds.height()).max(1.),
            ];
            (Some(node), size)
        }
        Shape::Image { source, size, fit } => {
            let image = image(source, images)?;
            (
                Some(element(
                    EId::Image,
                    vec![
                        attribute(AId::Href, image),
                        attribute(AId::Width, size[0]),
                        attribute(AId::Height, size[1]),
                        attribute(AId::PreserveAspectRatio, fit.as_svg()),
                    ],
                    vec![],
                )),
                size,
            )
        }
    };
    if !matches!(
        rendering,
        "" | "auto" | "crispEdges" | "geometricPrecision" | "optimizeSpeed"
    ) {
        return Err(PyValueError::new_err("invalid shape rendering"));
    }
    if let Some(node) = &mut node {
        let mut attrs = node.attrs.to_vec();
        attrs.push(attribute(AId::ShapeRendering, rendering.to_owned()));
        node.attrs = attrs.into_boxed_slice();
    }
    length(size[0])?;
    length(size[1])?;
    if let Some(node) = node.as_mut().filter(|candidate| {
        paints.is_empty()
            && template.is_none()
            && text_frames.is_empty()
            && shader.is_none()
            && numbers.is_empty()
            && clip.is_none()
            && path_animation.is_empty()
            && animated_radius.is_none()
            // Upstream raster caches can reuse a viewport-clipped text group at
            // another placement. Keep text shaping cached, but not that group.
            && !matches!(candidate.kind, NestedNodeKind::Element { tag_name: EId::Text })
    }) {
        // Include the element tag, which compute_runtime_hash expects in its seed.
        node.static_hash = Some(node.compute_runtime_hash(match node.kind {
            NestedNodeKind::Element { tag_name } => tag_name as u64,
            _ => 0,
        }));
    }
    Ok(Asset {
        node,
        size,
        offset,
        paints,
        template,
        text_frames,
        shader,
        numbers,
        clip,
        path_animation,
        radius: animated_radius,
    })
}

pub(super) fn borrow_node<'a>(node: &'a NestedNodeData<'a>) -> NestedNodeData<'a> {
    let kind = match &node.kind {
        NestedNodeKind::Text(text) => NestedNodeKind::Text(StringStorage::Borrowed(text.as_str())),
        kind => kind.clone(),
    };
    let attrs = node
        .attrs
        .iter()
        .map(|attr| {
            let value = match &attr.value {
                SvgAttributeValue::PathData(data) => {
                    SvgAttributeValue::PathData(Cow::Borrowed(data))
                }
                SvgAttributeValue::StringStorage(text) => {
                    SvgAttributeValue::StringStorage(StringStorage::Borrowed(text.as_str()))
                }
                value => value.clone(),
            };
            Attribute {
                name: attr.name,
                value,
            }
        })
        .collect();
    NestedNodeData {
        kind,
        attrs,
        children: node
            .children
            .iter()
            .map(|node| node.as_ref().map(borrow_node))
            .collect(),
        static_hash: node.static_hash,
    }
}

pub(super) fn image(
    source: PathBuf,
    images: &mut Images,
) -> PyResult<Arc<usvgr::PreloadedImageData>> {
    let source = source.canonicalize()?;
    if let Some(image) = images.get(&source) {
        return Ok(Arc::clone(image));
    }
    let bytes = std::fs::read(&source)?;
    let data =
        fframes::media::decode_image(&source.to_string_lossy(), &bytes).map_err(media_error)?;
    let image = Arc::new(data);
    images.insert(source, Arc::clone(&image));
    Ok(image)
}

fn text_node(content: String) -> NestedNodeData<'static> {
    NestedNodeData {
        kind: NestedNodeKind::Text(StringStorage::new_owned(content)),
        attrs: Box::new([]),
        children: vec![],
        static_hash: None,
    }
}
