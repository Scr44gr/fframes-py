use std::{
    ffi::{CStr, CString},
    path::Path,
    ptr,
};

use fframes::{EncoderInput, VideoEncoderInfo, ffmpeg_sys_fframes as ffi};
use pyo3::{exceptions::PyRuntimeError, prelude::*};

#[derive(serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct AudioOptions {
    pub encoder: String,
    pub bitrate: i64,
    pub sample_rate: usize,
    pub sample_format: String,
    pub codec_params: Vec<(String, String)>,
}

impl AudioOptions {
    pub fn native<'a>(
        &'a self,
        params: &'a [(&'a str, &'a str)],
    ) -> PyResult<fframes::EncoderOptions<'a>> {
        let name =
            CString::new(self.sample_format.as_str()).map_err(crate::render::render_error)?;
        #[expect(
            unsafe_code,
            reason = "FFmpeg exposes sample format lookup through a C string"
        )]
        // SAFETY: name is a valid NUL-terminated string that outlives this read-only lookup.
        let format = unsafe { ffi::av_get_sample_fmt(name.as_ptr()) };
        if format == ffi::AVSampleFormat::AV_SAMPLE_FMT_NONE
            || self.sample_rate == 0
            || self.sample_rate > i32::MAX as usize
            || self.bitrate <= 0
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "invalid audio sample_format, sample_rate or bitrate",
            ));
        }
        let codec_name =
            CString::new(self.encoder.as_str()).map_err(crate::render::render_error)?;
        #[expect(
            unsafe_code,
            reason = "FFmpeg exposes supported audio formats and rates through C descriptors"
        )]
        // SAFETY: the static codec descriptor is checked before use. Each config
        // returns a counted immutable array of the documented element type.
        unsafe {
            let codec = ffi::avcodec_find_encoder_by_name(codec_name.as_ptr());
            if codec.is_null() || (*codec).type_ != ffi::AVMediaType::AVMEDIA_TYPE_AUDIO {
                return Err(PyRuntimeError::new_err(
                    "audio encoder is unavailable or has the wrong media type",
                ));
            }
            let mut values = ptr::null();
            let mut count = 0;
            let status = ffi::avcodec_get_supported_config(
                ptr::null(),
                codec,
                ffi::AVCodecConfig::AV_CODEC_CONFIG_SAMPLE_FORMAT,
                0,
                &raw mut values,
                &raw mut count,
            );
            if status < 0 {
                return Err(PyRuntimeError::new_err("cannot query audio sample formats"));
            }
            if !values.is_null()
                && count > 0
                && !std::slice::from_raw_parts(values.cast::<ffi::AVSampleFormat>(), count as usize)
                    .contains(&format)
            {
                return Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "audio encoder {:?} does not support sample_format {:?}",
                    self.encoder, self.sample_format
                )));
            }
            values = ptr::null();
            count = 0;
            let status = ffi::avcodec_get_supported_config(
                ptr::null(),
                codec,
                ffi::AVCodecConfig::AV_CODEC_CONFIG_SAMPLE_RATE,
                0,
                &raw mut values,
                &raw mut count,
            );
            if status < 0 {
                return Err(PyRuntimeError::new_err("cannot query audio sample rates"));
            }
            if !values.is_null()
                && count > 0
                && !std::slice::from_raw_parts(values.cast::<i32>(), count as usize)
                    .contains(&(self.sample_rate as i32))
            {
                return Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "audio encoder {:?} does not support sample_rate {}",
                    self.encoder, self.sample_rate
                )));
            }
        }
        Ok(fframes::EncoderOptions {
            preferred_encoder: Some(&self.encoder),
            bitrate: Some(self.bitrate),
            sample_rate: self.sample_rate,
            sample_format: format,
            codec_params: Some(params),
            ..Default::default()
        })
    }
}

pub(crate) fn pixel_format(name: &str) -> PyResult<ffi::AVPixelFormat> {
    let name = CString::new(name).map_err(crate::render::render_error)?;
    #[expect(
        unsafe_code,
        reason = "FFmpeg exposes pixel format lookup through a C string"
    )]
    // SAFETY: name is a valid NUL-terminated string that outlives this read-only lookup.
    let format = unsafe { ffi::av_get_pix_fmt(name.as_ptr()) };
    if format == ffi::AVPixelFormat::AV_PIX_FMT_NONE {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "unknown pixel_format",
        ));
    }
    Ok(format)
}

pub(crate) fn color_matrix(value: &str) -> PyResult<fframes::YuvMatrix> {
    match value {
        "bt601" => Ok(fframes::YuvMatrix::Bt601),
        "bt709" => Ok(fframes::YuvMatrix::Bt709),
        _ => Err(pyo3::exceptions::PyValueError::new_err(
            "color_matrix must be 'bt601' or 'bt709'",
        )),
    }
}

