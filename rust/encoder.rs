use std::{
    ffi::{CStr, CString},
    path::Path,
    ptr,
};

use fframes::{EncoderInput, VideoEncoderInfo, ffmpeg_sys_fframes as ffi};
use pyo3::{exceptions::PyRuntimeError, prelude::*};

/// List video encoders registered in the linked FFmpeg library.
///
/// Hardware encoders may still require a compatible device and driver.
#[pyfunction]
pub(crate) fn available_encoders() -> Vec<String> {
    let mut encoders = Vec::new();
    let mut state = ptr::null_mut();
    #[expect(
        unsafe_code,
        reason = "FFmpeg exposes its codec registry through C pointers"
    )]
    // SAFETY: the iterator state is private to this call. Descriptors and their
    // NUL-terminated names are immutable static data owned by FFmpeg. Each pointer
    // is checked before dereferencing; no borrowed data escapes this call.
    unsafe {
        loop {
            let codec = ffi::av_codec_iterate(&mut state);
            if codec.is_null() {
                break;
            }
            if ffi::av_codec_is_encoder(codec) != 0
                && (*codec).type_ == ffi::AVMediaType::AVMEDIA_TYPE_VIDEO
            {
                encoders.push(CStr::from_ptr((*codec).name).to_string_lossy().into_owned());
            }
        }
    }
    encoders.sort_unstable();
    encoders
}

/// Check container compatibility and codec initialization before opening output files.
pub(crate) fn check_output(path: &Path, info: &VideoEncoderInfo<'_>) -> PyResult<()> {
    let filename = CString::new(path.to_string_lossy().as_bytes())
        .map_err(|error| PyRuntimeError::new_err(error.to_string()))?;
    #[expect(
        unsafe_code,
        reason = "fframes exposes no safe container compatibility query"
    )]
    // SAFETY: filename remains alive for both lookups. FFmpeg returns a static format
    // pointer, checked before use; VideoEncoderInfo owns a valid static codec pointer.
    // These queries borrow both descriptors and neither free nor modify them.
    let supported = unsafe {
        let format = ffi::av_guess_format(ptr::null(), filename.as_ptr(), ptr::null());
        !format.is_null()
            && ffi::avformat_query_codec(format, (*info.as_ptr()).id, ffi::FF_COMPLIANCE_NORMAL)
                == 1
    };
    if !supported {
        return Err(PyRuntimeError::new_err(
            "encoder is incompatible with the output container",
        ));
    }
    // Probe before upstream opens any segment files: failing to open a codec during
    // Encoder construction can leak its AVIOContext on error in fframes 1.2.0.
    let input = EncoderInput::requested(info)
        .map_err(|error| PyRuntimeError::new_err(error.to_string()))?;
    info.try_open(&input)
        .map_err(|error| PyRuntimeError::new_err(error.to_string()))
}
