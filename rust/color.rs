//! Shared checked color conversion at native input and output boundaries.

use std::str::FromStr;

use fframes::{Color, usvgr::svgtree::svgrtypes};
use pyo3::{PyResult, exceptions::PyValueError};

pub(crate) fn parse(value: &str) -> PyResult<Color> {
    let color =
        svgrtypes::Color::from_str(value).map_err(|_| PyValueError::new_err("invalid color"))?;
    Ok(Color {
        r: color.red,
        g: color.green,
        b: color.blue,
        a: color.alpha,
    })
}

pub(crate) fn hex(color: Color) -> String {
    format!(
        "#{:02X}{:02X}{:02X}{:02X}",
        color.r, color.g, color.b, color.a
    )
}
