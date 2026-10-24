//! Python bindings for native fframes interpolation and CPU SVG rendering.

// wgpu's device graph is nested inside the Send/Sync-checked PyO3 scene types.
#![recursion_limit = "256"]

mod analysis;
mod animation;
mod audio;
mod backend;
mod buffers;
mod clips;
mod color;
mod compose;
mod easing;
mod effects;
mod encoder;
mod fonts;
mod images;
mod inspection;
mod lottie;
mod progress;
mod render;
mod shader;
mod spectrum;
mod subtitles;
mod text;
mod three_d;
mod timing;
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
    module.add_class::<three_d::Renderer3D>()?;
    module.add_class::<progress::RenderControl>()?;
    module.add_class::<timing::TimelineIndex>()?;
    module.add_function(wrap_pyfunction!(timing::inspect_timeline, module)?)?;
    module.add_function(wrap_pyfunction!(analysis::analyze_audio, module)?)?;
    module.add_function(wrap_pyfunction!(three_d::compile_3d, module)?)?;
    module.add_function(wrap_pyfunction!(three_d::assets::model_info, module)?)?;
    module.add_function(wrap_pyfunction!(three_d::assets::text_shapes, module)?)?;
    module.add_function(wrap_pyfunction!(lottie::lottie_info, module)?)?;
    module.add_function(wrap_pyfunction!(inspection::inspect_video, module)?)?;
    module.add_function(wrap_pyfunction!(inspection::preview_video, module)?)?;
    module.add_function(wrap_pyfunction!(inspection::sheet_video, module)?)?;
    module.add_function(wrap_pyfunction!(inspection::detect_pops, module)?)?;
    module.add_function(wrap_pyfunction!(spectrum::decode_audio, module)?)?;
    module.add_function(wrap_pyfunction!(encoder::available_encoders, module)?)?;
    module.add_function(wrap_pyfunction!(subtitles::parse_subtitles, module)?)?;
    module.add_function(wrap_pyfunction!(clips::video_info, module)?)?;
    module.add_function(wrap_pyfunction!(images::image_info, module)?)?;
    module.add_function(wrap_pyfunction!(text::compile_text_layout, module)?)?;
    module.add_function(wrap_pyfunction!(animation::compile_animation, module)?)?;
    module.add_function(wrap_pyfunction!(
        animation::compile_color_animation,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(video::compile_video, module)?)?;
    module.add_function(wrap_pyfunction!(compose::compile_scene, module)?)?;
    module.add_function(wrap_pyfunction!(compose::paths::validate_path, module)?)?;
    Ok(())
}
