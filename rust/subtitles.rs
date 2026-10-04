//! Parse WebVTT natively without upstream's hour-timestamp and multiline bugs.

use pyo3::{exceptions::PyValueError, prelude::*};
use serde::Serialize;
use subtp::vtt::{VttBlock, VttComment, VttDescription, WebVtt};

#[derive(Serialize)]
struct Cue {
    start: f64,
    end: f64,
    text: String,
    name: Option<String>,
    settings: Option<Settings>,
}

#[derive(Serialize)]
struct Settings {
    vertical: Option<String>,
    line: Option<String>,
    position: Option<f32>,
    position_align: Option<String>,
    size: Option<f32>,
    align: Option<String>,
    region: Option<String>,
}

#[derive(Default, Serialize)]
struct Subtitles {
    description: Option<String>,
    styles: Vec<String>,
    regions: Vec<String>,
    notes: Vec<String>,
    cues: Vec<Cue>,
}

#[pyfunction]
pub(crate) fn parse_subtitles(py: Python<'_>, text: &str) -> PyResult<String> {
    py.detach(|| {
        let vtt = WebVtt::parse(text).map_err(|e| PyValueError::new_err(e.to_string()))?;
        let mut subtitles = Subtitles {
            description: vtt.header.description.map(|d| match d {
                VttDescription::Side(text) | VttDescription::Below(text) => text,
            }),
            ..Default::default()
        };
        for block in vtt.blocks {
            match block {
                VttBlock::Que(cue) => {
                    let start: std::time::Duration = cue.timings.start.into();
                    let end: std::time::Duration = cue.timings.end.into();
                    subtitles.cues.push(Cue {
                        start: start.as_secs_f64(),
                        end: end.as_secs_f64(),
                        text: cue.payload.join("\n"),
                        name: cue.identifier,
                        settings: cue.settings.map(|value| Settings {
                            vertical: value.vertical.map(|v| v.to_string()),
                            line: value.line.map(|v| v.to_string()),
                            position: value.position.as_ref().map(|v| v.value.value),
                            position_align: value
                                .position
                                .and_then(|v| v.alignment)
                                .map(|v| v.to_string()),
                            size: value.size.map(|v| v.value),
                            align: value.align.map(|v| v.to_string()),
                            region: value.region,
                        }),
                    });
                }
                VttBlock::Comment(VttComment::Side(note) | VttComment::Below(note)) => {
                    subtitles.notes.push(note)
                }
                VttBlock::Style(style) => subtitles.styles.push(style.style),
                VttBlock::Region(region) => subtitles.regions.push(region.to_string()),
            }
        }
        serde_json::to_string(&subtitles).map_err(|e| PyValueError::new_err(e.to_string()))
    })
}
