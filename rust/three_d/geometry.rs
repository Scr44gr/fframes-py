//! Build immutable geometry once and intern identical recipes within a scene.

use std::{collections::HashMap, path::PathBuf, sync::Arc};

use fframes::three_d::{Geometry, Mat4, MorphTarget, Shape, SkinWeights, Vec2, Vec3, Vec4};
use pyo3::{PyResult, exceptions::PyValueError};
use serde::{Deserialize, Serialize};

#[derive(Deserialize, Serialize)]
pub(super) struct Input {
    pub transform: [f32; 16],
    normals: Normals,
    crease: f32,
    #[serde(flatten)]
    shape: Primitive,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
enum Normals {
    Original,
    Flat,
    Smooth,
}

#[derive(Deserialize, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
enum Primitive {
    Box {
        size: [f32; 3],
        radius: f32,
        segments: u32,
    },
    Sphere {
        radius: f32,
        segments: [u32; 2],
        theta: [f32; 2],
    },
    Cylinder {
        top: f32,
        bottom: f32,
        height: f32,
        segments: u32,
        open: bool,
    },
    Capsule {
        radius: f32,
        length: f32,
        cap_segments: u32,
        radial_segments: u32,
    },
    Torus {
        radius: f32,
        tube: f32,
        segments: [u32; 2],
        arc: f32,
    },
    Plane {
        size: [f32; 2],
        axis: PlaneAxis,
        segments: [u32; 2],
    },
    Ring {
        inner: f32,
        outer: f32,
        segments: u32,
    },
    Lathe {
        points: Vec<[f32; 2]>,
        segments: u32,
    },
    Extrude {
        shape: Polygon,
        depth: f32,
        bevel: f32,
        bevel_segments: u32,
    },
    Text {
        text: String,
        font: PathBuf,
        height: f32,
        depth: f32,
        bevel: f32,
    },
    Icosahedron {
        radius: f32,
        detail: u32,
    },
    Tube {
        path: Vec<[f32; 3]>,
        radius: f32,
        segments: u32,
    },
    Mesh {
        positions: Vec<[f32; 3]>,
        indices: Vec<u32>,
        vertex_normals: Vec<[f32; 3]>,
        uvs: Vec<[f32; 2]>,
        colors: Vec<[f32; 4]>,
        skin: Option<Weights>,
        morph_targets: Vec<Morph>,
    },
    Stl {
        source: PathBuf,
    },
    Merged {
        parts: Vec<Input>,
    },
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
enum PlaneAxis {
    Xy,
    Xz,
}

#[derive(Deserialize, Serialize)]
struct Polygon {
    outer: Vec<[f32; 2]>,
    holes: Vec<Vec<[f32; 2]>>,
}

#[derive(Deserialize, Serialize)]
struct Weights {
    joints: Vec<[u16; 4]>,
    weights: Vec<[f32; 4]>,
}

#[derive(Deserialize, Serialize)]
struct Morph {
    name: Option<String>,
    positions: Vec<[f32; 3]>,
    normals: Vec<[f32; 3]>,
}

pub(super) type Cache = HashMap<String, Arc<Geometry>>;

impl Input {
    pub fn compile(self, cache: &mut Cache) -> PyResult<Arc<Geometry>> {
        let key = serde_json::to_string(&self).map_err(crate::render::render_error)?;
        if let Some(geometry) = cache.get(&key) {
            return Ok(Arc::clone(geometry));
        }
        let geometry = Arc::new(self.build()?);
        cache.insert(key, Arc::clone(&geometry));
        Ok(geometry)
    }

