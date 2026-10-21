//! Shared compiled 3D coordinates and HDR colors.

use crate::values::{ColorValue, Paint, Scalar, Value};
use fframes::three_d::{Rgb, Vec3};
use pyo3::PyResult;
use serde::Deserialize;

pub(super) fn scalar(input: Scalar, low: f64, high: f64) -> PyResult<Value> {
    input.check(low, high)?;
    Ok(input.compile())
}

pub(super) struct Vector([Value; 3]);

impl Vector {
    pub fn compile(input: [Scalar; 3]) -> PyResult<Self> {
        for v in &input {
            v.check(-1e7, 1e7)?;
        }
        Ok(Self(input.map(Scalar::compile)))
    }

    pub fn at(&self, time: f64) -> Vec3 {
        Vec3::from_array(std::array::from_fn(|i| self.0[i].value(time) as f32))
    }
}

#[derive(Deserialize)]
#[serde(untagged)]
pub(super) enum ColorInput {
    Linear([f32; 3]),
    Srgb(Paint),
}

pub(super) enum Color {
    Linear(Rgb),
    Srgb(ColorValue),
}

impl ColorInput {
    pub fn compile(self) -> PyResult<Color> {
        Ok(match self {
            Self::Linear(c) => Color::Linear(Rgb(Vec3::from_array(c))),
            Self::Srgb(p) => Color::Srgb(ColorValue::compile(p)?),
        })
    }
}

impl Color {
    pub fn animated(&self) -> bool {
        !matches!(
            self,
            Self::Linear(_)
                | Self::Srgb(ColorValue::Interpolate {
                    progress: Value::Constant(_),
                    ..
                })
        )
    }
    pub fn at(&self, time: f64) -> Rgb {
        match self {
            Self::Linear(c) => *c,
            Self::Srgb(c) => {
                let c = c.value(time);
                Rgb::srgb8(c.r, c.g, c.b)
            }
        }
    }
}
