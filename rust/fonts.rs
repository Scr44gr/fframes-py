//! Load owned font data for both public rendering APIs.

use std::{path::PathBuf, sync::Arc};

use fframes::usvgr::fontdb::{Database, Family, Query, Source};
use pyo3::{PyResult, exceptions::PyValueError};

pub(crate) fn load(paths: &[PathBuf], system: bool) -> PyResult<Database> {
    let mut fonts = Database::new();
    if system {
        fonts.load_system_fonts();
    }
    for path in paths {
        // Own bytes: subsequent source edits must not change a compiled video.
        let bytes = std::fs::read(path)?;
        if fonts
            .load_font_source(Source::Binary(Arc::new(bytes)))
            .is_empty()
        {
            return Err(PyValueError::new_err(format!(
                "invalid font file: {}",
                path.display()
            )));
        }
    }
    if fonts
        .query(&Query {
            families: &[Family::SansSerif],
            ..Default::default()
        })
        .is_none()
    {
        let family = fonts
            .faces()
            .next()
            .and_then(|face| face.families.first())
            .map(|family| family.0.clone());
        if let Some(family) = family {
            fonts.set_sans_serif_family(family);
        }
    }
    Ok(fonts)
}
