use std::path::PathBuf;

use crate::audio::Sound;
use crate::values::{Paint, Scalar};
use pyo3::{PyResult, exceptions::PyValueError};
use serde::Deserialize;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Plan {
    #[serde(default)]
    pub backend: crate::backend::Backend,
    pub resolution: [u32; 2],
    pub fps: usize,
    pub frames: usize,
    pub layers: Vec<Layer>,
    pub sounds: Vec<Sound>,
    pub fonts: Vec<PathBuf>,
    pub load_system_fonts: bool,
}

#[derive(Deserialize)]
pub(super) struct Layer {
    pub parent: Option<usize>,
    pub start: f64,
    pub end: f64,
    pub graphic: Graphic,
}

#[derive(Deserialize)]
pub(super) struct Graphic {
    pub position: Position,
    pub opacity: Scalar,
    pub rotation: Scalar,
    pub scale: Scalar,
    pub origin: Option<[f64; 2]>,
    pub mask: Option<Mask>,
    pub filter: Option<super::filters::Filter>,
    #[serde(flatten)]
    pub shape: Shape,
}

#[derive(Deserialize)]
pub(super) struct Mask {
    pub size: [f64; 2],
    pub radius: f64,
    pub position: [f64; 2],
}

#[derive(Deserialize)]
pub(super) struct Position {
    pub x: Coordinate,
    pub y: Coordinate,
}

#[derive(Deserialize)]
#[serde(untagged)]
pub(super) enum Coordinate {
    Value(Scalar),
    Align(String),
}

impl Coordinate {
    pub fn resolve(self, parent: f64, extent: f64, horizontal: bool) -> PyResult<Scalar> {
        match self {
            Self::Value(value) => {
                value.check(-1e7, 1e7)?;
                Ok(value)
            }
            Self::Align(name) => Ok(Scalar::Constant(match name.as_str() {
                "center" => (parent - extent) / 2.,
                "left" if horizontal => 0.,
                "top" if !horizontal => 0.,
                "right" if horizontal => parent - extent,
                "bottom" if !horizontal => parent - extent,
                _ => return Err(PyValueError::new_err("invalid alignment")),
            })),
        }
    }
}

#[derive(Deserialize)]
#[serde(untagged)]
pub(super) enum TextContent {
    Constant(String),
    Template { template: String },
    Frames { frames: Vec<String> },
}

#[derive(Default, Deserialize)]
#[serde(rename_all = "lowercase")]
pub(super) enum TextAnchor {
    #[default]
    Bounds,
    Baseline,
}

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase")]
pub(super) enum Shape {
    Video {
        source: PathBuf,
        offset: f64,
        r#loop: bool,
        size: [f64; 2],
    },
    Shader {
        shader: crate::shader::Input,
        size: [f64; 2],
    },
    Group {
        size: [f64; 2],
    },
    Rectangle {
        size: [Scalar; 2],
        radius: f64,
        fill: Option<Paint>,
        stroke: Option<Stroke>,
    },
    Circle {
        radius: f64,
        fill: Option<Paint>,
        stroke: Option<Stroke>,
    },
    Text {
        content: TextContent,
        fill: Paint,
        font_family: String,
        font_size: f64,
        font_weight: u16,
        #[serde(default)]
        anchor: TextAnchor,
        #[serde(default)]
        letter_spacing: f64,
        #[serde(default = "text_anchor")]
        text_anchor: String,
        #[serde(default = "baseline")]
        baseline: String,
        #[serde(default = "font_style")]
        font_style: String,
    },
    Path {
        size: [f64; 2],
        segments: Vec<Segment>,
        fill: Option<Paint>,
        stroke: Option<Stroke>,
    },
    Image {
        source: PathBuf,
        size: [f64; 2],
    },
}

fn text_anchor() -> String {
    "start".into()
}
fn baseline() -> String {
    "auto".into()
}
fn font_style() -> String {
    "normal".into()
}

#[derive(Deserialize)]
pub(super) struct Stroke {
    pub color: Paint,
    pub width: f64,
}

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase")]
pub(super) enum Segment {
    Move {
        x: f64,
        y: f64,
    },
    Line {
        x: f64,
        y: f64,
    },
    Cubic {
        control1: [f64; 2],
        control2: [f64; 2],
        end: [f64; 2],
    },
    Close,
}
