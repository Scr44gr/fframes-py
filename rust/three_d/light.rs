//! Lights and their native animated parameters.

use super::values::{Color, ColorInput, Vector, scalar};
use crate::values::{Scalar, Value};
use fframes::three_d::{Aabb, DirectionalLight, Light, PointLight, Shadow, SpotLight};
use pyo3::PyResult;
use serde::Deserialize;

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub(super) enum Input {
    Ambient {
        color: ColorInput,
        intensity: Scalar,
    },
    Hemisphere {
        sky: ColorInput,
        ground: ColorInput,
        intensity: Scalar,
    },
    Directional {
        color: ColorInput,
        intensity: Scalar,
        direction: [Scalar; 3],
        shadow: Option<ShadowInput>,
    },
    Point {
        color: ColorInput,
        intensity: Scalar,
        distance: Scalar,
        decay: Scalar,
    },
    Spot {
        color: ColorInput,
        intensity: Scalar,
        distance: Scalar,
        decay: Scalar,
        direction: [Scalar; 3],
        angle: f32,
        penumbra: Scalar,
    },
}

#[derive(Deserialize)]
pub(super) struct ShadowInput {
    map_size: u32,
    softness: f32,
    strength: f32,
    bias: f32,
    bounds: Option<[[f32; 3]; 2]>,
}

pub(super) enum Program {
    Ambient(Color, Value),
    Hemisphere(Color, Color, Value),
    Directional {
        color: Color,
        intensity: Value,
        direction: Vector,
        shadow: Option<Shadow>,
    },
    Point {
        color: Color,
        intensity: Value,
        distance: Value,
        decay: Value,
    },
    Spot {
        color: Color,
        intensity: Value,
        distance: Value,
        decay: Value,
        direction: Vector,
        angle: f32,
        penumbra: Value,
    },
}

impl Input {
    pub fn compile(self) -> PyResult<Program> {
        let positive = |v| scalar(v, 0., 1e7);
        Ok(match self {
            Self::Ambient { color, intensity } => {
                Program::Ambient(color.compile()?, positive(intensity)?)
            }
            Self::Hemisphere {
                sky,
                ground,
                intensity,
            } => Program::Hemisphere(sky.compile()?, ground.compile()?, positive(intensity)?),
            Self::Directional {
                color,
                intensity,
                direction,
                shadow,
            } => Program::Directional {
                color: color.compile()?,
                intensity: positive(intensity)?,
                direction: Vector::compile(direction)?,
                shadow: shadow.map(|s| Shadow {
                    map_size: s.map_size,
                    softness: s.softness,
                    strength: s.strength,
                    bias: s.bias,
                    bounds: s.bounds.map(|[min, max]| Aabb {
                        min: min.into(),
                        max: max.into(),
                    }),
                }),
            },
            Self::Point {
                color,
                intensity,
                distance,
                decay,
            } => Program::Point {
                color: color.compile()?,
                intensity: positive(intensity)?,
                distance: positive(distance)?,
                decay: positive(decay)?,
            },
            Self::Spot {
                color,
                intensity,
                distance,
                decay,
                direction,
                angle,
                penumbra,
            } => Program::Spot {
                color: color.compile()?,
                intensity: positive(intensity)?,
                distance: positive(distance)?,
                decay: positive(decay)?,
                direction: Vector::compile(direction)?,
                angle,
                penumbra: scalar(penumbra, 0., 1.)?,
            },
        })
    }
}

impl Program {
    pub fn at(&self, time: f64) -> PyResult<Light> {
        let normalize = |value: &Vector| {
            let value = value.at(time);
            value.try_normalize().ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err(format!(
                    "light direction must be nonzero at {time}s"
                ))
            })
        };
        let v = |v: &Value| v.value(time) as f32;
        Ok(match self {
            Self::Ambient(color, intensity) => Light::ambient(color.at(time), v(intensity)),
            Self::Hemisphere(sky, ground, intensity) => {
                Light::hemisphere(sky.at(time), ground.at(time), v(intensity))
            }
            Self::Directional {
                color,
                intensity,
                direction,
                shadow,
            } => Light::Directional(DirectionalLight {
                color: color.at(time),
                intensity: v(intensity),
                direction: normalize(direction)?,
                shadow: shadow.clone(),
            }),
            Self::Point {
                color,
                intensity,
                distance,
                decay,
            } => Light::Point(PointLight {
                color: color.at(time),
                intensity: v(intensity),
                distance: v(distance),
                decay: v(decay),
            }),
            Self::Spot {
                color,
                intensity,
                distance,
                decay,
                direction,
                angle,
                penumbra,
            } => Light::Spot(SpotLight {
                color: color.at(time),
                intensity: v(intensity),
                distance: v(distance),
                decay: v(decay),
                direction: normalize(direction)?,
                angle: *angle,
                penumbra: v(penumbra),
            }),
        })
    }
}