pub(crate) fn validate_parameters(
    name: &str,
    params: &[(&str, &str)],
    audio: bool,
    path: &Path,
) -> PyResult<()> {
    let codec_name = CString::new(name).map_err(crate::render::render_error)?;
    let filename =
        CString::new(path.to_string_lossy().as_bytes()).map_err(crate::render::render_error)?;
    #[expect(
        unsafe_code,
        reason = "FFmpeg's encoder registry and AVOption validation have C-only APIs"
    )]
    // SAFETY: strings outlive all lookups. Registry pointers are immutable and checked;
    // the private, unopened codec context is freed on every success/error path.
    unsafe {
        let codec = ffi::avcodec_find_encoder_by_name(codec_name.as_ptr());
        if codec.is_null() {
            return Err(PyRuntimeError::new_err(format!(
                "encoder {name:?} is not available in this FFmpeg build; use fframes.available_encoders() to inspect the linked library"
            )));
        }
        let expected = if audio {
            ffi::AVMediaType::AVMEDIA_TYPE_AUDIO
        } else {
            ffi::AVMediaType::AVMEDIA_TYPE_VIDEO
        };
        if (*codec).type_ != expected {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "encoder has the wrong media type",
            ));
        }
        let format = ffi::av_guess_format(ptr::null(), filename.as_ptr(), ptr::null());
        if format.is_null()
            || ffi::avformat_query_codec(format, (*codec).id, ffi::FF_COMPLIANCE_NORMAL) == 0
        {
            return Err(PyRuntimeError::new_err(
                "encoder is incompatible with the output container",
            ));
        }
        let mut context = ffi::avcodec_alloc_context3(codec);
        if context.is_null() {
            return Err(PyRuntimeError::new_err(
                "cannot allocate encoder options context",
            ));
        }
        let result = (|| {
            for &(key, value) in params {
                if [
                    "pix_fmt",
                    "pixel_format",
                    "video_size",
                    "width",
                    "height",
                    "s",
                    "r",
                    "framerate",
                    "sample_rate",
                    "sample_fmt",
                    "request_sample_fmt",
                    "ar",
                    "ac",
                    "ch_layout",
                    "channel_layout",
                    "channels",
                    "time_base",
                ]
                .contains(&key)
                {
                    return Err(pyo3::exceptions::PyValueError::new_err(format!(
                        "codec_params[{key:?}] changes stream layout; use the typed rendering fields"
                    )));
                }
                let key_c = CString::new(key).map_err(crate::render::render_error)?;
                let value_c = CString::new(value).map_err(crate::render::render_error)?;
                let result = ffi::av_opt_set(
                    context.cast(),
                    key_c.as_ptr(),
                    value_c.as_ptr(),
                    ffi::AV_OPT_SEARCH_CHILDREN,
                );
                if result < 0 {
                    return Err(pyo3::exceptions::PyValueError::new_err(format!(
                        "invalid codec_params[{key:?}]={value:?} for encoder {name:?}"
                    )));
                }
            }
            Ok(())
        })();
        ffi::avcodec_free_context(&raw mut context);
        result
    }
}

/// List video encoders registered in the linked FFmpeg library.
///
/// Hardware encoders may still require a compatible device and driver.
#[pyfunction]
#[pyo3(signature = (audio=false))]
pub(crate) fn available_encoders(audio: bool) -> Vec<String> {
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
                && (*codec).type_
                    == if audio {
                        ffi::AVMediaType::AVMEDIA_TYPE_AUDIO
                    } else {
                        ffi::AVMediaType::AVMEDIA_TYPE_VIDEO
                    }
            {
                encoders.push(CStr::from_ptr((*codec).name).to_string_lossy().into_owned());
            }
        }
    }
    encoders.sort_unstable();
    encoders
}

/// Check container compatibility and codec initialization before opening output files.
pub(crate) fn check_output(
    path: &Path,
    info: &VideoEncoderInfo<'_>,
    requested: Option<ffi::AVPixelFormat>,
) -> PyResult<EncoderInput> {
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
    // Hardware encoders such as QSV require semiplanar NV12 instead of planar
    // YUV420P. Both carry 8-bit 4:2:0 pixels; do not fall back to RGB or 10-bit.
    let input = if let Some(format) = requested {
        if !info.supports(format) {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "pixel_format is not supported by the selected encoder",
            ));
        }
        EncoderInput::software(format)
    } else if info.supports(ffi::AVPixelFormat::AV_PIX_FMT_YUV420P) {
        EncoderInput::software(ffi::AVPixelFormat::AV_PIX_FMT_YUV420P)
    } else if info.supports(ffi::AVPixelFormat::AV_PIX_FMT_NV12) {
        EncoderInput::software(ffi::AVPixelFormat::AV_PIX_FMT_NV12)
    } else {
        return Err(PyRuntimeError::new_err(format!(
            "encoder {:?} accepts neither YUV420P nor NV12; 8-bit 4:2:0 input is required",
            info.name()
        )));
    };
    let input = input.with_color_matrix(info.options.color_matrix);
    info.try_open(&input)
        .map_err(|error| PyRuntimeError::new_err(error.to_string()))?;
    Ok(input)
}
