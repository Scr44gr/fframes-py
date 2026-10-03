//! Decode shared easing descriptions before constructing upstream runtimes.

use fframes::animation::Easing as Native;
use pyo3::{PyResult, exceptions::PyValueError};
use serde::Deserialize;

#[derive(Deserialize)]
#[serde(try_from = "Description")]
pub(crate) struct Easing(Native);

#[derive(Deserialize)]
#[serde(untagged)]
enum Description {
    Name(String),
    Curve(Curve),
}

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
enum Curve {
    Spring {
        mass: f32,
        stiffness: f32,
        damping: f32,
    },
    CubicBezier {
        x1: f32,
        y1: f32,
        x2: f32,
        y2: f32,
    },
}

impl TryFrom<Description> for Easing {
    type Error = String;

    fn try_from(value: Description) -> Result<Self, Self::Error> {
        let easing = match value {
            Description::Name(name) => match name.as_str() {
                "linear" => Native::Linear,
                "ease_in" => Native::EaseIn,
                "ease_out" => Native::EaseOut,
                "ease_in_out" => Native::EaseInOut,
                _ => return Err("unsupported easing".into()),
            },
            Description::Curve(Curve::Spring {
                mass,
                stiffness,
                damping,
            }) => {
                if [mass, stiffness, damping]
                    .iter()
                    .any(|v| !v.is_finite() || *v <= 0. || *v > 1e4)
                    || !(1e-3..=1e6).contains(&(damping / mass))
                    || !(1e-3..=1e6).contains(&(stiffness / mass))
                {
                    return Err("spring parameters exceed the supported settling range".into());
                }
                Native::Spring {
                    mass,
                    stiffness,
                    damping,
                }
            }
            Description::Curve(Curve::CubicBezier { x1, y1, x2, y2 }) => {
                if [x1, y1, x2, y2]
                    .iter()
                    .any(|v| !v.is_finite() || !(0. ..=1.).contains(v))
                {
                    return Err("Bézier control points must be in 0..1".into());
                }
                Native::CubicBezier(x1, y1, x2, y2)
            }
        };
        Ok(Self(easing))
    }
}

impl Easing {
    pub fn parse(source: &str) -> PyResult<Self> {
        if source.starts_with('{') {
            serde_json::from_str(source).map_err(|err| PyValueError::new_err(err.to_string()))
        } else {
            Self::try_from(Description::Name(source.to_owned())).map_err(PyValueError::new_err)
        }
    }

    pub fn native(&self) -> Native {
        self.0
    }

    pub fn maximum(&self) -> f64 {
        if let Native::Spring {
            mass,
            stiffness,
            damping,
        } = self.0
        {
            let zeta = f64::from(damping) / (2. * (f64::from(stiffness) * f64::from(mass)).sqrt());
            if zeta < 1. {
                return 1. + (-zeta * std::f64::consts::PI / (1. - zeta * zeta).sqrt()).exp();
            }
        }
        1.
    }
}
