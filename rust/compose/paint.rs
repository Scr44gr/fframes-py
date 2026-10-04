use std::path::PathBuf;

use fframes::usvgr::svgtree::{AId, Attribute, EId, NestedNodeData, svgrtypes::Transform};
use pyo3::{PyResult, exceptions::PyValueError};
use serde::Deserialize;

use super::graphics::{Images, attribute, borrow_node, element, image};
use super::input::Stroke;
use crate::color::parse;
use crate::values::{ColorValue, Paint, Scalar, Value, matrix};

#[derive(Deserialize)]
#[serde(untagged)]
pub(super) enum Brush {
    Color(Paint),
    Server(Box<Server>),
}

#[derive(Deserialize)]
pub(super) struct Stop {
    offset: f64,
    color: String,
}

#[derive(Deserialize)]
pub(super) struct Gradient {
    stops: Vec<Stop>,
    units: String,
    spread: String,
    matrix: Option<[Scalar; 6]>,
}

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub(super) enum Server {
    LinearGradient {
        start: [f64; 2],
        end: [f64; 2],
        #[serde(flatten)]
        gradient: Gradient,
    },
    RadialGradient {
        center: [f64; 2],
        radius: f64,
        focus: Option<[f64; 2]>,
        #[serde(flatten)]
        gradient: Gradient,
    },
    Pattern {
        source: PathBuf,
        size: [f64; 2],
        matrix: Option<[Scalar; 6]>,
    },
}

struct Definition {
    node: NestedNodeData<'static>,
    matrix: Option<[Value; 6]>,
}

#[derive(Default)]
pub(super) struct Paints {
    colors: Vec<(usize, ColorValue)>,
    definitions: Vec<Definition>,
}

impl Paints {
    pub fn is_empty(&self) -> bool {
        self.colors.is_empty() && self.definitions.is_empty()
    }

    pub fn wrap<'a>(&'a self, mut node: NestedNodeData<'a>, time: f64) -> NestedNodeData<'a> {
        for (index, color) in &self.colors {
            node.attrs[*index].value = color.value(time).into();
        }
        if self.definitions.is_empty() {
            return node;
        }
        let definitions = self
            .definitions
            .iter()
            .map(|definition| {
                let mut node = borrow_node(&definition.node);
                if let Some(matrix) = &definition.matrix {
                    let [a, b, c, d, e, f] = std::array::from_fn(|i| matrix[i].value(time));
                    node.attrs[1].value = Transform { a, b, c, d, e, f }.into();
                }
                Some(node)
            })
            .collect();
        element(
            EId::G,
            vec![],
            vec![Some(element(EId::Defs, vec![], definitions)), Some(node)],
        )
    }

    pub fn apply(
        &mut self,
        attrs: &mut Vec<Attribute<'static>>,
        fill: Option<Brush>,
        stroke: Option<Stroke>,
        numbers: &mut Vec<(usize, Value)>,
        images: &mut Images,
        index: usize,
    ) -> PyResult<()> {
        self.color(attrs, AId::Fill, fill, images, index)?;
        if let Some(stroke) = stroke {
            if !stroke.width.is_finite()
                || stroke.width <= 0.
                || stroke.width > 1e7
                || !stroke.miter_limit.is_finite()
                || stroke.miter_limit < 1.
                || stroke.dash.iter().any(|v| !v.is_finite() || *v < 0.)
                || !matches!(stroke.cap.as_str(), "butt" | "round" | "square")
                || !matches!(stroke.join.as_str(), "miter" | "round" | "bevel")
            {
                return Err(PyValueError::new_err("invalid stroke"));
            }
            self.color(attrs, AId::Stroke, Some(stroke.color), images, index)?;
            attrs.extend([
                attribute(AId::StrokeWidth, stroke.width),
                attribute(AId::StrokeLinecap, stroke.cap),
                attribute(AId::StrokeLinejoin, stroke.join),
                attribute(AId::StrokeMiterlimit, stroke.miter_limit),
            ]);
            if !stroke.dash.is_empty() {
                attrs.push(attribute(
                    AId::StrokeDasharray,
                    stroke
                        .dash
                        .iter()
                        .map(f64::to_string)
                        .collect::<Vec<_>>()
                        .join(" "),
                ));
                stroke.dash_offset.check(-1e7, 1e7)?;
                let animated = !matches!(stroke.dash_offset, Scalar::Constant(_));
                let value = stroke.dash_offset.compile();
                let initial = value.value(0.);
                if animated {
                    numbers.push((attrs.len(), value));
                }
                attrs.push(attribute(AId::StrokeDashoffset, initial));
            }
        }
        Ok(())
    }

