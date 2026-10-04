//! Compile vector commands once; only changing coordinates are evaluated per frame.

use fframes::usvgr::svgtree::svgrtypes::{PathParser, PathSegment};
use pyo3::{exceptions::PyValueError, prelude::*};
use serde::Deserialize;

use crate::values::{Scalar, Value};

#[derive(Deserialize)]
#[serde(untagged)]
pub(super) enum Input {
    Data(String),
    Segments(Vec<Segment>),
}

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase")]
pub(super) enum Segment {
    Move { x: Scalar, y: Scalar },
    Line { x: Scalar, y: Scalar },
    Cubic(Box<Cubic>),
    Close,
}

#[derive(Deserialize)]
pub(super) struct Cubic {
    control1: [Scalar; 2],
    control2: [Scalar; 2],
    end: [Scalar; 2],
}

pub(super) enum Command {
    Move([Value; 2]),
    Line([Value; 2]),
    Cubic(Box<[Value; 6]>),
}

impl Command {
    pub fn sample(&self, time: f64) -> PathSegment {
        match self {
            Self::Move([x, y]) => PathSegment::MoveTo {
                abs: true,
                x: x.value(time),
                y: y.value(time),
            },
            Self::Line([x, y]) => PathSegment::LineTo {
                abs: true,
                x: x.value(time),
                y: y.value(time),
            },
            Self::Cubic(values) => {
                let [x1, y1, x2, y2, x, y] = values.as_ref();
                PathSegment::CurveTo {
                    abs: true,
                    x1: x1.value(time),
                    y1: y1.value(time),
                    x2: x2.value(time),
                    y2: y2.value(time),
                    x: x.value(time),
                    y: y.value(time),
                }
            }
        }
    }

    fn animated(&self) -> bool {
        let values: &[Value] = match self {
            Self::Move(values) | Self::Line(values) => values,
            Self::Cubic(values) => values.as_ref(),
        };
        values
            .iter()
            .any(|value| !matches!(value, Value::Constant(_)))
    }
}

pub(super) struct Path {
    pub segments: Vec<PathSegment>,
    pub animations: Vec<(usize, Command)>,
}

fn values<const N: usize>(values: [Scalar; N]) -> PyResult<[Value; N]> {
    for value in &values {
        value.check(-f64::MAX, f64::MAX)?;
    }
    Ok(values.map(Scalar::compile))
}

impl Path {
    pub fn compile(input: Input) -> PyResult<Self> {
        let input = match input {
            Input::Data(data) => {
                return Ok(Self {
                    segments: parse(&data)?,
                    animations: Vec::new(),
                });
            }
            Input::Segments(input) => input,
        };
        if input.len() < 2 || !matches!(input.first(), Some(Segment::Move { .. })) {
            return Err(PyValueError::new_err(
                "path requires MoveTo and at least two segments",
            ));
        }
        let mut segments = Vec::with_capacity(input.len());
        let mut animations = Vec::new();
        for segment in input {
            let command = match segment {
                Segment::Move { x, y } => Command::Move(values([x, y])?),
                Segment::Line { x, y } => Command::Line(values([x, y])?),
                Segment::Cubic(cubic) => {
                    let Cubic {
                        control1: [x1, y1],
                        control2: [x2, y2],
                        end: [x, y],
                    } = *cubic;
                    Command::Cubic(Box::new(values([x1, y1, x2, y2, x, y])?))
                }
                Segment::Close => {
                    segments.push(PathSegment::ClosePath { abs: true });
                    continue;
                }
            };
            segments.push(command.sample(0.));
            if command.animated() {
                animations.push((segments.len() - 1, command));
            }
        }
        Ok(Self {
            segments,
            animations,
        })
    }
}

fn parse(source: &str) -> PyResult<Vec<PathSegment>> {
    let segments = PathParser::from(source)
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| PyValueError::new_err(error.to_string()))?;
    if segments.len() < 2 || !matches!(segments.first(), Some(PathSegment::MoveTo { .. })) {
        return Err(PyValueError::new_err(
            "path requires an initial moveto and drawing commands",
        ));
    }
    Ok(segments)
}

#[pyfunction]
pub(crate) fn validate_path(source: &str) -> PyResult<()> {
    parse(source).map(|_| ())
}
