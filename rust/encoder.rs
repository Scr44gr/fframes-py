use std::{ffi::CString, path::Path, ptr};

use fframes::{EncoderInput, VideoEncoderInfo, ffmpeg_sys_fframes as ffi};
use pyo3::{exceptions::PyRuntimeError, prelude::*};

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
