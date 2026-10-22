//! Typed SVG filter graphs compiled without XML serialization.

use super::graphics::{Images, attribute, element};
use fframes::usvgr::svgtree::{AId, Attribute, EId, NestedNodeData};
use pyo3::{PyResult, exceptions::PyValueError};
use serde::Deserialize;
use std::collections::HashSet;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Filter {
    steps: Vec<Step>,
    region: [f64; 4],
    #[serde(default)]
    units: Units,
    #[serde(default)]
    color_space: ColorSpace,
}
#[derive(Default, Deserialize)]
#[serde(rename_all = "lowercase")]
enum Units {
    #[default]
    Bounds,
    User,
}
#[derive(Default, Deserialize)]
#[serde(rename_all = "lowercase")]
enum ColorSpace {
    #[default]
    Linear,
    Srgb,
}

#[derive(Deserialize)]
struct Step {
    result: String,
    region: Option<[f64; 4]>,
    #[serde(flatten)]
    content: Content,
}
#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase")]
enum Content {
    Blur {
        source: String,
        sigma: [f64; 2],
    },
    Flood {
        color: String,
    },
    Offset {
        source: String,
        dx: f64,
        dy: f64,
    },
    Colormatrix {
        source: String,
        values: [[f64; 5]; 4],
    },
    Composite {
        source: String,
        destination: String,
        operator: Operator,
        coefficients: Option<[f64; 4]>,
    },
    Merge {
        sources: Vec<String>,
    },
    Blend {
        source: String,
        destination: String,
        mode: super::input::BlendMode,
    },
    Displacement {
        source: String,
        destination: String,
        scale: f64,
        x_channel: Channel,
        y_channel: Channel,
    },
    Morphology {
        source: String,
        operator: Morphology,
        radius: [f64; 2],
    },
    Turbulence {
        frequency: [f64; 2],
        octaves: u32,
        seed: i32,
        noise: Noise,
        stitch: bool,
    },
    Tile {
        source: String,
    },
    Convolve {
        source: String,
        order: [u32; 2],
        kernel: Vec<f64>,
        divisor: Option<f64>,
        bias: f64,
        target: Option<[u32; 2]>,
        edge: Edge,
        preserve_alpha: bool,
    },
    Transfer {
        source: String,
        red: Option<Transfer>,
        green: Option<Transfer>,
        blue: Option<Transfer>,
        alpha: Option<Transfer>,
    },
    Lighting {
        source: String,
        light: Light,
        mode: Lighting,
        color: String,
        surface_scale: f64,
        constant: f64,
        exponent: Option<f64>,
    },
    Image {
        source: crate::buffers::Source,
        fit: Fit,
    },
}
#[derive(Deserialize)]
#[serde(rename_all = "lowercase")]
enum Operator {
    Over,
    In,
    Out,
    Atop,
    Xor,
    Arithmetic,
}
#[derive(Deserialize)]
enum Channel {
    R,
    G,
    B,
    A,
}
impl Channel {
    fn svg(&self) -> &'static str {
        match self {
            Self::R => "R",
            Self::G => "G",
            Self::B => "B",
            Self::A => "A",
        }
    }
}
#[derive(Deserialize)]
#[serde(rename_all = "lowercase")]
enum Morphology {
    Erode,
    Dilate,
}
#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
enum Noise {
    FractalNoise,
    Turbulence,
}
#[derive(Deserialize)]
#[serde(rename_all = "lowercase")]
enum Edge {
    Duplicate,
    Wrap,
    None,
}
#[derive(Deserialize)]
#[serde(rename_all = "lowercase")]
enum Lighting {
    Diffuse,
    Specular,
}
#[derive(Deserialize)]
#[serde(rename_all = "lowercase")]
enum Fit {
    Contain,
    Cover,
    Stretch,
}
#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase", deny_unknown_fields)]
enum Transfer {
    Table {
        values: Vec<f64>,
    },
    Discrete {
        values: Vec<f64>,
    },
    Linear {
        slope: f64,
        intercept: f64,
    },
    Gamma {
        amplitude: f64,
        exponent: f64,
        offset: f64,
    },
}
#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase", deny_unknown_fields)]
enum Light {
    Distant {
        azimuth: f64,
        elevation: f64,
    },
    Point {
        position: [f64; 3],
    },
    Spot {
        position: [f64; 3],
        target: [f64; 3],
        exponent: f64,
        cone: Option<f64>,
    },
}
fn numbers(values: impl IntoIterator<Item = f64>) -> PyResult<String> {
    values
        .into_iter()
        .map(|v| {
            if v.is_finite() {
                Ok(v.to_string())
            } else {
                Err(PyValueError::new_err("filter values must be finite"))
            }
        })
        .collect::<PyResult<Vec<_>>>()
        .map(|s| s.join(" "))
}
fn region_attrs(region: [f64; 4]) -> PyResult<Vec<Attribute<'static>>> {
    if region.iter().any(|v| !v.is_finite()) || region[2] <= 0. || region[3] <= 0. {
        return Err(PyValueError::new_err(
            "filter region requires finite values and positive extents",
        ));
    }
    Ok([AId::X, AId::Y, AId::Width, AId::Height]
        .into_iter()
        .zip(region)
        .map(|(id, v)| attribute(id, v))
        .collect())
}
impl Transfer {
    fn node(self, tag: EId) -> PyResult<NestedNodeData<'static>> {
        let discrete = matches!(&self, Self::Discrete { .. });
        let (kind, attrs) = match self {
            Self::Table { values } | Self::Discrete { values } => {
                if values.is_empty() {
                    return Err(PyValueError::new_err("transfer table must not be empty"));
                }
                (
                    if discrete { "discrete" } else { "table" },
                    vec![attribute(AId::TableValues, numbers(values)?)],
                )
            }
            Self::Linear { slope, intercept } => (
                "linear",
                vec![
                    attribute(AId::Slope, slope),
                    attribute(AId::Intercept, intercept),
                ],
            ),
            Self::Gamma {
                amplitude,
                exponent,
                offset,
            } => {
                if !exponent.is_finite() || exponent <= 0. {
                    return Err(PyValueError::new_err("gamma exponent must be positive"));
                }
                (
                    "gamma",
                    vec![
                        attribute(AId::Amplitude, amplitude),
                        attribute(AId::Exponent, exponent),
                        attribute(AId::Offset, offset),
                    ],
                )
            }
        };
        Ok(element(
            tag,
            std::iter::once(attribute(AId::Type, kind))
                .chain(attrs)
                .collect(),
            vec![],
        ))
    }
}
impl Light {
    fn node(self) -> NestedNodeData<'static> {
        let position = |p: [f64; 3]| {
            [AId::X, AId::Y, AId::Z]
                .into_iter()
                .zip(p)
                .map(|(k, v)| attribute(k, v))
                .collect::<Vec<_>>()
        };
        let (tag, attrs) = match self {
            Self::Distant { azimuth, elevation } => (
                EId::FeDistantLight,
                vec![
                    attribute(AId::Azimuth, azimuth),
                    attribute(AId::Elevation, elevation),
                ],
            ),
            Self::Point { position: p } => (EId::FePointLight, position(p)),
            Self::Spot {
                position: p,
                target,
                exponent,
                cone,
            } => {
                let mut attrs = position(p);
                attrs.extend(
                    [AId::PointsAtX, AId::PointsAtY, AId::PointsAtZ]
                        .into_iter()
                        .zip(target)
                        .map(|(k, v)| attribute(k, v)),
                );
                attrs.push(attribute(AId::SpecularExponent, exponent));
                if let Some(cone) = cone {
                    attrs.push(attribute(AId::LimitingConeAngle, cone));
                }
                (EId::FeSpotLight, attrs)
            }
        };
        element(tag, attrs, vec![])
    }
}

