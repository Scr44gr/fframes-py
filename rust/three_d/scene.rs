//! Compile node hierarchies once, then pose cheap scene clones in Rust.

use super::{
    environment, geometry, light, material,
    values::{Color, ColorInput, Vector, scalar},
};
use crate::{
    render::{FrameCache, render_error},
    values::{Scalar, Value},
};
use fframes::three_d::{self as d, Mat4, NodeId, Object, Quat};
use pyo3::{PyResult, exceptions::PyValueError};
use serde::Deserialize;
use std::{
    collections::HashMap,
    path::PathBuf,
    sync::{Arc, Mutex},
};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Input {
    nodes: Vec<Node>,
    background: Option<environment::BackgroundInput>,
    environment: Option<environment::Input>,
    fog: Option<environment::FogInput>,
    reflector: Option<environment::ReflectorInput>,
    #[serde(default)]
    animations: Vec<super::animation::Input>,
}

#[derive(Deserialize)]
#[serde(untagged)]
pub(super) enum SequenceInput {
    Single(Box<Input>),
    Frames { frames: Vec<Input>, fps: usize },
}

pub(super) struct Sequence {
    frames: Vec<Program>,
    fps: usize,
}

impl SequenceInput {
    pub fn compile(self, fps: usize, buffers: &crate::buffers::Buffers) -> PyResult<Sequence> {
        let (inputs, sample_fps) = match self {
            Self::Single(scene) => (vec![*scene], 1),
            Self::Frames { frames, fps } => (frames, fps),
        };
        if inputs.is_empty() || sample_fps == 0 {
            return Err(PyValueError::new_err(
                "SceneFrames requires nonempty frames and positive fps",
            ));
        }
        let mut geometry = HashMap::new();
        let mut models = HashMap::new();
        let frames = inputs
            .into_iter()
            .map(|input| input.compile(fps, buffers, &mut geometry, &mut models))
            .collect::<PyResult<_>>()?;
        Ok(Sequence {
            frames,
            fps: sample_fps,
        })
    }
}

impl Sequence {
    pub fn get(&self, time: f64) -> &Program {
        let index = (time.max(0.) * self.fps as f64 + 1e-9).floor() as usize;
        &self.frames[index.min(self.frames.len() - 1)]
    }
    pub fn gpu_limits(&self) -> PyResult<Option<String>> {
        for scene in &self.frames {
            if let Some(message) = scene.gpu_limits()? {
                return Ok(Some(message));
            }
        }
        Ok(None)
    }
    pub fn at(
        &self,
        time: f64,
        cache: &mut FrameCache,
        rasterizer: &crate::backend::Rasterizer<'_>,
    ) -> PyResult<d::Scene> {
        self.get(time).at(time, cache, rasterizer)
    }
    pub fn pose(&self, time: f64) -> PyResult<d::Scene> {
        self.get(time).pose(time)
    }
    pub fn node(&self, name: &str, time: f64) -> PyResult<NodeId> {
        self.get(time).node(name)
    }
}

#[derive(Deserialize)]
struct Transform {
    name: Option<String>,
    position: [Scalar; 3],
    rotation: [Scalar; 3],
    quaternion: Option<[f32; 4]>,
    scale: [Scalar; 3],
    visible: Visibility,
}

#[derive(Deserialize)]
#[serde(untagged)]
enum Visibility {
    Constant(bool),
    Frames { values: Vec<bool>, fps: usize },
}

impl Visibility {
    fn at(&self, time: f64) -> bool {
        match self {
            Self::Constant(value) => *value,
            Self::Frames { values, fps } => {
                let index = (time.max(0.) * *fps as f64 + 1e-9).floor() as usize;
                values[index.min(values.len() - 1)]
            }
        }
    }
}

