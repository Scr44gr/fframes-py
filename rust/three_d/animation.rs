//! Named transform and morph channels using the engine's glTF interpolator.

use fframes::three_d::{AnimationClip, Channel, Interpolation, Keyframes, NodeId, Quat, Vec3};
use pyo3::{PyResult, exceptions::PyValueError};
use serde::Deserialize;
use std::collections::HashMap;

#[derive(Deserialize)]
pub(super) struct Input {
    #[serde(flatten)]
    pub playback: super::scene::Playback,
    duration: f32,
    channels: Vec<ChannelInput>,
}

#[derive(Deserialize)]
struct ChannelInput {
    node: String,
    times: Vec<f32>,
    interpolation: Mode,
    #[serde(flatten)]
    keyframes: Frames,
}

#[derive(Deserialize, Clone, Copy)]
#[serde(rename_all = "snake_case")]
enum Mode {
    Step,
    Linear,
    CubicSpline,
}

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase")]
enum Frames {
    Translation { values: Vec<[f32; 3]> },
    Scale { values: Vec<[f32; 3]> },
    Rotation { values: Vec<[f32; 4]> },
    Weights { values: Vec<Vec<f32>> },
}

impl Input {
    pub fn compile(
        self,
        names: &HashMap<String, NodeId>,
    ) -> PyResult<(AnimationClip, super::scene::Playback)> {
        let channels = self
            .channels
            .into_iter()
            .map(|c| {
                let node = *names.get(&c.node).ok_or_else(|| {
                    PyValueError::new_err(format!(
                        "animation channel references missing node {:?}",
                        c.node
                    ))
                })?;
                let interpolation = match c.interpolation {
                    Mode::Step => Interpolation::Step,
                    Mode::Linear => Interpolation::Linear,
                    Mode::CubicSpline => Interpolation::CubicSpline,
                };
                let keyframes = match c.keyframes {
                    Frames::Translation { values } => {
                        Keyframes::Translation(values.into_iter().map(Vec3::from).collect())
                    }
                    Frames::Scale { values } => {
                        Keyframes::Scale(values.into_iter().map(Vec3::from).collect())
                    }
                    Frames::Rotation { values } => Keyframes::Rotation(
                        values
                            .into_iter()
                            .enumerate()
                            .map(|(i, q)| {
                                let q = Quat::from_array(q);
                                if matches!(c.interpolation, Mode::CubicSpline) && i % 3 != 1 {
                                    q
                                } else {
                                    q.normalize()
                                }
                            })
                            .collect(),
                    ),
                    Frames::Weights { values } => Keyframes::Weights {
                        targets: values.first().map_or(0, Vec::len),
                        values: values.into_iter().flatten().collect(),
                    },
                };
                Ok(Channel {
                    node,
                    interpolation,
                    times: c.times,
                    keyframes,
                })
            })
            .collect::<PyResult<_>>()?;
        Ok((
            AnimationClip {
                name: self.playback.name.clone(),
                duration: self.duration,
                channels,
            },
            self.playback,
        ))
    }
}