pub(super) fn compile(
    filter: Filter,
    index: usize,
    images: &mut Images<'_>,
) -> PyResult<NestedNodeData<'static>> {
    region_attrs(filter.region)?;
    if filter.steps.is_empty() {
        return Err(PyValueError::new_err("filter steps must not be empty"));
    }
    let mut names = HashSet::from(["SourceGraphic".to_owned(), "SourceAlpha".to_owned()]);
    let mut steps = Vec::with_capacity(filter.steps.len());
    for step in filter.steps {
        let mut attrs = if let Some(region) = step.region {
            region_attrs(region)?
        } else {
            vec![]
        };
        let mut sources = vec![];
        let mut children = vec![];
        let mut input = |source: String, destination: Option<String>| {
            sources.push(source.clone());
            attrs.push(attribute(AId::In, source));
            if let Some(destination) = destination {
                sources.push(destination.clone());
                attrs.push(attribute(AId::In2, destination));
            }
        };
        let tag = match step.content {
            Content::Blur { source, sigma } => {
                input(source, None);
                if sigma.iter().any(|v| !v.is_finite() || *v < 0. || *v > 1e4) {
                    return Err(PyValueError::new_err("invalid blur deviation"));
                }
                attrs.push(attribute(AId::StdDeviation, numbers(sigma)?));
                EId::FeGaussianBlur
            }
            Content::Flood { color } => {
                attrs.push(attribute(AId::FloodColor, crate::color::parse(&color)?));
                EId::FeFlood
            }
            Content::Offset { source, dx, dy } => {
                input(source, None);
                numbers([dx, dy])?;
                attrs.extend([attribute(AId::Dx, dx), attribute(AId::Dy, dy)]);
                EId::FeOffset
            }
            Content::Colormatrix { source, values } => {
                input(source, None);
                attrs.extend([
                    attribute(AId::Type, "matrix"),
                    attribute(AId::Values, numbers(values.into_iter().flatten())?),
                ]);
                EId::FeColorMatrix
            }
            Content::Composite {
                source,
                destination,
                operator,
                coefficients,
            } => {
                input(source, Some(destination));
                if matches!(operator, Operator::Arithmetic) != coefficients.is_some() {
                    return Err(PyValueError::new_err(
                        "arithmetic composite requires coefficients; other operators do not",
                    ));
                }
                attrs.push(attribute(
                    AId::Operator,
                    match operator {
                        Operator::Over => "over",
                        Operator::In => "in",
                        Operator::Out => "out",
                        Operator::Atop => "atop",
                        Operator::Xor => "xor",
                        Operator::Arithmetic => "arithmetic",
                    },
                ));
                if let Some(values) = coefficients {
                    numbers(values)?;
                    attrs.extend(
                        [AId::K1, AId::K2, AId::K3, AId::K4]
                            .into_iter()
                            .zip(values)
                            .map(|(k, v)| attribute(k, v)),
                    );
                }
                EId::FeComposite
            }
            Content::Merge { sources: inputs } => {
                if inputs.is_empty() {
                    return Err(PyValueError::new_err("merge requires input sources"));
                }
                children = inputs
                    .iter()
                    .map(|v| {
                        Some(element(
                            EId::FeMergeNode,
                            vec![attribute(AId::In, v.clone())],
                            vec![],
                        ))
                    })
                    .collect();
                sources = inputs;
                EId::FeMerge
            }
            Content::Blend {
                source,
                destination,
                mode,
            } => {
                input(source, Some(destination));
                attrs.push(attribute(AId::Mode, mode.as_svg()));
                EId::FeBlend
            }
            Content::Displacement {
                source,
                destination,
                scale,
                x_channel,
                y_channel,
            } => {
                input(source, Some(destination));
                attrs.extend([
                    attribute(AId::Scale, scale),
                    attribute(AId::XChannelSelector, x_channel.svg()),
                    attribute(AId::YChannelSelector, y_channel.svg()),
                ]);
                EId::FeDisplacementMap
            }
            Content::Morphology {
                source,
                operator,
                radius,
            } => {
                input(source, None);
                if radius
                    .iter()
                    .any(|v| !v.is_finite() || *v <= 0. || *v > 1e4)
                {
                    return Err(PyValueError::new_err("morphology requires positive radii"));
                }
                attrs.extend([
                    attribute(
                        AId::Operator,
                        match operator {
                            Morphology::Erode => "erode",
                            Morphology::Dilate => "dilate",
                        },
                    ),
                    attribute(AId::Radius, numbers(radius)?),
                ]);
                EId::FeMorphology
            }
            Content::Turbulence {
                frequency,
                octaves,
                seed,
                noise,
                stitch,
            } => {
                if frequency.iter().any(|v| !v.is_finite() || *v < 0.)
                    || !(1..=16).contains(&octaves)
                {
                    return Err(PyValueError::new_err(
                        "invalid turbulence frequency or octaves",
                    ));
                }
                attrs.extend([
                    attribute(AId::BaseFrequency, numbers(frequency)?),
                    attribute(AId::NumOctaves, octaves),
                    attribute(AId::Seed, seed),
                    attribute(
                        AId::Type,
                        match noise {
                            Noise::FractalNoise => "fractalNoise",
                            Noise::Turbulence => "turbulence",
                        },
                    ),
                    attribute(AId::StitchTiles, if stitch { "stitch" } else { "noStitch" }),
                ]);
                EId::FeTurbulence
            }
            Content::Tile { source } => {
                input(source, None);
                EId::FeTile
            }
            Content::Convolve {
                source,
                order,
                kernel,
                divisor,
                bias,
                target,
                edge,
                preserve_alpha,
            } => {
                input(source, None);
                if order.contains(&0)
                    || (u64::from(order[0]) * u64::from(order[1])) != kernel.len() as u64
                    || divisor == Some(0.)
                    || target.is_some_and(|t| t[0] >= order[0] || t[1] >= order[1])
                {
                    return Err(PyValueError::new_err(
                        "invalid convolution order, kernel, divisor or target",
                    ));
                }
                attrs.extend([
                    attribute(AId::Order, format!("{} {}", order[0], order[1])),
                    attribute(AId::KernelMatrix, numbers(kernel)?),
                    attribute(AId::Bias, bias),
                    attribute(
                        AId::EdgeMode,
                        match edge {
                            Edge::Duplicate => "duplicate",
                            Edge::Wrap => "wrap",
                            Edge::None => "none",
                        },
                    ),
                    attribute(
                        AId::PreserveAlpha,
                        if preserve_alpha { "true" } else { "false" },
                    ),
                ]);
                if let Some(d) = divisor {
                    attrs.push(attribute(AId::Divisor, d));
                }
                if let Some([x, y]) = target {
                    attrs.extend([attribute(AId::TargetX, x), attribute(AId::TargetY, y)]);
                }
                EId::FeConvolveMatrix
            }
            Content::Transfer {
                source,
                red,
                green,
                blue,
                alpha,
            } => {
                input(source, None);
                for (tag, transfer) in [EId::FeFuncR, EId::FeFuncG, EId::FeFuncB, EId::FeFuncA]
                    .into_iter()
                    .zip([red, green, blue, alpha])
                {
                    if let Some(transfer) = transfer {
                        children.push(Some(transfer.node(tag)?));
                    }
                }
                EId::FeComponentTransfer
            }
            Content::Lighting {
                source,
                light,
                mode,
                color,
                surface_scale,
                constant,
                exponent,
            } => {
                input(source, None);
                if matches!(mode, Lighting::Specular) != exponent.is_some()
                    || exponent.is_some_and(|v| !(1. ..=128.).contains(&v))
                {
                    return Err(PyValueError::new_err(
                        "specular lighting requires an exponent in 1..128",
                    ));
                }
                attrs.extend([
                    attribute(AId::LightingColor, crate::color::parse(&color)?),
                    attribute(AId::SurfaceScale, surface_scale),
                ]);
                let (tag, key) = match mode {
                    Lighting::Diffuse => (EId::FeDiffuseLighting, AId::DiffuseConstant),
                    Lighting::Specular => (EId::FeSpecularLighting, AId::SpecularConstant),
                };
                attrs.push(attribute(key, constant));
                if let Some(exponent) = exponent {
                    attrs.push(attribute(AId::SpecularExponent, exponent));
                }
                children.push(Some(light.node()));
                tag
            }
            Content::Image { source, fit } => {
                // feImage resolves string references through Options.image_data;
                // unlike image elements, it does not consume ImageData attributes.
                let image = super::graphics::image(source, images)?;
                attrs.extend([
                    attribute(AId::Href, image.id.clone()),
                    attribute(
                        AId::PreserveAspectRatio,
                        match fit {
                            Fit::Contain => "xMidYMid meet",
                            Fit::Cover => "xMidYMid slice",
                            Fit::Stretch => "none",
                        },
                    ),
                ]);
                EId::FeImage
            }
        };
        if sources.iter().any(|v| !names.contains(v)) || !names.insert(step.result.clone()) {
            return Err(PyValueError::new_err(
                "filter results must be unique with prior inputs",
            ));
        }
        attrs.push(attribute(AId::Result, step.result));
        steps.push(Some(element(tag, attrs, children)));
    }
    let attrs = [AId::X, AId::Y, AId::Width, AId::Height]
        .into_iter()
        .zip(filter.region)
        .map(|(id, value)| match filter.units {
            Units::Bounds => attribute(id, format!("{}%", value * 100.)),
            Units::User => attribute(id, value),
        })
        .chain([
            attribute(AId::Id, format!("filter-{index}")),
            attribute(
                AId::FilterUnits,
                match filter.units {
                    Units::Bounds => "objectBoundingBox",
                    Units::User => "userSpaceOnUse",
                },
            ),
            attribute(
                AId::ColorInterpolationFilters,
                match filter.color_space {
                    ColorSpace::Linear => "linearRGB",
                    ColorSpace::Srgb => "sRGB",
                },
            ),
        ])
        .collect();
    Ok(element(
        EId::Defs,
        vec![],
        vec![Some(element(EId::Filter, attrs, steps))],
    ))
}
