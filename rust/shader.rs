//! Compile shader inputs once and evaluate uniforms entirely in Rust.

use crate::{
    render::media_error,
    values::{ColorValue, Paint, Scalar, Value},
};
use fframes::{Frame, Shader, ShaderUniformValue, ShaderUniforms, usvgr};
use fframes_skia_renderer::skia_safe::runtime_effect::{ChildType, uniform::Type};
use pyo3::{PyResult, exceptions::PyValueError};
use serde::Deserialize;
use std::{collections::HashSet, path::PathBuf, sync::Arc};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Input {
    pub source: String,
    pub language: String,
    pub uniforms: Vec<Uniform>,
    #[serde(default)]
    pub time_offset: f64,
}

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase", deny_unknown_fields)]
pub(crate) enum Uniform {
    Float {
        name: String,
        value: Scalar,
    },
    Color {
        name: String,
        value: Paint,
    },
    Vector {
        name: String,
        value: Vec<Scalar>,
    },
    Int {
        name: String,
        value: i32,
    },
    Image {
        name: String,
        source: PathBuf,
    },
    Video {
        name: String,
        source: PathBuf,
        offset: f64,
        r#loop: bool,
    },
}

enum Binding {
    Float(Value),
    Color(ColorValue),
    Vector(Vec<Value>),
    Video(crate::clips::Source),
    Constant(ShaderUniformValue),
}

pub(crate) struct Program {
    shader: Shader,
    uniforms: Vec<(String, Binding)>,
    first: usize,
}

impl Program {
    pub fn compile(input: Input, fps: usize) -> PyResult<Self> {
        if !input.time_offset.is_finite() || !(0. ..=86400.).contains(&input.time_offset) {
            return Err(PyValueError::new_err("invalid shader time offset"));
        }
        let first = (input.time_offset * fps as f64 + 1e-9).floor() as usize;
        let shader = match input.language.as_str() {
            "sksl" => Shader::sksl(input.source),
            "shadertoy" => Shader::shadertoy(input.source),
            _ => return Err(PyValueError::new_err("unsupported shader language")),
        };
        // Upstream logs compilation failures and skips the layer. Surface them
        // before rendering so an invalid program cannot silently produce a video.
        let effect = fframes_skia_renderer::render::compile_shader(&shader)
            .map_err(PyValueError::new_err)?;
        let mut uniforms = Vec::with_capacity(input.uniforms.len());
        let mut names = HashSet::new();
        for uniform in input.uniforms {
            let (name, binding, ty) = match uniform {
                Uniform::Float { name, value } => {
                    value.check(-f64::from(f32::MAX), f64::from(f32::MAX))?;
                    (name, Binding::Float(value.compile()), Some(Type::Float))
                }
                Uniform::Color { name, value } => (
                    name,
                    Binding::Color(ColorValue::compile(value)?),
                    Some(Type::Float4),
                ),
                Uniform::Vector { name, value } => {
                    for coordinate in &value {
                        coordinate.check(-f64::from(f32::MAX), f64::from(f32::MAX))?;
                    }
                    let ty = match value.len() {
                        2 => Type::Float2,
                        3 => Type::Float3,
                        4 => Type::Float4,
                        _ => return Err(PyValueError::new_err("uniform vectors need 2–4 values")),
                    };
                    (
                        name,
                        Binding::Vector(value.into_iter().map(Scalar::compile).collect()),
                        Some(ty),
                    )
                }
                Uniform::Int { name, value } => (
                    name,
                    Binding::Constant(ShaderUniformValue::Int(value)),
                    Some(Type::Int),
                ),
                Uniform::Image { name, source } => {
                    let bytes = std::fs::read(&source)?;
                    let image = fframes::media::decode_image(&source.to_string_lossy(), &bytes)
                        .map_err(media_error)?;
                    (
                        name,
                        Binding::Constant(ShaderUniformValue::Image(Arc::new(image))),
                        None,
                    )
                }
                Uniform::Video {
                    name,
                    source,
                    offset,
                    r#loop,
                } => (
                    name,
                    Binding::Video(crate::clips::Source::open(
                        crate::clips::Input {
                            source,
                            offset,
                            r#loop,
                        },
                        fps,
                    )?),
                    None,
                ),
            };
            if !names.insert(name.clone())
                || matches!(
                    name.as_str(),
                    "iTime" | "iFrame" | "iResolution" | "iTimeDelta"
                )
            {
                return Err(PyValueError::new_err(
                    "duplicate or reserved shader uniform",
                ));
            }
            let matches = match ty {
                Some(ty) => effect
                    .uniforms()
                    .iter()
                    .any(|u| u.name() == name && u.ty() == ty),
                None => effect
                    .children()
                    .iter()
                    .any(|u| u.name() == name && u.ty() == ChildType::Shader),
            };
            if !matches {
                return Err(PyValueError::new_err(format!(
                    "shader uniform {name:?} is absent or has a different type"
                )));
            }
            uniforms.push((name, binding));
        }
        Ok(Self {
            shader,
            uniforms,
            first,
        })
    }

    pub fn draw(
        &self,
        index: usize,
        fps: usize,
        cache: &mut crate::clips::Decoders,
    ) -> PyResult<Arc<usvgr::PreloadedImageData>> {
        let frame = Frame::new(index + self.first, index + self.first, fps);
        // Keep sample selection on the integer frame grid. Upstream's f32
        // seconds can round down (for example frame 54 at 60 fps) and repeat
        // the previous sample or decoded video frame.
        let time = (index + self.first) as f64 / fps as f64;
        let mut uniforms = ShaderUniforms::new();
        for (name, binding) in &self.uniforms {
            uniforms = match binding {
                Binding::Float(value) => uniforms.float(name.clone(), value.value(time) as f32),
                Binding::Color(value) => uniforms.color(name.clone(), value.value(time)),
                Binding::Vector(values) => {
                    let coordinate = |i: usize| values[i].value(time) as f32;
                    let value = match values.len() {
                        2 => ShaderUniformValue::Float2([coordinate(0), coordinate(1)]),
                        3 => ShaderUniformValue::Float3([
                            coordinate(0),
                            coordinate(1),
                            coordinate(2),
                        ]),
                        _ => ShaderUniformValue::Float4([
                            coordinate(0),
                            coordinate(1),
                            coordinate(2),
                            coordinate(3),
                        ]),
                    };
                    uniforms.set(name.clone(), value)
                }
                Binding::Video(source) => {
                    let image = source.image(time, fps, cache)?.unwrap_or_else(transparent);
                    uniforms.set(name.clone(), ShaderUniformValue::Image(image))
                }
                Binding::Constant(value) => uniforms.set(name.clone(), value.clone()),
            };
        }
        Ok(self.shader.draw(&frame, uniforms).href())
    }
}

fn transparent() -> Arc<usvgr::PreloadedImageData> {
    static PIXEL: std::sync::OnceLock<Arc<usvgr::PreloadedImageData>> = std::sync::OnceLock::new();
    Arc::clone(PIXEL.get_or_init(|| {
        Arc::new(usvgr::PreloadedImageData::new_blended(
            "fframes-py:transparent".into(),
            1,
            1,
            &[0; 4],
        ))
    }))
}