#[derive(Deserialize)]
struct Node {
    #[serde(flatten)]
    transform: Transform,
    #[serde(flatten)]
    content: Content,
}

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase")]
enum Content {
    Group {
        children: Vec<Node>,
    },
    Mesh {
        geometry: geometry::Input,
        material: Box<material::Input>,
        cast_shadow: bool,
        receive_shadow: bool,
        skin: Option<Skin>,
        morph_weights: Vec<Scalar>,
        instances: Option<Instances>,
        children: Vec<Node>,
    },
    Light {
        light: light::Input,
    },
    Particles {
        items: Vec<Particle>,
        blending: material::Blend,
    },
    Model {
        source: PathBuf,
        animations: Vec<Playback>,
        poses: Vec<Transform>,
        #[serde(default)]
        materials: Vec<MaterialOverride>,
        children: Vec<Node>,
    },
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct MaterialOverride {
    node: String,
    material: material::Input,
}

#[derive(Deserialize)]
struct Skin {
    joints: Vec<String>,
    inverse_bind_matrices: Vec<[f32; 16]>,
}

#[derive(Deserialize)]
struct Instances {
    transforms: Vec<[f32; 16]>,
    colors: Vec<ColorInput>,
}

#[derive(Deserialize)]
struct Particle {
    position: [Scalar; 3],
    size: Scalar,
    color: ColorInput,
    opacity: Scalar,
}

#[derive(Deserialize)]
pub(super) struct Playback {
    pub name: String,
    time: Option<Scalar>,
    speed: Scalar,
    offset: Scalar,
    weight: Scalar,
    r#loop: bool,
}

struct Pose {
    node: NodeId,
    position: Vector,
    rotation: Vector,
    quaternion: Option<Quat>,
    scale: Vector,
    visible: Visibility,
}
struct ParticleProgram {
    position: Vector,
    size: Value,
    color: Color,
    opacity: Value,
}
struct Motion {
    clip: d::AnimationClip,
    offset: u32,
    time: Option<Value>,
    speed: Value,
    start: Value,
    weight: Value,
    looping: bool,
}

enum Appearance {
    Material(NodeId, Box<material::Program>, Option<Vec<Value>>),
    Light(NodeId, Box<light::Program>),
    Particles(NodeId, Vec<ParticleProgram>, d::Blending),
    InstanceColors(NodeId, Vec<Color>),
}

impl Playback {
    fn compile(self, clip: d::AnimationClip, offset: u32) -> PyResult<Motion> {
        Ok(Motion {
            clip,
            offset,
            time: self.time.map(|v| scalar(v, -1e7, 1e7)).transpose()?,
            speed: scalar(self.speed, -1e7, 1e7)?,
            start: scalar(self.offset, -1e7, 1e7)?,
            weight: scalar(self.weight, 0., 1.)?,
            looping: self.r#loop,
        })
    }
}

pub(super) struct Program {
    base: d::Scene,
    poses: Vec<Pose>,
    overrides: Vec<Pose>,
    appearances: Vec<Appearance>,
    motions: Vec<Motion>,
    background: environment::BackgroundProgram,
    environment: environment::Program,
    fog: Option<environment::FogProgram>,
    names: HashMap<String, NodeId>,
}

struct Builder<'a> {
    buffers: &'a crate::buffers::Buffers,
    program: Program,
    geometry: &'a mut geometry::Cache,
    models: &'a mut HashMap<PathBuf, Arc<d::Model>>,
    skins: Vec<(NodeId, Skin)>,
    fps: usize,
}

impl Transform {
    fn compile(self, node: NodeId) -> PyResult<Pose> {
        if let Visibility::Frames { values, fps } = &self.visible
            && (values.is_empty() || *fps == 0)
        {
            return Err(PyValueError::new_err(
                "visibility requires nonempty samples and positive fps",
            ));
        }
        for value in &self.scale {
            value.check(-1e7, 1e7)?;
        }
        let quaternion = self.quaternion.map(Quat::from_array);
        if quaternion.is_some_and(|q| !q.is_finite() || q.length_squared() < 1e-12) {
            return Err(PyValueError::new_err(
                "quaternion must be finite and nonzero",
            ));
        }
        Ok(Pose {
            node,
            position: Vector::compile(self.position)?,
            rotation: Vector::compile(self.rotation)?,
            quaternion: quaternion.map(Quat::normalize),
            scale: Vector::compile(self.scale)?,
            visible: self.visible,
        })
    }
}

impl Pose {
    fn apply(&self, scene: &mut d::Scene, time: f64) {
        let node = &mut scene[self.node];
        node.position = self.position.at(time);
        let r = self.rotation.at(time);
        node.rotation = self.quaternion.unwrap_or_else(|| d::euler(r.x, r.y, r.z));
        node.scale = self.scale.at(time);
        node.visible = self.visible.at(time);
    }
}

