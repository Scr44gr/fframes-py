use std::{borrow::Cow, collections::HashMap, path::PathBuf, str::FromStr, sync::Arc};

use fframes::usvgr::{
    self,
    svgtree::{
        AId, Attribute, EId, NestedNodeData, NestedNodeKind, NestedSvgDocument, StringStorage,
        SvgAttributeValue,
        svgrtypes::{self, PathSegment},
    },
};
use pyo3::{PyResult, exceptions::PyValueError};

use super::input::{Segment, Shape, Stroke};
use crate::render::{media_error, render_error};

pub(super) struct Asset {
    pub node: Option<NestedNodeData<'static>>,
    pub size: [f64; 2],
    pub offset: [f64; 2],
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
    fill: Option<String>,
    stroke: Option<Stroke>,
) -> PyResult<()> {
    attrs.push(color(AId::Fill, fill)?);
    if let Some(stroke) = stroke {
        length(stroke.width)?;
        attrs.push(color(AId::Stroke, Some(stroke.color))?);
        attrs.push(attribute(AId::StrokeWidth, stroke.width));
    }
    Ok(())
}

fn color(name: AId, value: Option<String>) -> PyResult<Attribute<'static>> {
    match value {
        Some(value) => {
            let parsed = svgrtypes::Color::from_str(&value)
                .map_err(|_| PyValueError::new_err("invalid color"))?;
            Ok(Attribute {
                name,
                value: SvgAttributeValue::Color(parsed),
            })
        }
        None => Ok(attribute(name, "none")),
    }
}

fn length(value: f64) -> PyResult<()> {
    if !value.is_finite() || value <= 0. || value > 1e7 {
        return Err(PyValueError::new_err("invalid graphic size"));
    }
    Ok(())
}

pub(super) fn prepare(
    shape: Shape,
    fonts: &usvgr::fontdb::Database,
    images: &mut Images,
) -> PyResult<Asset> {
    let mut offset = [0., 0.];
    let (mut node, size) = match shape {
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
            let mut attrs = vec![
                attribute(AId::Width, size[0]),
                attribute(AId::Height, size[1]),
                attribute(AId::Rx, radius),
            ];
            paint(&mut attrs, fill, stroke)?;
            (Some(element(EId::Rect, attrs, vec![])), size)
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
            paint(&mut attrs, fill, stroke)?;
            (
                Some(element(EId::Circle, attrs, vec![])),
                [radius * 2., radius * 2.],
            )
        }
        Shape::Path {
            size,
            segments,
            fill,
            stroke,
        } => {
            if !matches!(segments.first(), Some(Segment::Move { .. })) {
                return Err(PyValueError::new_err("path must begin with MoveTo"));
            }
            let segments = segments
                .into_iter()
                .map(|segment| match segment {
                    Segment::Move { x, y } => PathSegment::MoveTo { abs: true, x, y },
                    Segment::Line { x, y } => PathSegment::LineTo { abs: true, x, y },
                    Segment::Cubic {
                        control1: [x1, y1],
                        control2: [x2, y2],
                        end: [x, y],
                    } => PathSegment::CurveTo {
                        abs: true,
                        x1,
                        y1,
                        x2,
                        y2,
                        x,
                        y,
                    },
                    Segment::Close => PathSegment::ClosePath { abs: true },
                })
                .collect::<Vec<_>>();
            let mut attrs = vec![attribute(AId::D, segments)];
            paint(&mut attrs, fill, stroke)?;
            (Some(element(EId::Path, attrs, vec![])), size)
        }
        Shape::Text {
            content,
            fill,
            font_family,
            font_size,
            font_weight,
        } => {
            length(font_size)?;
            if fonts.is_empty() {
                return Err(PyValueError::new_err(
                    "text requires a font; supply fonts or enable system fonts",
                ));
            }
            let text = NestedNodeData {
                kind: NestedNodeKind::Text(StringStorage::new_owned(content)),
                attrs: Box::new([]),
                children: vec![],
                static_hash: None,
            };
            let node = element(
                EId::Text,
                vec![
                    color(AId::Fill, Some(fill))?,
                    attribute(AId::FontFamily, font_family),
                    attribute(AId::FontSize, font_size),
                    attribute(AId::FontWeight, font_weight.to_string()),
                ],
                vec![Some(text)],
            );
            let doc = document(1, 1, vec![Some(borrow_node(&node))]);
            let tree = usvgr::Tree::from_nested_svgtree(&doc, &usvgr::Options::default(), fonts)
                .map_err(render_error)?;
            let bounds = tree.root().bounding_box();
            offset = [-f64::from(bounds.x()), -f64::from(bounds.y())];
            // Whitespace has no ink but remains a valid text component.
            let size = [
                f64::from(bounds.width()).max(1.),
                f64::from(bounds.height()).max(1.),
            ];
            (Some(node), size)
        }
        Shape::Image { source, size } => {
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
                        attribute(AId::PreserveAspectRatio, "none"),
                    ],
                    vec![],
                )),
                size,
            )
        }
    };
    length(size[0])?;
    length(size[1])?;
    if let Some(node) = node.as_mut() {
        // Include the element tag, which compute_runtime_hash expects in its seed.
        node.static_hash = Some(node.compute_runtime_hash(match node.kind {
            NestedNodeKind::Element { tag_name } => tag_name as u64,
            _ => 0,
        }));
    }
    Ok(Asset { node, size, offset })
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