    fn build(self) -> PyResult<Geometry> {
        let geometry = match self.shape {
            Primitive::Box {
                size: [w, h, d],
                radius,
                segments,
            } => {
                if radius == 0. {
                    Geometry::cuboid(w, h, d)
                } else {
                    Geometry::rounded_box(w, h, d, radius, segments)
                }
            }
            Primitive::Sphere {
                radius,
                segments: [w, h],
                theta: [start, length],
            } => Geometry::sphere_partial(radius, w, h, start, length),
            Primitive::Cylinder {
                top,
                bottom,
                height,
                segments,
                open,
            } => {
                if open {
                    Geometry::cylinder_open(top, bottom, height, segments)
                } else {
                    Geometry::cylinder(top, bottom, height, segments)
                }
            }
            Primitive::Capsule {
                radius,
                length,
                cap_segments,
                radial_segments,
            } => Geometry::capsule(radius, length, cap_segments, radial_segments),
            Primitive::Torus {
                radius,
                tube,
                segments: [radial, tubular],
                arc,
            } => Geometry::torus_arc(radius, tube, radial, tubular, arc),
            Primitive::Plane {
                size: [w, h],
                axis,
                segments: [x, y],
            } => {
                let mut plane = Geometry::floor_segments(w, h, x, y);
                match axis {
                    PlaneAxis::Xz => plane,
                    PlaneAxis::Xy => {
                        // Upstream floor UVs repeat per world unit. XY screens use the
                        // normalized, top-left convention of Geometry::plane instead.
                        for uv in &mut plane.uvs {
                            *uv = *uv / Vec2::new(w, h) + Vec2::splat(0.5);
                        }
                        plane.rotate_x(std::f32::consts::FRAC_PI_2)
                    }
                }
            }
            Primitive::Ring {
                inner,
                outer,
                segments,
            } => Geometry::ring(inner, outer, segments),
            Primitive::Lathe { points, segments } => Geometry::lathe(
                &points.into_iter().map(Vec2::from).collect::<Vec<_>>(),
                segments,
            ),
            Primitive::Extrude {
                shape,
                depth,
                bevel,
                bevel_segments,
            } => Geometry::extrude_shape(
                &Shape {
                    outer: shape.outer.into_iter().map(Vec2::from).collect(),
                    holes: shape
                        .holes
                        .into_iter()
                        .map(|h| h.into_iter().map(Vec2::from).collect())
                        .collect(),
                },
                depth,
                bevel,
                bevel_segments,
            ),
            Primitive::Text {
                text,
                font,
                height,
                depth,
                bevel,
            } => Geometry::text(&std::fs::read(font)?, &text, height, depth, bevel)
                .map_err(crate::render::render_error)?,
            Primitive::Icosahedron { radius, detail } => {
                if detail > 6 {
                    return Err(PyValueError::new_err("icosahedron detail must be <= 6"));
                }
                Geometry::icosahedron(radius, detail)
            }
            Primitive::Tube {
                path,
                radius,
                segments,
            } => Geometry::tube(
                &path.into_iter().map(Vec3::from).collect::<Vec<_>>(),
                radius,
                segments,
            ),
            Primitive::Mesh {
                positions,
                indices,
                vertex_normals,
                uvs,
                colors,
                skin,
                morph_targets,
            } => {
                let count = positions.len();
                if !indices.len().is_multiple_of(3) || indices.iter().any(|&i| i as usize >= count)
                {
                    return Err(PyValueError::new_err(
                        "indices must reference complete triangles",
                    ));
                }
                let mut geometry = Geometry::new(
                    positions.into_iter().map(Vec3::from).collect(),
                    vertex_normals.into_iter().map(Vec3::from).collect(),
                    uvs.into_iter().map(Vec2::from).collect(),
                    indices,
                );
                if !colors.is_empty() {
                    geometry.colors = colors.into_iter().map(Vec4::from).collect();
                }
                geometry.skin = skin.map(|s| SkinWeights {
                    joints: s.joints,
                    weights: s.weights,
                });
                geometry.morph_targets = morph_targets
                    .into_iter()
                    .map(|m| MorphTarget {
                        name: m.name,
                        positions: m.positions.into_iter().map(Vec3::from).collect(),
                        normals: m.normals.into_iter().map(Vec3::from).collect(),
                    })
                    .collect();
                geometry
            }
            Primitive::Stl { source } => {
                Geometry::from_stl(&std::fs::read(source)?).map_err(crate::render::render_error)?
            }
            Primitive::Merged { parts } => Geometry::merge(
                parts
                    .into_iter()
                    .map(Input::build)
                    .collect::<PyResult<Vec<_>>>()?,
            ),
        };
        let geometry = geometry.transform(Mat4::from_cols_array(&self.transform));
        Ok(match self.normals {
            Normals::Original => geometry,
            Normals::Flat => geometry.flat(),
            Normals::Smooth => geometry.smooth(self.crease),
        })
    }
}