impl Input {
    pub fn compile(
        self,
        fps: usize,
        buffers: &crate::buffers::Buffers,
        geometry: &mut geometry::Cache,
        models: &mut HashMap<PathBuf, Arc<d::Model>>,
    ) -> PyResult<Program> {
        let mut base = d::Scene::new();
        base.reflector = self.reflector.map(environment::ReflectorInput::compile);
        let mut builder = Builder {
            buffers,
            program: Program {
                base,
                poses: Vec::new(),
                overrides: Vec::new(),
                appearances: Vec::new(),
                motions: Vec::new(),
                background: self
                    .background
                    .map(environment::BackgroundInput::compile)
                    .transpose()?
                    .unwrap_or(environment::BackgroundProgram::Transparent),
                environment: self
                    .environment
                    .map(environment::Input::compile)
                    .transpose()?
                    .unwrap_or(environment::Program::None),
                fog: self.fog.map(environment::FogInput::compile).transpose()?,
                names: HashMap::new(),
            },
            geometry,
            models,
            skins: Vec::new(),
            fps,
        };
        for node in self.nodes {
            builder.add(node, None)?;
        }
        for (id, skin) in builder.skins {
            let joints = skin
                .joints
                .iter()
                .map(|name| {
                    builder.program.names.get(name).copied().ok_or_else(|| {
                        PyValueError::new_err(format!(
                            "skin joint {name:?} does not exist; name its node explicitly"
                        ))
                    })
                })
                .collect::<PyResult<Vec<_>>>()?;
            if joints.len() != skin.inverse_bind_matrices.len() {
                return Err(PyValueError::new_err("skin matrices must match its joints"));
            }
            if let Some(mesh) = builder.program.base[id].mesh_mut() {
                if let Some(weights) = &mesh.geometry.skin {
                    if weights
                        .joints
                        .iter()
                        .flatten()
                        .any(|&j| j as usize >= joints.len())
                    {
                        return Err(PyValueError::new_err(
                            "skin weight references a missing joint",
                        ));
                    }
                } else {
                    return Err(PyValueError::new_err(
                        "a skinned mesh needs geometry.skin weights",
                    ));
                }
                mesh.skin = Some(d::Skin {
                    joints,
                    inverse_bind_matrices: Arc::new(
                        skin.inverse_bind_matrices
                            .iter()
                            .map(Mat4::from_cols_array)
                            .collect(),
                    ),
                });
            }
        }
        for animation in self.animations {
            let (clip, playback) = animation.compile(&builder.program.names)?;
            for channel in &clip.channels {
                if let d::Keyframes::Weights { targets, .. } = &channel.keyframes {
                    let Object::Mesh(mesh) = &builder.program.base[channel.node].object else {
                        return Err(PyValueError::new_err(
                            "morph animation requires a mesh node",
                        ));
                    };
                    if *targets != mesh.geometry.morph_targets.len() || mesh.instances.is_some() {
                        return Err(PyValueError::new_err(
                            "morph animation target count must match geometry, and instanced meshes cannot morph",
                        ));
                    }
                }
            }
            builder.program.motions.push(playback.compile(clip, 0)?);
        }
        Ok(builder.program)
    }
}