    fn color(
        &mut self,
        attrs: &mut Vec<Attribute<'static>>,
        name: AId,
        value: Option<Brush>,
        images: &mut Images,
        index: usize,
    ) -> PyResult<()> {
        let value = match value {
            None => "none".into(),
            Some(Brush::Color(Paint::Constant(value))) => parse(&value)?.into(),
            Some(Brush::Color(paint)) => {
                let value = ColorValue::compile(paint)?;
                let initial = value.value(0.);
                self.colors.push((attrs.len(), value));
                initial.into()
            }
            Some(Brush::Server(server)) => {
                let id = format!("paint-{index}-{}", self.definitions.len());
                self.definitions.push(compile(*server, &id, images)?);
                format!("url(#{id})").into()
            }
        };
        attrs.push(Attribute { name, value });
        Ok(())
    }
}

fn compile(server: Server, id: &str, images: &mut Images) -> PyResult<Definition> {
    let (tag, mut attrs, gradient) = match server {
        Server::Pattern {
            source,
            size,
            matrix: transform,
        } => {
            for value in size {
                super::graphics::length(value)?;
            }
            return Ok(Definition {
                node: element(
                    EId::Pattern,
                    vec![
                        attribute(AId::Id, id.to_owned()),
                        attribute(AId::PatternTransform, Transform::default()),
                        attribute(AId::PatternUnits, "userSpaceOnUse"),
                        attribute(AId::Width, size[0]),
                        attribute(AId::Height, size[1]),
                    ],
                    vec![Some(element(
                        EId::Image,
                        vec![
                            attribute(AId::Href, image(source, images)?),
                            attribute(AId::Width, size[0]),
                            attribute(AId::Height, size[1]),
                            attribute(AId::PreserveAspectRatio, "none"),
                        ],
                        vec![],
                    ))],
                ),
                matrix: matrix(transform)?,
            });
        }
        Server::LinearGradient {
            start,
            end,
            gradient,
        } => (
            EId::LinearGradient,
            vec![
                attribute(AId::X1, start[0]),
                attribute(AId::Y1, start[1]),
                attribute(AId::X2, end[0]),
                attribute(AId::Y2, end[1]),
            ],
            gradient,
        ),
        Server::RadialGradient {
            center,
            radius,
            focus,
            gradient,
        } => {
            super::graphics::length(radius)?;
            let focus = focus.unwrap_or(center);
            (
                EId::RadialGradient,
                vec![
                    attribute(AId::Cx, center[0]),
                    attribute(AId::Cy, center[1]),
                    attribute(AId::R, radius),
                    attribute(AId::Fx, focus[0]),
                    attribute(AId::Fy, focus[1]),
                ],
                gradient,
            )
        }
    };
    if gradient.stops.len() < 2
        || gradient
            .stops
            .windows(2)
            .any(|pair| pair[0].offset > pair[1].offset)
        || !matches!(gradient.spread.as_str(), "pad" | "reflect" | "repeat")
    {
        return Err(PyValueError::new_err("invalid gradient"));
    }
    let units = match gradient.units.as_str() {
        "bounds" => "objectBoundingBox",
        "user" => "userSpaceOnUse",
        _ => return Err(PyValueError::new_err("invalid gradient units")),
    };
    let mut attributes = vec![
        attribute(AId::Id, id.to_owned()),
        attribute(AId::GradientTransform, Transform::default()),
        attribute(AId::GradientUnits, units),
        attribute(AId::SpreadMethod, gradient.spread),
    ];
    attributes.append(&mut attrs);
    let children = gradient
        .stops
        .into_iter()
        .map(|stop| {
            if !stop.offset.is_finite() || !(0. ..=1.).contains(&stop.offset) {
                return Err(PyValueError::new_err("invalid gradient stop"));
            }
            let color = parse(&stop.color)?;
            Ok(Some(element(
                EId::Stop,
                vec![
                    attribute(AId::Offset, stop.offset),
                    attribute(AId::StopColor, color),
                ],
                vec![],
            )))
        })
        .collect::<PyResult<Vec<_>>>()?;
    Ok(Definition {
        node: element(tag, attributes, children),
        matrix: matrix(gradient.matrix)?,
    })
}
