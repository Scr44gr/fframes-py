use std::path::PathBuf;

use super::paint::Brush;
use crate::audio::Sound;
use crate::values::Scalar;
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
    pub matrix: Option<[Scalar; 6]>,
    #[serde(default)]
    pub rendering: String,
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
    Runs(Vec<TextRun>),
    Template { template: String },
    Frames { frames: Vec<String> },
}

#[derive(Deserialize)]
pub(super) struct TextRun {
    pub content: String,
    pub font_family: Option<String>,
    pub font_size: Option<f64>,
    pub font_weight: Option<u16>,
    pub fill: Option<String>,
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
        #[serde(default)]
        fit: Fit,
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
        fill: Option<Brush>,
        stroke: Option<Stroke>,
    },
    Circle {
        radius: f64,
        fill: Option<Brush>,
        stroke: Option<Stroke>,
    },
    Ellipse {
        size: [f64; 2],
        fill: Option<Brush>,
        stroke: Option<Stroke>,
    },
    Text {
        content: TextContent,
        fill: Option<Brush>,
        stroke: Option<Stroke>,
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
        segments: super::paths::Input,
        fill: Option<Brush>,
        stroke: Option<Stroke>,
    },
    Image {
        source: PathBuf,
        size: [f64; 2],
        #[serde(default)]
        fit: Fit,
    },
}

#[derive(Default, Deserialize)]
#[serde(rename_all = "lowercase")]
pub(super) enum Fit {
    #[default]
    Fill,
    Contain,
    Cover,
}

impl Fit {
    pub fn as_svg(&self) -> &'static str {
        match self {
            Self::Fill => "none",
            Self::Contain => "xMidYMid meet",
            Self::Cover => "xMidYMid slice",
        }
    }
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
    pub color: Brush,
    pub width: f64,
    #[serde(default = "cap")]
    pub cap: String,
    #[serde(default = "join")]
    pub join: String,
    #[serde(default = "miter_limit")]
    pub miter_limit: f64,
    #[serde(default)]
    pub dash: Vec<f64>,
    #[serde(default = "dash_offset")]
    pub dash_offset: Scalar,
}

fn cap() -> String {
    "butt".into()
}
fn join() -> String {
    "miter".into()
}
fn miter_limit() -> f64 {
    4.
}
fn dash_offset() -> Scalar {
    Scalar::Constant(0.)
}
