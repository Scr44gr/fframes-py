//! Python bindings for native fframes interpolation and CPU SVG rendering.

mod animation;
mod backend;
mod color;
mod compose;
mod easing;
mod encoder;
mod fonts;
mod render;
mod shader;
mod values;
mod video;

use pyo3::prelude::*;

#[pymodule]
fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<animation::Animation>()?;
    module.add_class::<animation::ColorAnimation>()?;
    module.add_class::<video::SvgVideo>()?;
    module.add_class::<compose::SceneVideo>()?;
    module.add_function(wrap_pyfunction!(animation::compile_animation, module)?)?;
    module.add_function(wrap_pyfunction!(
        animation::compile_color_animation,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(video::compile_video, module)?)?;
    module.add_function(wrap_pyfunction!(compose::compile_scene, module)?)?;
    Ok(())
}
