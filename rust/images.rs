//! Image metadata using the same decoder as rendering, with optional container EXIF.

use std::{io::Cursor, path::PathBuf};

use pyo3::prelude::*;
use serde::Serialize;

#[derive(Serialize)]
struct Field {
    ifd: u16,
    tag: String,
    value: String,
}

#[derive(Serialize)]
struct Info {
    width: u32,
    height: u32,
    exif: Vec<Field>,
}

#[pyfunction]
pub(crate) fn image_info(py: Python<'_>, source: PathBuf) -> PyResult<String> {
    py.detach(|| {
        let bytes = std::fs::read(&source)?;
        let image = fframes::media::decode_image(&source.to_string_lossy(), &bytes)
            .map_err(crate::render::media_error)?;
        let exif = fframes::exif::Reader::new()
            .read_from_container(&mut Cursor::new(&bytes))
            .ok();
        let fields = exif.as_ref().map_or_else(Vec::new, |data| {
            data.fields()
                .map(|field| Field {
                    ifd: field.ifd_num.0,
                    tag: field.tag.to_string(),
                    value: field.display_value().with_unit(data).to_string(),
                })
                .collect()
        });
        serde_json::to_string(&Info {
            width: image.width,
            height: image.height,
            exif: fields,
        })
        .map_err(crate::render::render_error)
    })
}
