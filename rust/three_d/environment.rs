//! Environment lighting and atmosphere shared by both rasterizers.

use super::values::{Color, ColorInput, scalar};
use crate::{
    render::render_error,
    values::{Scalar, Value},
};
use fframes::three_d::{
    Background, Environment, EnvironmentMap, Fog, Reflector, SoftBox, Studio, Vec3,
};
use pyo3::PyResult;
use serde::Deserialize;
use std::{path::PathBuf, sync::Arc};

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase")]
pub(super) enum Input {
    Studio(Box<StudioInput>),
    Map {
        source: MapSource,
        intensity: Scalar,
        rotation: Scalar,
    },
}

#[derive(Deserialize)]
pub(super) struct StudioInput {
    intensity: Scalar,
    rotation: Scalar,
    sky: ColorInput,
    horizon: ColorInput,
    ground: ColorInput,
    softboxes: Option<Vec<BoxInput>>,
}

#[derive(Deserialize)]
#[serde(untagged)]
pub(super) enum MapSource {
    File(PathBuf),
    Pixels {
        size: [usize; 2],
        pixels: Vec<[f32; 3]>,
    },
}

impl MapSource {
    fn load(self) -> PyResult<EnvironmentMap> {
        match self {
            Self::File(path) => EnvironmentMap::decode(&std::fs::read(path)?).map_err(render_error),
            Self::Pixels {
                size: [width, height],
                pixels,
            } => {
                if width == 0 || height == 0 || pixels.len() != width.saturating_mul(height) {
                    return Err(pyo3::exceptions::PyValueError::new_err(
                        "environment pixels must contain width * height RGB values",
                    ));
                }
                Ok(EnvironmentMap::from_linear(
                    width,
                    height,
                    pixels.into_iter().map(Vec3::from).collect(),
                ))
            }
        }
    }
}

#[derive(Deserialize)]
pub(super) struct BoxInput {
    direction: [f32; 3],
    half_size: [f32; 2],
    color: ColorInput,
}

#[derive(Deserialize)]
#[serde(untagged)]
pub(super) enum BackgroundInput {
    Environment { kind: EnvironmentTag, blur: f32 },
    Color(ColorInput),
}

#[derive(Deserialize)]
#[serde(rename_all = "lowercase")]
pub(super) enum EnvironmentTag {
    Environment,
}

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase")]
pub(super) enum FogInput {
    Linear {
        color: ColorInput,
        near: f32,
        far: f32,
    },
    Exp2 {
        color: ColorInput,
        density: f32,
    },
}

#[derive(Deserialize)]
pub(super) struct ReflectorInput {
    pub point: [f32; 3],
    pub normal: [f32; 3],
    pub scale: f32,
}

pub(super) enum BackgroundProgram {
    Transparent,
    Environment(f32),
    Color(Color),
}

pub(super) enum Program {
    None,
    Studio(Box<StudioProgram>),
    Map {
        map: Arc<EnvironmentMap>,
        intensity: Value,
        rotation: Value,
    },
}

pub(super) struct StudioProgram {
    intensity: Value,
    rotation: Value,
    sky: Color,
    horizon: Color,
    ground: Color,
    softboxes: Vec<(SoftBox, Color)>,
}

impl Input {
    pub fn compile(self) -> PyResult<Program> {
        Ok(match self {
            Self::Map {
                source,
                intensity,
                rotation,
            } => Program::Map {
                map: Arc::new(source.load()?),
                intensity: scalar(intensity, 0., 1e7)?,
                rotation: scalar(rotation, -1e7, 1e7)?,
            },
            Self::Studio(studio) => {
                let StudioInput {
                    intensity,
                    rotation,
                    sky,
                    horizon,
                    ground,
                    softboxes,
                } = *studio;
                let softboxes = match softboxes {
                    Some(boxes) => boxes
                        .into_iter()
                        .map(|b| {
                            let color = b.color.compile()?;
                            Ok((
                                SoftBox {
                                    direction: Vec3::from(b.direction).normalize_or(Vec3::Y),
                                    half_size: b.half_size.into(),
                                    color: color.at(0.),
                                },
                                color,
                            ))
                        })
                        .collect::<PyResult<_>>()?,
                    None => match Environment::studio() {
                        Environment::Studio(s) => s
                            .softboxes
                            .into_iter()
                            .map(|b| {
                                let color = Color::Linear(b.color);
                                (b, color)
                            })
                            .collect(),
                        _ => Vec::new(),
                    },
                };
                Program::Studio(Box::new(StudioProgram {
                    intensity: scalar(intensity, 0., 1e7)?,
                    rotation: scalar(rotation, -1e7, 1e7)?,
                    sky: sky.compile()?,
                    horizon: horizon.compile()?,
                    ground: ground.compile()?,
                    softboxes,
                }))
            }
        })
    }
}

impl Program {
    pub fn at(&self, time: f64) -> Environment {
        match self {
            Self::None => Environment::None,
            Self::Map {
                map,
                intensity,
                rotation,
            } => Environment::Map {
                map: Arc::clone(map),
                intensity: intensity.value(time) as f32,
                rotation: rotation.value(time) as f32,
            },
            Self::Studio(studio) => {
                let StudioProgram {
                    intensity,
                    rotation,
                    sky,
                    horizon,
                    ground,
                    softboxes,
                } = studio.as_ref();
                Environment::Studio(Studio {
                    sky: sky.at(time),
                    horizon: horizon.at(time),
                    ground: ground.at(time),
                    intensity: intensity.value(time) as f32,
                    rotation: rotation.value(time) as f32,
                    softboxes: softboxes
                        .iter()
                        .map(|(b, c)| SoftBox {
                            color: c.at(time),
                            ..b.clone()
                        })
                        .collect(),
                })
            }
        }
    }
}

impl BackgroundInput {
    pub fn compile(self) -> PyResult<BackgroundProgram> {
        Ok(match self {
            Self::Environment {
                kind: EnvironmentTag::Environment,
                blur,
            } => BackgroundProgram::Environment(blur),
            Self::Color(c) => BackgroundProgram::Color(c.compile()?),
        })
    }
}

impl BackgroundProgram {
    pub fn at(&self, time: f64) -> Background {
        match self {
            Self::Transparent => Background::Transparent,
            Self::Environment(blur) => Background::Environment { blur: *blur },
            Self::Color(c) => Background::Color(c.at(time)),
        }
    }
}

pub(super) enum FogProgram {
    Linear { color: Color, near: f32, far: f32 },
    Exp2 { color: Color, density: f32 },
}

impl FogInput {
    pub fn compile(self) -> PyResult<FogProgram> {
        Ok(match self {
            Self::Linear { color, near, far } => FogProgram::Linear {
                color: color.compile()?,
                near,
                far,
            },
            Self::Exp2 { color, density } => FogProgram::Exp2 {
                color: color.compile()?,
                density,
            },
        })
    }
}

impl FogProgram {
    pub fn at(&self, time: f64) -> Fog {
        match self {
            Self::Linear { color, near, far } => Fog::Linear {
                color: color.at(time),
                near: *near,
                far: *far,
            },
            Self::Exp2 { color, density } => Fog::Exp2 {
                color: color.at(time),
                density: *density,
            },
        }
    }
}

impl ReflectorInput {
    pub fn compile(self) -> Reflector {
        Reflector::new(self.point.into(), self.normal.into()).scale(self.scale)
    }
}