impl Builder<'_> {
    fn add(&mut self, input: Node, parent: Option<NodeId>) -> PyResult<()> {
        let name = input.transform.name.clone();
        let id = match parent {
            Some(p) => self.program.base.add_to(p, d::Node::group()),
            None => self.program.base.add(d::Node::group()),
        };
        if let Some(name) = name.as_ref() {
            if self.program.names.insert(name.clone(), id).is_some() {
                return Err(PyValueError::new_err(format!(
                    "duplicate 3D node name {name:?}; names must be unique in a scene"
                )));
            }
            self.program.base[id].name = Some(name.as_str().into());
        }
        self.program.poses.push(input.transform.compile(id)?);
        let children = match input.content {
            Content::Group { children } => children,
            Content::Mesh {
                geometry,
                material,
                cast_shadow,
                receive_shadow,
                skin,
                morph_weights,
                instances,
                children,
            } => {
                let geometry = geometry.compile(self.geometry)?;
                if geometry.skin.is_some() && skin.is_none() {
                    return Err(PyValueError::new_err(
                        "geometry.skin supplies vertex weights; add Mesh(skin=Skin(...)) to bind its joints",
                    ));
                }
                let mut mesh_node = d::Node::mesh(geometry, d::Material::default())
                    .shadows(cast_shadow, receive_shadow);
                if let Some(mesh) = mesh_node.mesh_mut() {
                    if !morph_weights.is_empty()
                        && morph_weights.len() != mesh.geometry.morph_targets.len()
                    {
                        return Err(PyValueError::new_err(
                            "morph_weights must match geometry.morph_targets",
                        ));
                    }
                    mesh.instances = instances.map(|instances| {
                        let programs = instances.colors.into_iter().map(ColorInput::compile).collect::<PyResult<Vec<_>>>()?;
                        let colors = programs.iter().map(|c| c.at(0.)).collect();
                        if programs.iter().any(Color::animated) {
                            self.program.appearances.push(Appearance::InstanceColors(id, programs));
                        }
                        let transforms = instances.transforms.iter().map(Mat4::from_cols_array).collect::<Vec<_>>();
                        if transforms.iter().any(|m| !m.is_finite() || m.determinant() <= 0.) { return Err(PyValueError::new_err("instance matrices must be finite, invertible and must not mirror")); }
                        Ok::<_, pyo3::PyErr>(Arc::new(d::Instances { transforms, colors }))
                    }).transpose()?;
                }
                self.program.base[id].object = mesh_node.object;
                if let Some(skin) = skin {
                    self.skins.push((id, skin));
                }
                self.program.appearances.push(Appearance::Material(
                    id,
                    Box::new(material.compile(self.fps, self.buffers)?),
                    Some(
                        morph_weights
                            .into_iter()
                            .map(|v| scalar(v, -1e7, 1e7))
                            .collect::<PyResult<_>>()?,
                    ),
                ));
                children
            }
            Content::Light { light } => {
                self.program
                    .appearances
                    .push(Appearance::Light(id, Box::new(light.compile()?)));
                Vec::new()
            }
            Content::Particles { items, blending } => {
                let items = items
                    .into_iter()
                    .map(|p| {
                        Ok(ParticleProgram {
                            position: Vector::compile(p.position)?,
                            size: scalar(p.size, f64::MIN_POSITIVE, 1e7)?,
                            color: p.color.compile()?,
                            opacity: scalar(p.opacity, 0., 1.)?,
                        })
                    })
                    .collect::<PyResult<_>>()?;
                self.program
                    .appearances
                    .push(Appearance::Particles(id, items, blending.native()));
                Vec::new()
            }
            Content::Model {
                source,
                animations,
                poses,
                materials,
                children,
            } => {
                let source = source.canonicalize()?;
                if !self.models.contains_key(&source) {
                    self.models
                        .insert(source.clone(), Arc::new(load_model(&source)?));
                }
                let model = &self.models[&source];
                let offset = self.program.base.append(Some(id), &model.scene);
                for (node, data) in model.scene.nodes() {
                    if let (Some(prefix), Some(local)) = (name.as_ref(), data.name.as_ref()) {
                        let qualified = format!("{prefix}/{local}");
                        if self
                            .program
                            .names
                            .insert(qualified.clone(), NodeId(node.0 + offset))
                            .is_some()
                        {
                            return Err(PyValueError::new_err(format!(
                                "ambiguous model node {qualified:?}"
                            )));
                        }
                    }
                }
                for playback in animations {
                    let clip = model
                        .animation(&playback.name)
                        .ok_or_else(|| {
                            PyValueError::new_err(format!(
                                "model has no animation {:?}",
                                playback.name
                            ))
                        })?
                        .clone();
                    self.program.motions.push(playback.compile(clip, offset)?);
                }
                for pose in poses {
                    let name = pose
                        .name
                        .as_deref()
                        .ok_or_else(|| PyValueError::new_err("model pose requires a node name"))?;
                    let node = model.scene.find(name).ok_or_else(|| {
                        PyValueError::new_err(format!("model has no node {name:?}"))
                    })?;
                    self.program
                        .overrides
                        .push(pose.compile(NodeId(node.0 + offset))?);
                }
                let mut targets = std::collections::HashSet::new();
                for replacement in materials {
                    let matching: Vec<_> = model
                        .scene
                        .nodes()
                        .filter(|(_, node)| node.name.as_deref() == Some(&replacement.node))
                        .collect();
                    if matching.len() != 1 || !targets.insert(replacement.node.clone()) {
                        return Err(PyValueError::new_err(format!(
                            "material override requires a unique model mesh node {:?}",
                            replacement.node
                        )));
                    }
                    let (node, data) = matching[0];
                    if data.as_mesh().is_none() {
                        return Err(PyValueError::new_err(format!(
                            "material override node {:?} is not a mesh",
                            replacement.node
                        )));
                    }
                    self.program.appearances.push(Appearance::Material(
                        NodeId(node.0 + offset),
                        Box::new(replacement.material.compile(self.fps, self.buffers)?),
                        None,
                    ));
                }
                children
            }
        };
        for child in children {
            self.add(child, Some(id))?;
        }
        Ok(())
    }
}

pub(super) fn load_model(path: &std::path::Path) -> PyResult<d::Model> {
    let directory = path
        .parent()
        .ok_or_else(|| PyValueError::new_err("model path has no parent directory"))?;
    let missing = Mutex::new(Vec::new());
    let model = d::Model::from_gltf_with(&std::fs::read(path)?, |uri| {
        let bytes = directory
            .join(uri)
            .canonicalize()
            .ok()
            .filter(|p| p.starts_with(directory))
            .and_then(|p| std::fs::read(p).ok());
        if bytes.is_none() {
            missing
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .push(uri.to_owned());
        }
        bytes
    })
    .map_err(render_error)?;
    let missing = missing
        .into_inner()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    if !missing.is_empty() {
        return Err(PyValueError::new_err(format!(
            "glTF resources are missing or outside its directory: {}",
            missing.join(", ")
        )));
    }
    Ok(model)
}

