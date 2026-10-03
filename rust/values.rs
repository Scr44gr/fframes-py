//! Shared scalar and paint evaluation for layers and shader uniforms.

use crate::easing::Easing;
use fframes::animation::{Animatable, AnimationRuntime as NativeTween};
use pyo3::{PyResult, exceptions::PyValueError};
use serde::Deserialize;

#[derive(Deserialize)]
#[serde(untagged)]
pub(crate) enum Scalar {
    Constant(f64),
    Samples {
        values: Vec<f64>,
        fps: usize,
    },
    Tween {
        from_value: f64,
        to_value: f64,
        duration: f64,
        easing: Easing,
        #[serde(default)]
        start_at: f64,
    },
}

impl Scalar {
    pub fn check(&self, low: f64, high: f64) -> PyResult<()> {
        let (a, b) = match self {
            Self::Constant(value) => (*value, *value),
            Self::Samples { values, fps } => {
                if values.is_empty() || *fps == 0 || *fps > i32::MAX as usize {
                    return Err(PyValueError::new_err("invalid scalar samples"));
                }
                for value in values {
                    Self::Constant(*value).check(low, high)?;
                }
                return Ok(());
            }
            Self::Tween {
                from_value,
                to_value,
                duration,
                start_at,
                easing,
            } => {
                if !duration.is_finite()
                    || *duration <= 0.
                    || *duration > 86400.
                    || !start_at.is_finite()
                    || *start_at < 0.
                    || *start_at > 86400.
                    || (*duration as f32) == 0.
                {
                    return Err(PyValueError::new_err("invalid tween duration"));
                }
                (
                    *from_value,
                    from_value + (to_value - from_value) * easing.maximum(),
                )
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
            Self::Samples { values, fps } => Value::Samples { values, fps },
            Self::Tween {
                from_value,
                to_value,
                duration,
                easing,
                start_at,
            } => {
                let easing = easing.native();
                let animation = NativeTween::new(duration as f32, &easing);
                Value::Tween {
                    from: from_value,
                    delta: to_value - from_value,
                    duration: f64::from(animation.get_duration()),
                    start_at,
                    animation,
                }
            }
        }
    }
}

pub(crate) enum Value {
    Constant(f64),
    Samples {
        values: Vec<f64>,
        fps: usize,
    },
    Tween {
        from: f64,
        delta: f64,
        duration: f64,
        start_at: f64,
        animation: NativeTween,
    },
}

impl Value {
    pub fn value(&self, time: f64) -> f64 {
        match self {
            Self::Constant(value) => *value,
            Self::Samples { values, fps } => {
                let index = (time.max(0.) * *fps as f64 + 1e-9).floor() as usize;
                values[index.min(values.len() - 1)]
            }
            Self::Tween {
                from,
                delta,
                duration,
                start_at,
                animation,
            } => {
                let time = time - start_at;
                if time >= *duration {
                    from + delta
                } else {
                    from + delta * f64::from(animation.solve(&(time.max(0.) as f32)))
                }
            }
        }
    }
}

#[derive(Deserialize)]
#[serde(untagged)]
pub(crate) enum Paint {
    Constant(String),
    Tween {
        from_value: String,
        to_value: String,
        duration: f64,
        easing: Easing,
        #[serde(default)]
        start_at: f64,
    },
}

pub(crate) struct ColorValue {
    from: fframes::Color,
    to: fframes::Color,
    progress: Value,
}

impl ColorValue {
    pub fn compile(paint: Paint) -> PyResult<Self> {
        let (from, to, progress) = match paint {
            Paint::Constant(value) => {
                let color = crate::color::parse(&value)?;
                (color, color, Value::Constant(0.))
            }
            Paint::Tween {
                from_value,
                to_value,
                duration,
                easing,
                start_at,
            } => {
                let scalar = Scalar::Tween {
                    from_value: 0.,
                    to_value: 1.,
                    duration,
                    easing,
                    start_at,
                };
                scalar.check(-2., 2.)?;
                (
                    crate::color::parse(&from_value)?,
                    crate::color::parse(&to_value)?,
                    scalar.compile(),
                )
            }
        };
        Ok(Self { from, to, progress })
    }

    pub fn value(&self, time: f64) -> fframes::Color {
        self.from
            .apply_progress(&self.to, self.progress.value(time) as f32)
    }
}
