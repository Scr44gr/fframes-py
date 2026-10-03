use std::path::PathBuf;

use fframes::animation::{AnimationRuntime as NativeTween, Easing as NativeEasing};
use pyo3::{PyResult, exceptions::PyValueError};
use serde::Deserialize;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Plan {
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
    #[serde(flatten)]
    pub shape: Shape,
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
pub(super) enum Scalar {
    Constant(f64),
    Tween {
        from_value: f64,
        to_value: f64,
        duration: f64,
        easing: Easing,
    },
}

impl Scalar {
    pub fn check(&self, low: f64, high: f64) -> PyResult<()> {
        let (a, b) = match self {
            Self::Constant(value) => (*value, *value),
            Self::Tween {
                from_value,
                to_value,
                duration,
                ..
            } => {
                if !duration.is_finite() || *duration <= 0. || *duration > 86400. {
                    return Err(PyValueError::new_err("invalid tween duration"));
                }
                (*from_value, *to_value)
            }
        };
        if !a.is_finite() || !b.is_finite() || a < low || a > high || b < low || b > high {
            return Err(PyValueError::new_err("scalar outside its supported range"));
        }
        Ok(())
    }

    pub fn compile(self) -> Value {
        match self {
            Self::Constant(value) => Value::Constant(value),
            Self::Tween {
                from_value,
                to_value,
                duration,
                easing,
            } => {
                let easing = easing.native();
                Value::Tween {
                    from: from_value,
                    delta: to_value - from_value,
                    duration,
                    animation: NativeTween::new(1., &easing),
                }
            }
        }
    }
}

pub(super) enum Value {
    Constant(f64),
    Tween {
        from: f64,
        delta: f64,
        duration: f64,
        animation: NativeTween,
    },
}

impl Value {
    pub fn value(&self, time: f64) -> f64 {
        match self {
            Self::Constant(value) => *value,
            Self::Tween {
                from,
                delta,
                duration,
                animation,
            } => {
                from + delta * f64::from(animation.solve(&((time / duration).clamp(0., 1.) as f32)))
            }
        }
    }
}

#[derive(Deserialize)]
#[serde(rename_all = "snake_case")]
pub(super) enum Easing {
    Linear,
    EaseIn,
    EaseOut,
    EaseInOut,
}

impl Easing {
    pub fn native(&self) -> NativeEasing {
        match self {
            Self::Linear => NativeEasing::Linear,
            Self::EaseIn => NativeEasing::EaseIn,
            Self::EaseOut => NativeEasing::EaseOut,
            Self::EaseInOut => NativeEasing::EaseInOut,
        }
    }
}

#[derive(Deserialize)]
#[serde(untagged)]
pub(super) enum Paint {
    Constant(String),
    Tween {
        from_value: String,
        to_value: String,
        duration: f64,
        easing: Easing,
    },
}

#[derive(Deserialize)]
#[serde(untagged)]
pub(super) enum TextContent {
    Constant(String),
    Template { template: String },
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
    Group {
        size: [f64; 2],
    },
    Rectangle {
        size: [f64; 2],
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

#[derive(Deserialize)]
pub(super) struct Sound {
    pub start: f64,
    pub end: f64,
    pub audio: Audio,
}

#[derive(Deserialize)]
pub(super) struct Audio {
    pub source: PathBuf,
    pub gain_db: f32,
    pub pan: f32,
    pub offset: f64,
    pub fade_in: f32,
    pub fade_out: f32,
    pub r#loop: bool,
}
