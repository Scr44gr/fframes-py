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
}

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase", deny_unknown_fields)]
pub(crate) enum Uniform {
    Float { name: String, value: Scalar },
    Color { name: String, value: Paint },
    Vector { name: String, value: Vec<f32> },
    Int { name: String, value: i32 },
    Image { name: String, source: PathBuf },
}

enum Binding {
    Float(Value),
    Color(ColorValue),
    Constant(ShaderUniformValue),
}

pub(crate) struct Program {
    shader: Shader,
    uniforms: Vec<(String, Binding)>,
}

impl Program {
    pub fn compile(input: Input) -> PyResult<Self> {
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
                    if value.iter().any(|v| !v.is_finite()) {
                        return Err(PyValueError::new_err("uniform vector must be finite"));
                    }
                    let (value, ty) = match value.as_slice() {
                        [a, b] => (ShaderUniformValue::Float2([*a, *b]), Type::Float2),
                        [a, b, c] => (ShaderUniformValue::Float3([*a, *b, *c]), Type::Float3),
                        [a, b, c, d] => {
                            (ShaderUniformValue::Float4([*a, *b, *c, *d]), Type::Float4)
                        }
                        _ => return Err(PyValueError::new_err("uniform vectors need 2–4 values")),
                    };
                    (name, Binding::Constant(value), Some(ty))
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
        Ok(Self { shader, uniforms })
    }

    pub fn draw(&self, index: usize, fps: usize) -> Arc<usvgr::PreloadedImageData> {
        let frame = Frame::new(index, index, fps);
        let time = f64::from(frame.seconds());
        let mut uniforms = ShaderUniforms::new();
        for (name, binding) in &self.uniforms {
            uniforms = match binding {
                Binding::Float(value) => uniforms.float(name.clone(), value.value(time) as f32),
                Binding::Color(value) => uniforms.color(name.clone(), value.value(time)),
                Binding::Constant(value) => uniforms.set(name.clone(), value.clone()),
            };
        }
        self.shader.draw(&frame, uniforms).href()
    }
}
