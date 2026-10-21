//! Camera animation and projection with upstream coordinate conventions.

use super::values::{Vector, scalar};
use crate::values::{Scalar, Value};
use fframes::three_d::{Camera, Focus, Vec2, Vec3};
use pyo3::{PyResult, exceptions::PyValueError};
use serde::Deserialize;

#[derive(Deserialize)]
pub(super) struct Input {
    position: [Scalar; 3],
    orbit: Option<Orbit>,
    target: [Scalar; 3],
    up: [f32; 3],
    fov: Scalar,
    ortho_height: Option<Scalar>,
    near: f32,
    far: f32,
    roll: Scalar,
    shift: [f32; 2],
    focus: Option<FocusInput>,
}

#[derive(Deserialize)]
struct FocusInput {
    distance: Option<Scalar>,
    point: Option<[Scalar; 3]>,
    blur: Scalar,
}

enum FocusTarget {
    Distance(Value),
    Point(Vector),
}
struct FocusProgram {
    target: FocusTarget,
    blur: Value,
}

#[derive(Deserialize)]
struct Orbit {
    distance: Scalar,
    azimuth: Scalar,
    elevation: Scalar,
}

pub(super) struct Program {
    base: Camera,
    position: Vector,
    target: Vector,
    fov: Value,
    ortho_height: Option<Value>,
    roll: Value,
    focus: Option<FocusProgram>,
    orbit: Option<[Value; 3]>,
}

impl Input {
    pub fn compile(self) -> PyResult<Program> {
        if self.near <= 0. || self.far <= self.near {
            return Err(PyValueError::new_err("camera requires 0 < near < far"));
        }
        let mut base = Camera::perspective(45.);
        base.up = Vec3::from(self.up).normalize_or(Vec3::Y);
        base.near = self.near;
        base.far = self.far;
        base.shift = Vec2::from(self.shift);
        Ok(Program {
            base,
            orbit: self
                .orbit
                .map(|o| {
                    Ok::<_, pyo3::PyErr>([
                        scalar(o.distance, f64::MIN_POSITIVE, 1e7)?,
                        scalar(o.azimuth, -1e7, 1e7)?,
                        scalar(o.elevation, -1e7, 1e7)?,
                    ])
                })
                .transpose()?,
            position: Vector::compile(self.position)?,
            target: Vector::compile(self.target)?,
            fov: scalar(self.fov, 0.001, 179.999)?,
            ortho_height: self
                .ortho_height
                .map(|v| scalar(v, f64::MIN_POSITIVE, 1e7))
                .transpose()?,
            roll: scalar(self.roll, -1e7, 1e7)?,
            focus: self
                .focus
                .map(|f| {
                    let target = match (f.distance, f.point) {
                        (Some(distance), None) => {
                            FocusTarget::Distance(scalar(distance, f64::MIN_POSITIVE, 1e7)?)
                        }
                        (None, Some(point)) => FocusTarget::Point(Vector::compile(point)?),
                        _ => {
                            return Err(PyValueError::new_err(
                                "focus requires exactly one of distance or point",
                            ));
                        }
                    };
                    Ok(FocusProgram {
                        target,
                        blur: scalar(f.blur, 0., 1e7)?,
                    })
                })
                .transpose()?,
        })
    }
}

impl Program {
    pub fn at(&self, time: f64) -> PyResult<Camera> {
        let mut camera = self.base;
        camera.position = self.position.at(time);
        camera.target = self.target.at(time);
        if let Some([distance, azimuth, elevation]) = &self.orbit {
            camera = camera.orbit(
                camera.target,
                distance.value(time) as f32,
                azimuth.value(time) as f32,
                elevation.value(time) as f32,
            );
        }
        let direction = camera.target - camera.position;
        if direction.length_squared() < 1e-12 || direction.cross(camera.up).length_squared() < 1e-12
        {
            return Err(PyValueError::new_err(format!(
                "camera at {time}s needs distinct position/target and an up vector not parallel to its viewing direction"
            )));
        }
        camera.fov = self.fov.value(time) as f32;
        camera.ortho_height = self.ortho_height.as_ref().map(|v| v.value(time) as f32);
        camera.roll = self.roll.value(time) as f32;
        if let Some(focus) = &self.focus {
            let blur = focus.blur.value(time) as f32;
            camera = match &focus.target {
                FocusTarget::Point(point) => camera.focus_on(point.at(time), blur),
                FocusTarget::Distance(distance) => {
                    camera.focus = Some(Focus {
                        distance: distance.value(time) as f32,
                        blur,
                    });
                    camera
                }
            };
        }
        Ok(camera)
    }
}
