//! Compile typed filter graphs to the same primitives used by upstream SVGs.

use std::collections::HashSet;

use fframes::usvgr::svgtree::{AId, EId, NestedNodeData};
use pyo3::{PyResult, exceptions::PyValueError};
use serde::Deserialize;

use super::graphics::{attribute, element};

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
#[serde(tag = "kind", rename_all = "lowercase", deny_unknown_fields)]
enum Step {
    Blur {
        result: String,
        source: String,
        sigma: [f64; 2],
    },
    Flood {
        result: String,
        color: String,
    },
    Composite {
        result: String,
        source: String,
        destination: String,
        operator: Operator,
    },
    Merge {
        result: String,
        sources: Vec<String>,
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
}

pub(super) fn compile(filter: Filter, index: usize) -> PyResult<NestedNodeData<'static>> {
    if filter.steps.is_empty()
        || filter.region.iter().any(|v| !v.is_finite())
        || filter.region[2] <= 0.
        || filter.region[3] <= 0.
    {
        return Err(PyValueError::new_err(
            "invalid filter region or empty steps",
        ));
    }
    let mut names = HashSet::from(["SourceAlpha".to_owned(), "SourceGraphic".to_owned()]);
    let mut steps = Vec::with_capacity(filter.steps.len());
    for step in filter.steps {
        let (tag, result, sources, mut attrs, children) = match step {
            Step::Blur {
                result,
                source,
                sigma,
            } => {
                if sigma.iter().any(|v| !v.is_finite() || *v < 0. || *v > 1e4) {
                    return Err(PyValueError::new_err("invalid blur deviation"));
                }
                (
                    EId::FeGaussianBlur,
                    result,
                    vec![source.clone()],
                    vec![
                        attribute(AId::In, source),
                        attribute(AId::StdDeviation, format!("{} {}", sigma[0], sigma[1])),
                    ],
                    vec![],
                )
            }
            Step::Flood { result, color } => {
                let color = crate::color::parse(&color)?;
                (
                    EId::FeFlood,
                    result,
                    vec![],
                    vec![attribute(AId::FloodColor, color)],
                    vec![],
                )
            }
            Step::Composite {
                result,
                source,
                destination,
                operator,
            } => {
                let operator = match operator {
                    Operator::Over => "over",
                    Operator::In => "in",
                    Operator::Out => "out",
                    Operator::Atop => "atop",
                    Operator::Xor => "xor",
                };
                (
                    EId::FeComposite,
                    result,
                    vec![source.clone(), destination.clone()],
                    vec![
                        attribute(AId::In, source),
                        attribute(AId::In2, destination),
                        attribute(AId::Operator, operator),
                    ],
                    vec![],
                )
            }
            Step::Merge { result, sources } => {
                if sources.is_empty() {
                    return Err(PyValueError::new_err("merge requires input sources"));
                }
                let children = sources
                    .iter()
                    .map(|source| {
                        Some(element(
                            EId::FeMergeNode,
                            vec![attribute(AId::In, source.clone())],
                            vec![],
                        ))
                    })
                    .collect();
                (EId::FeMerge, result, sources, vec![], children)
            }
        };
        if sources.iter().any(|source| !names.contains(source)) || !names.insert(result.clone()) {
            return Err(PyValueError::new_err(
                "filter results must be unique with prior inputs",
            ));
        }
        attrs.push(attribute(AId::Result, result));
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
