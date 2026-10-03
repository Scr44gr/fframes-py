//! Adapt an owned font database to upstream's text layout API.

use std::{path::PathBuf, sync::Arc};

use fframes::{
    BreakLinesOpts, FFramesContext, FFramesMode, FontFace, FontQuery, FontSource, FontStretch,
    FontStyle, Frame, TextOverflow, TimeBase, VideoSize,
    usvgr::fontdb::{self, Database, Family, Query, Source, Weight},
};
use pyo3::{exceptions::PyValueError, prelude::*};
use serde::Deserialize;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    fonts: Vec<PathBuf>,
    load_system_fonts: bool,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Font {
    family: String,
    size: usize,
    weight: u16,
    style: String,
}

impl Font {
    fn parse(source: &str) -> PyResult<Self> {
        let font: Self =
            serde_json::from_str(source).map_err(|err| PyValueError::new_err(err.to_string()))?;
        if font.family.is_empty()
            || font.size == 0
            || font.size > 100000
            || !(100..=900).contains(&font.weight)
            || !matches!(font.style.as_str(), "normal" | "italic" | "oblique")
        {
            return Err(PyValueError::new_err("invalid font query"));
        }
        Ok(font)
    }

    fn query(&self) -> FontQuery<'_> {
        FontQuery {
            family: &self.family,
            size: self.size,
            weight: self.weight,
            style: match self.style.as_str() {
                "italic" => FontStyle::Italic,
                "oblique" => FontStyle::Oblique,
                _ => FontStyle::Normal,
            },
            ..Default::default()
        }
    }
}

#[derive(Debug)]
struct Face<'a>(fframes::ttf_parser::Face<'a>);

impl<'a> FontFace<'a> for Face<'a> {
    fn is_monospaced(&self) -> Option<bool> {
        Some(self.0.is_monospaced())
    }

    fn resolve_char_width(&self, size: usize, ch: char) -> Option<usize> {
        let advance = self.0.glyph_hor_advance(self.0.glyph_index(ch)?)?;
        Some(size * usize::from(advance) / usize::from(self.0.units_per_em()))
    }
}

/// Immutable font storage and native text operations.
#[pyclass(frozen, module = "fframes._native")]
#[derive(Debug)]
pub(crate) struct TextLayout {
    fonts: Database,
}

impl<'a> FontSource<'a> for TextLayout {
    fn add_font(&mut self, _filename: String, data: Arc<dyn AsRef<[u8]> + Sync + Send>) {
        self.fonts.load_font_source(Source::Binary(data));
    }

    fn resolve_font(
        &'a self,
        name: &str,
        weight: u16,
        style: FontStyle,
        _stretch: FontStretch,
    ) -> Option<Box<dyn FontFace<'a> + 'a>> {
        let id = self.fonts.query(&Query {
            families: &[Family::Name(name)],
            weight: Weight(weight),
            style: match style {
                FontStyle::Normal => fontdb::Style::Normal,
                FontStyle::Italic => fontdb::Style::Italic,
                FontStyle::Oblique => fontdb::Style::Oblique,
            },
            ..Default::default()
        })?;
        let info = self.fonts.face(id)?;
        let data = match &info.source {
            Source::Binary(data) | Source::SharedFile(_, data) => data.as_ref().as_ref(),
            Source::File(_) => return None,
        };
        let face = fframes::ttf_parser::Face::parse(data, info.index).ok()?;
        Some(Box::new(Face(face)))
    }
}

impl TextLayout {
    fn context(&self) -> FFramesContext<'_, '_> {
        FFramesContext {
            time_base: TimeBase {
                fps: 1,
                sample_rate: 48000,
            },
            current_video_size: VideoSize {
                width: 1,
                height: 1,
            },
            duration_in_frames: 1,
            mode: FFramesMode::Renderer,
            scenes: None,
            media_source: None,
            font_source: Some(self),
            abort_signal: None,
        }
    }
}

fn missing_font() -> PyErr {
    PyValueError::new_err("font family could not be resolved")
}

#[pymethods]
impl TextLayout {
    fn widths(&self, py: Python<'_>, texts: Vec<String>, font: &str) -> PyResult<Vec<usize>> {
        let font = Font::parse(font)?;
        py.detach(|| {
            let ctx = self.context();
            let mut frame = Frame::new(0, 0, 1);
            texts
                .iter()
                .map(|text| {
                    frame
                        .text_width(&ctx, font.query(), text)
                        .ok_or_else(missing_font)
                })
                .collect()
        })
    }

    fn fit(
        &self,
        py: Python<'_>,
        text: &str,
        font: &str,
        width: usize,
        marker: &str,
    ) -> PyResult<String> {
        let font = Font::parse(font)?;
        py.detach(|| {
            Frame::new(0, 0, 1)
                .text_fit(
                    &self.context(),
                    font.query(),
                    text,
                    width,
                    TextOverflow::Marker(marker),
                )
                .map(|text| text.into_owned())
                .ok_or_else(missing_font)
        })
    }

    fn wrap(&self, py: Python<'_>, text: &str, font: &str, width: usize) -> PyResult<Vec<String>> {
        let font = Font::parse(font)?;
        py.detach(|| {
            let lines = Frame::new(0, 0, 1)
                .text_break_lines_structure(
                    &self.context(),
                    text,
                    BreakLinesOpts::<i32, i32> {
                        font: font.query(),
                        width,
                        ..Default::default()
                    },
                )
                .ok_or_else(missing_font)?;
            Ok(lines
                .lines
                .into_iter()
                .map(|line| line.words.join(" "))
                .collect())
        })
    }
}

#[pyfunction]
pub(crate) fn compile_text_layout(py: Python<'_>, config: &str) -> PyResult<TextLayout> {
    let input: Input =
        serde_json::from_str(config).map_err(|err| PyValueError::new_err(err.to_string()))?;
    py.detach(|| {
        let loaded = crate::fonts::load(&input.fonts, input.load_system_fonts)?;
        // Own system fonts too: no mmap or changed files during detached work.
        let mut fonts = Database::new();
        let mut seen = std::collections::HashSet::new();
        for face in loaded.faces() {
            match &face.source {
                Source::File(path) => {
                    if seen.insert(path) {
                        fonts.load_font_data(std::fs::read(path)?);
                    }
                }
                source => {
                    fonts.load_font_source(source.clone());
                }
            }
        }
        Ok(TextLayout { fonts })
    })
}
