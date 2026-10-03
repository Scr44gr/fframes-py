//! Python bindings for native fframes interpolation and CPU SVG rendering.

mod animation;
mod encoder;
mod video;

use pyo3::prelude::*;

#[pymodule]
fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<animation::Animation>()?;
    module.add_class::<video::SvgVideo>()?;
    module.add_function(wrap_pyfunction!(animation::compile_animation, module)?)?;
    module.add_function(wrap_pyfunction!(video::compile_video, module)?)?;
    Ok(())
}
