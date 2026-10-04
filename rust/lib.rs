//! Python bindings for native fframes interpolation and CPU SVG rendering.

mod animation;
mod audio;
mod backend;
mod clips;
mod color;
mod compose;
mod easing;
mod encoder;
mod fonts;
mod render;
mod shader;
mod spectrum;
mod subtitles;
mod text;
mod values;
mod video;

use pyo3::prelude::*;

#[pymodule]
fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<animation::Animation>()?;
    module.add_class::<animation::ColorAnimation>()?;
    module.add_class::<video::SvgVideo>()?;
    module.add_class::<compose::SceneVideo>()?;
    module.add_class::<text::TextLayout>()?;
    module.add_class::<spectrum::AudioAnalysis>()?;
    module.add_function(wrap_pyfunction!(spectrum::decode_audio, module)?)?;
    module.add_function(wrap_pyfunction!(subtitles::parse_subtitles, module)?)?;
    module.add_function(wrap_pyfunction!(clips::video_info, module)?)?;
    module.add_function(wrap_pyfunction!(text::compile_text_layout, module)?)?;
    module.add_function(wrap_pyfunction!(animation::compile_animation, module)?)?;
    module.add_function(wrap_pyfunction!(
        animation::compile_color_animation,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(video::compile_video, module)?)?;
    module.add_function(wrap_pyfunction!(compose::compile_scene, module)?)?;
    Ok(())
}