impl Program {
    pub fn gpu_limits(&self) -> PyResult<Option<String>> {
        let mut direct = 0;
        let mut shadows = 0;
        let mut count = |light: &d::Light| match light {
            d::Light::Directional(light) => {
                direct += 1;
                shadows += usize::from(light.shadow.is_some());
            }
            d::Light::Point(_) | d::Light::Spot(_) => direct += 1,
            _ => {}
        };
        for (_, node) in self.base.nodes() {
            if let Object::Light(light) = &node.object {
                count(light);
            }
        }
        for appearance in &self.appearances {
            if let Appearance::Light(_, light) = appearance {
                count(&light.at(0.)?);
            }
        }
        let softboxes = match self.environment.at(0.) {
            d::Environment::Studio(s) => s.softboxes.len(),
            _ => 0,
        };
        Ok((direct > 16 || shadows > 2 || softboxes > 8).then(|| format!("3D GPU limits exceeded: {direct}/16 direct lights, {shadows}/2 shadow lights, {softboxes}/8 softboxes; use device='cpu' or 'auto'")))
    }

    pub fn at(
        &self,
        time: f64,
        cache: &mut FrameCache,
        rasterizer: &crate::backend::Rasterizer<'_>,
    ) -> PyResult<d::Scene> {
        let mut scene = self.pose(time)?;
        scene.background = self.background.at(time);
        scene.environment = self.environment.at(time);
        scene.fog = self.fog.as_ref().map(|f| f.at(time));
        for appearance in &self.appearances {
            match appearance {
                Appearance::InstanceColors(id, colors) => {
                    if let Some(mesh) = scene[*id].mesh_mut()
                        && let Some(instances) = &mut mesh.instances
                    {
                        Arc::make_mut(instances).colors =
                            colors.iter().map(|c| c.at(time)).collect();
                    }
                }
                Appearance::Material(id, material, _) => {
                    if let Some(mesh) = scene[*id].mesh_mut() {
                        mesh.material = material.at(time, cache, rasterizer)?;
                    }
                }
                Appearance::Light(id, light) => scene[*id].object = Object::Light(light.at(time)?),
                Appearance::Particles(id, particles, blending) => {
                    scene[*id].object = Object::Particles(d::Particles {
                        items: particles
                            .iter()
                            .map(|p| {
                                d::Particle::new(
                                    p.position.at(time),
                                    p.size.value(time) as f32,
                                    p.color.at(time),
                                )
                                .opacity(p.opacity.value(time) as f32)
                            })
                            .collect(),
                        blending: *blending,
                    })
                }
            }
        }
        Ok(scene)
    }

    pub fn pose(&self, time: f64) -> PyResult<d::Scene> {
        let mut scene = self.base.clone();
        for pose in &self.poses {
            pose.apply(&mut scene, time);
        }
        for appearance in &self.appearances {
            if let Appearance::Material(id, _, Some(weights)) = appearance
                && let Some(mesh) = scene[*id].mesh_mut()
            {
                mesh.morph_weights = weights.iter().map(|w| w.value(time) as f32).collect();
            }
        }
        for motion in &self.motions {
            let t = motion.time.as_ref().map_or_else(
                || time * motion.speed.value(time) + motion.start.value(time),
                |t| t.value(time),
            ) as f32;
            let weight = motion.weight.value(time) as f32;
            if motion.looping {
                motion
                    .clip
                    .apply_looped(&mut scene, motion.offset, t, weight);
            } else {
                motion.clip.apply(&mut scene, motion.offset, t, weight);
            }
        }
        for pose in &self.overrides {
            pose.apply(&mut scene, time);
        }
        if scene
            .nodes()
            .any(|(_, n)| !n.scale.is_finite() || n.scale.abs().min_element() == 0.)
        {
            return Err(PyValueError::new_err(format!(
                "animated scale must remain nonzero at time {time}; check keyframes and spline tangents"
            )));
        }
        Ok(scene)
    }

    pub fn node(&self, name: &str) -> PyResult<NodeId> {
        self.names
            .get(name)
            .copied()
            .ok_or_else(|| PyValueError::new_err(format!("no 3D node named {name:?}")))
    }
}
