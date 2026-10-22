//! PBR material values sampled on the native scene clock.

use super::{
    texture,
    values::{Color, ColorInput, scalar},
};
use crate::{
    render::FrameCache,
    values::{Scalar, Value},
};
use fframes::three_d::{Blending, Material, Shading, Side};
use pyo3::PyResult;
use serde::Deserialize;

#[derive(Deserialize)]
pub(super) struct Input {
    shading: Shader,
    color: ColorInput,
    opacity: Scalar,
    metalness: Scalar,
    roughness: Scalar,
    emissive: ColorInput,
    emissive_intensity: Scalar,
    clearcoat: Scalar,
    clearcoat_roughness: Scalar,
    reflection: Scalar,
    env_intensity: Scalar,
    flat_shading: bool,
    side: Face,
    blending: Blend,
    transparent: bool,
    depth_write: bool,
    map: Option<texture::Input>,
    emissive_map: Option<texture::Input>,
    metal_rough_map: Option<texture::Input>,
    normal_map: Option<texture::Input>,
    normal_scale: Scalar,
    ao_map: Option<texture::Input>,
    fog: bool,
}

#[derive(Deserialize)]
#[serde(rename_all = "snake_case")]
enum Shader {
    Standard,
    Unlit,
    ShadowCatcher,
    Normals,
}

#[derive(Deserialize)]
#[serde(rename_all = "lowercase")]
enum Face {
    Front,
    Back,
    Double,
}

#[derive(Deserialize, Clone, Copy)]
#[serde(rename_all = "lowercase")]
pub(super) enum Blend {
    Normal,
    Additive,
}

impl Blend {
    pub fn native(self) -> Blending {
        match self {
            Self::Normal => Blending::Normal,
            Self::Additive => Blending::Additive,
        }
    }
}

pub(super) struct Program {
    base: Material,
    color: Color,
    emissive: Color,
    values: [Value; 9],
    maps: [Option<texture::Program>; 5],
}

impl Input {
    pub fn compile(self, fps: usize, buffers: &crate::buffers::Buffers) -> PyResult<Program> {
        Ok(Program {
            base: Material {
                shading: match self.shading {
                    Shader::Standard => Shading::Standard,
                    Shader::Unlit => Shading::Unlit,
                    Shader::ShadowCatcher => Shading::ShadowCatcher,
                    Shader::Normals => Shading::Normals,
                },
                side: match self.side {
                    Face::Front => Side::Front,
                    Face::Back => Side::Back,
                    Face::Double => Side::Double,
                },
                flat_shading: self.flat_shading,
                blending: self.blending.native(),
                transparent: self.transparent,
                depth_write: self.depth_write,
                fog: self.fog,
                ..Default::default()
            },
            color: self.color.compile()?,
            emissive: self.emissive.compile()?,
            values: [
                scalar(self.opacity, 0., 1.)?,
                scalar(self.metalness, 0., 1.)?,
                scalar(self.roughness, 0., 1.)?,
                scalar(self.emissive_intensity, 0., 1e7)?,
                scalar(self.clearcoat, 0., 1.)?,
                scalar(self.clearcoat_roughness, 0., 1.)?,
                scalar(self.reflection, 0., 1.)?,
                scalar(self.env_intensity, 0., 1e7)?,
                scalar(self.normal_scale, 0., 1e7)?,
            ],
            maps: [
                self.map.map(|t| t.compile(fps, buffers)).transpose()?,
                self.emissive_map
                    .map(|t| t.compile(fps, buffers))
                    .transpose()?,
                self.metal_rough_map
                    .map(|t| t.compile(fps, buffers))
                    .transpose()?,
                self.normal_map
                    .map(|t| t.compile(fps, buffers))
                    .transpose()?,
                self.ao_map.map(|t| t.compile(fps, buffers)).transpose()?,
            ],
        })
    }
}

impl Program {
    pub fn at(
        &self,
        time: f64,
        cache: &mut FrameCache,
        rasterizer: &crate::backend::Rasterizer<'_>,
    ) -> PyResult<Material> {
        let mut material = self.base.clone();
        material.color = self.color.at(time);
        material.emissive = self.emissive.at(time);
        let [
            opacity,
            metalness,
            roughness,
            emissive_intensity,
            clearcoat,
            clearcoat_roughness,
            reflection,
            env_intensity,
            normal_scale,
        ] = self.values.each_ref().map(|v| v.value(time) as f32);
        material.opacity = opacity;
        material.metalness = metalness;
        material.roughness = roughness;
        material.emissive_intensity = emissive_intensity;
        material.clearcoat = clearcoat;
        material.clearcoat_roughness = clearcoat_roughness;
        material.reflection = reflection;
        material.env_intensity = env_intensity;
        material.normal_scale = normal_scale;
        let map = |i: usize, cache: &mut FrameCache| {
            self.maps[i]
                .as_ref()
                .map(|p| p.at(time, cache, rasterizer))
                .transpose()
        };
        material.map = map(0, cache)?;
        material.emissive_map = map(1, cache)?;
        material.metal_rough_map = map(2, cache)?;
        material.normal_map = map(3, cache)?;
        material.ao_map = map(4, cache)?;
        Ok(material)
    }
}
