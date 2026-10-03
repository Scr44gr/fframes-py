use std::fmt::Debug;

use fframes::{
    Color,
    animation::{Animatable, KeyFrame, KeyFramesAnimation},
};
use pyo3::{exceptions::PyValueError, prelude::*};

type KeyframeInput<T = f64> = (f32, f32, T, T, String);

/// Compiled scalar keyframes, reusable across frame samples.
#[pyclass(frozen, module = "fframes._native")]
pub(crate) struct Animation {
    animation: KeyFramesAnimation<f64>,
}

#[pymethods]
impl Animation {
    /// Interpolate a value at a frame index using the supplied frame rate.
    fn sample(&self, index: usize, fps: usize) -> PyResult<f64> {
        sample(&self.animation, index, fps)
    }

    /// Interpolate a batch while reusing one frame context and releasing the GIL.
    fn sample_many(&self, py: Python<'_>, indices: Vec<usize>, fps: usize) -> PyResult<Vec<f64>> {
        check_fps(fps)?;
        Ok(py.detach(|| samples(&self.animation, indices, fps, std::convert::identity)))
    }
}

/// Compiled color keyframes using the original RGBA interpolation arithmetic.
#[pyclass(frozen, module = "fframes._native")]
pub(crate) struct ColorAnimation {
    animation: KeyFramesAnimation<Color>,
}

#[pymethods]
impl ColorAnimation {
    fn sample(&self, index: usize, fps: usize) -> PyResult<String> {
        sample(&self.animation, index, fps).map(crate::color::hex)
    }

    fn sample_many(
        &self,
        py: Python<'_>,
        indices: Vec<usize>,
        fps: usize,
    ) -> PyResult<Vec<String>> {
        check_fps(fps)?;
        Ok(py.detach(|| samples(&self.animation, indices, fps, crate::color::hex)))
    }
}

fn sample<T: Animatable + Default + Debug>(
    animation: &KeyFramesAnimation<T>,
    index: usize,
    fps: usize,
) -> PyResult<T> {
    check_fps(fps)?;
    Ok(fframes::Frame::new(index, index, fps).animate(animation))
}

fn samples<T: Animatable + Default + Debug, U>(
    animation: &KeyFramesAnimation<T>,
    indices: Vec<usize>,
    fps: usize,
    convert: impl Fn(T) -> U,
) -> Vec<U> {
    let mut frame = fframes::Frame::new(0, 0, fps);
    indices
        .into_iter()
        .map(|index| {
            frame.index = index;
            frame.global_index = index;
            convert(frame.animate(animation))
        })
        .collect()
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
    Ok(Animation {
        animation: compile(keyframes, |a, b| {
            a.is_finite() && b.is_finite() && (b - a).is_finite()
        })?,
    })
}

/// Compile validated string colors into reusable upstream RGBA keyframes.
#[pyfunction]
pub(crate) fn compile_color_animation(
    keyframes: Vec<KeyframeInput<String>>,
) -> PyResult<ColorAnimation> {
    let keyframes = keyframes
        .into_iter()
        .map(|(start, end, from, to, easing)| {
            Ok((
                start,
                end,
                crate::color::parse(&from)?,
                crate::color::parse(&to)?,
                easing,
            ))
        })
        .collect::<PyResult<Vec<_>>>()?;
    Ok(ColorAnimation {
        animation: compile(keyframes, |_, _| true)?,
    })
}

fn compile<T: Animatable + Default>(
    keyframes: Vec<KeyframeInput<T>>,
    valid: impl Fn(T, T) -> bool,
) -> PyResult<KeyFramesAnimation<T>> {
    if keyframes.is_empty() {
        return Err(PyValueError::new_err("at least one keyframe is required"));
    }
    let mut previous_end = 0.0;
    let easings = keyframes
        .iter()
        .map(|k| crate::easing::Easing::parse(&k.4).map(|e| e.native()))
        .collect::<PyResult<Vec<_>>>()?;
    let mut frames = Vec::with_capacity(keyframes.len());
    for ((start, end, from, to, _), easing) in keyframes.into_iter().zip(&easings) {
        if !start.is_finite()
            || !end.is_finite()
            || !valid(from, to)
            || start < previous_end
            || end <= start
        {
            return Err(PyValueError::new_err(
                "keyframes must be finite, ordered, non-overlapping and have positive duration",
            ));
        }
        previous_end = end;
        frames.push(KeyFrame {
            start,
            end: Some(end),
            from,
            to,
            easing,
        });
    }
    Ok(KeyFramesAnimation::new(frames))
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
