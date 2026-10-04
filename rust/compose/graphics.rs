use std::{borrow::Cow, collections::HashMap, path::PathBuf, sync::Arc};

use fframes::usvgr::{
    self,
    svgtree::{
        AId, Attribute, EId, NestedNodeData, NestedNodeKind, NestedSvgDocument, StringStorage,
        SvgAttributeValue,
    },
};
use pyo3::{PyResult, exceptions::PyValueError};

use super::input::{Shape, Stroke, TextAnchor, TextContent};
use super::text::Template;
use crate::color::parse as parse_color;
use crate::render::{media_error, render_error};
use crate::values::{ColorValue, Paint, Scalar, Value};

pub(super) struct Asset {
    pub node: Option<NestedNodeData<'static>>,
    pub size: [f64; 2],
    pub offset: [f64; 2],
    colors: Vec<AnimatedPaint>,
    template: Option<Template>,
    text_frames: Vec<String>,
    shader: Option<crate::shader::Program>,
    numbers: Vec<(usize, Value)>,
    clip: Option<crate::clips::Source>,
    path_animation: Vec<(usize, super::paths::Command)>,
}

struct AnimatedPaint {
    index: usize,
    value: ColorValue,
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
            node.attrs[0].value = shader.draw(frame, fps).into();
        }
        for color in &self.colors {
            node.attrs[color.index].value = color.value.value(time).into();
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
        Ok(Some(node))
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

fn paint(
    attrs: &mut Vec<Attribute<'static>>,
    fill: Option<Paint>,
    stroke: Option<Stroke>,
    animations: &mut Vec<AnimatedPaint>,
) -> PyResult<()> {
    color(attrs, AId::Fill, fill, animations)?;
    if let Some(stroke) = stroke {
        length(stroke.width)?;
        color(attrs, AId::Stroke, Some(stroke.color), animations)?;
        attrs.push(attribute(AId::StrokeWidth, stroke.width));
    }
    Ok(())
}

fn color(
    attrs: &mut Vec<Attribute<'static>>,
    name: AId,
    value: Option<Paint>,
    animations: &mut Vec<AnimatedPaint>,
) -> PyResult<()> {
    let value = match value {
        Some(Paint::Constant(value)) => parse_color(&value)?.into(),
        Some(paint @ Paint::Tween { .. }) => {
            let value = ColorValue::compile(paint)?;
            let from = value.value(0.);
            animations.push(AnimatedPaint {
                index: attrs.len(),
                value,
            });
            from.into()
        }
        None => "none".into(),
    };
    attrs.push(Attribute { name, value });
    Ok(())
}

fn length(value: f64) -> PyResult<()> {
    if !value.is_finite() || value <= 0. || value > 1e7 {
        return Err(PyValueError::new_err("invalid graphic size"));
    }
    Ok(())
}

pub(super) fn mask(
    mask: super::input::Mask,
    index: usize,
    offset: [f64; 2],
) -> PyResult<NestedNodeData<'static>> {
    for length_value in mask.size {
        length(length_value)?;
    }
    if !mask.radius.is_finite()
        || mask.radius < 0.
        || mask.radius > 1e7
        || mask
            .position
            .iter()
            .any(|v| !v.is_finite() || v.abs() > 1e7)
    {
        return Err(PyValueError::new_err("invalid clipping mask"));
    }
    Ok(element(
        EId::Defs,
        vec![],
        vec![Some(element(
            EId::ClipPath,
            vec![attribute(AId::Id, format!("clip-{index}"))],
            vec![Some(element(
                EId::Rect,
                vec![
                    attribute(AId::Width, mask.size[0]),
                    attribute(AId::Height, mask.size[1]),
                    attribute(AId::Rx, mask.radius),
                    attribute(AId::X, mask.position[0] - offset[0]),
                    attribute(AId::Y, mask.position[1] - offset[1]),
                ],
                vec![],
            ))],
        ))],
    ))
}

pub(super) fn prepare(
    shape: Shape,
    fonts: &usvgr::fontdb::Database,
    images: &mut Images,
    fps: usize,
) -> PyResult<Asset> {
    let mut offset = [0., 0.];
    let mut colors = Vec::new();
    let mut template = None;
    let mut text_frames = Vec::new();
    let mut shader = None;
    let mut numbers = Vec::new();
    let mut clip = None;
    let mut path_animation = Vec::new();
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
            shader = Some(crate::shader::Program::compile(input)?);
            (
                Some(element(
                    EId::Image,
                    vec![
                        attribute(AId::Href, ""),
                        attribute(AId::Width, size[0]),
                        attribute(AId::Height, size[1]),
                        attribute(AId::PreserveAspectRatio, "none"),
                    ],
                    vec![],
                )),
                size,
            )
        }
        Shape::Group { size } => (None, size),
        Shape::Rectangle {
            size,
            radius,
            fill,
            stroke,
        } => {
            if !radius.is_finite() || radius < 0. {
                return Err(PyValueError::new_err("invalid radius"));
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
            paint(&mut attrs, fill, stroke, &mut colors)?;
            (Some(element(EId::Rect, attrs, vec![])), extent)
        }
        Shape::Circle {
            radius,
            fill,
            stroke,
        } => {
            length(radius)?;
            let mut attrs = vec![
                attribute(AId::Cx, radius),
                attribute(AId::Cy, radius),
                attribute(AId::R, radius),
            ];
            paint(&mut attrs, fill, stroke, &mut colors)?;
            (
                Some(element(EId::Circle, attrs, vec![])),
                [radius * 2., radius * 2.],
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
            paint(&mut attrs, fill, stroke, &mut colors)?;
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
            paint(&mut attrs, fill, stroke, &mut colors)?;
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
            if !matches!(&content, TextContent::Constant(_))
                && !matches!(anchor, TextAnchor::Baseline)
            {
                return Err(PyValueError::new_err(
                    "dynamic text requires baseline anchoring",
                ));
            }
            let content = match content {
                TextContent::Constant(content) => content,
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
            let text = NestedNodeData {
                kind: NestedNodeKind::Text(StringStorage::new_owned(content)),
                attrs: Box::new([]),
                children: vec![],
                static_hash: None,
            };
            let mut attrs = vec![
                attribute(AId::FontFamily, font_family),
                attribute(AId::FontSize, font_size),
                attribute(AId::FontWeight, font_weight.to_string()),
                attribute(AId::LetterSpacing, letter_spacing),
                attribute(AId::TextAnchor, text_anchor),
                attribute(AId::DominantBaseline, baseline),
                attribute(AId::FontStyle, font_style),
            ];
            paint(&mut attrs, fill, stroke, &mut colors)?;
            let node = element(EId::Text, attrs, vec![Some(text)]);
            let doc = document(1, 1, vec![Some(borrow_node(&node))]);
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
            let source = source.canonicalize()?;
            let image = if let Some(image) = images.get(&source) {
                Arc::clone(image)
            } else {
                let bytes = std::fs::read(&source)?;
                let data = fframes::media::decode_image(&source.to_string_lossy(), &bytes)
                    .map_err(media_error)?;
                let image = Arc::new(data);
                images.insert(source, Arc::clone(&image));
                image
            };
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
    length(size[0])?;
    length(size[1])?;
    if let Some(node) = node.as_mut().filter(|_| {
        colors.is_empty()
            && template.is_none()
            && text_frames.is_empty()
            && shader.is_none()
            && numbers.is_empty()
            && clip.is_none()
            && path_animation.is_empty()
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
        colors,
        template,
        text_frames,
        shader,
        numbers,
        clip,
        path_animation,
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
