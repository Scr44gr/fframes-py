use fframes::animation::{Easing, KeyFrame, KeyFramesAnimation};
use pyo3::{exceptions::PyValueError, prelude::*};

type KeyframeInput = (f32, f32, f64, f64, String);

/// Compiled scalar keyframes, reusable across frame samples.
#[pyclass(frozen, module = "fframes._native")]
pub(crate) struct Animation {
    animation: KeyFramesAnimation<f64>,
}

#[pymethods]
impl Animation {
    /// Interpolate a value at a frame index using the supplied frame rate.
    fn sample(&self, index: usize, fps: usize) -> PyResult<f64> {
        check_fps(fps)?;
        Ok(fframes::Frame::new(index, index, fps).animate(&self.animation))
    }

    /// Interpolate a batch while reusing one frame context and releasing the GIL.
    fn sample_many(&self, py: Python<'_>, indices: Vec<usize>, fps: usize) -> PyResult<Vec<f64>> {
        check_fps(fps)?;
        Ok(py.detach(|| {
            let mut frame = fframes::Frame::new(0, 0, fps);
            indices
                .into_iter()
                .map(|index| {
                    frame.index = index;
                    frame.global_index = index;
                    frame.animate(&self.animation)
                })
                .collect()
        }))
    }
}

fn check_fps(fps: usize) -> PyResult<()> {
    if fps == 0 || fps > i32::MAX as usize {
        return Err(PyValueError::new_err(
            "fps must be between 1 and 2147483647",
        ));
    }
    Ok(())
}

/// Compile ordered keyframes into an immutable native animation.
///
/// # Errors
/// Returns ValueError for empty, invalid or overlapping keyframes or unsupported easing.
#[pyfunction]
pub(crate) fn compile_animation(keyframes: Vec<KeyframeInput>) -> PyResult<Animation> {
    if keyframes.is_empty() {
        return Err(PyValueError::new_err("at least one keyframe is required"));
    }
    let mut previous_end = 0.0;
    let mut frames = Vec::with_capacity(keyframes.len());
    for (start, end, from, to, kind) in keyframes {
        if !start.is_finite()
            || !end.is_finite()
            || !from.is_finite()
            || !to.is_finite()
            || !(to - from).is_finite()
            || start < previous_end
            || end <= start
        {
            return Err(PyValueError::new_err(
                "keyframes must be finite, ordered, non-overlapping and have positive duration",
            ));
        }
        previous_end = end;
        let easing = match kind.as_str() {
            "linear" => &Easing::Linear,
            "ease_in" => &Easing::EaseIn,
            "ease_out" => &Easing::EaseOut,
            "ease_in_out" => &Easing::EaseInOut,
            _ => return Err(PyValueError::new_err("unsupported easing")),
        };
        frames.push(KeyFrame {
            start,
            end: Some(end),
            from,
            to,
            easing,
        });
    }
    Ok(Animation {
        animation: KeyFramesAnimation::new(frames),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn holds_endpoints_and_interpolates_between_them() -> PyResult<()> {
        let animation = compile_animation(vec![(1., 2., 10., 20., "linear".into())])?;
        assert_eq!(
            [
                animation.sample(0, 30)?,
                animation.sample(45, 30)?,
                animation.sample(90, 30)?
            ],
            [10., 15., 20.],
        );
        Ok(())
    }
}
