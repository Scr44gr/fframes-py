//! Compile bounded text formatting once; evaluate without Python callbacks.

use pyo3::{PyResult, exceptions::PyValueError};

enum Part {
    Literal(String),
    Frame,
    Seconds(usize),
}

pub(super) struct Template(Vec<Part>);

impl Template {
    pub fn compile(source: &str) -> PyResult<Self> {
        let mut parts = Vec::new();
        let mut literal = String::new();
        let mut chars = source.chars().peekable();
        while let Some(ch) = chars.next() {
            if ch != '{' && ch != '}' {
                literal.push(ch);
            } else if chars.peek() == Some(&ch) {
                literal.push(ch);
                chars.next();
            } else if ch == '{' {
                if !literal.is_empty() {
                    parts.push(Part::Literal(std::mem::take(&mut literal)));
                }
                let mut field = String::new();
                loop {
                    match chars.next() {
                        Some('}') => break,
                        Some(ch) => field.push(ch),
                        None => return Err(PyValueError::new_err("unclosed text template field")),
                    }
                }
                if field == "frame" {
                    parts.push(Part::Frame);
                } else if let Some(spec) = field.strip_prefix("seconds:.") {
                    let bytes = spec.as_bytes();
                    if bytes.len() != 2 || !bytes[0].is_ascii_digit() || bytes[1] != b'f' {
                        return Err(PyValueError::new_err("invalid seconds precision"));
                    }
                    parts.push(Part::Seconds(usize::from(bytes[0] - b'0')));
                } else {
                    return Err(PyValueError::new_err("unsupported text template field"));
                }
            } else {
                return Err(PyValueError::new_err("unmatched text template brace"));
            }
        }
        if !literal.is_empty() {
            parts.push(Part::Literal(literal));
        }
        Ok(Self(parts))
    }

    pub fn render(&self, frame: usize, seconds: f64) -> String {
        let mut output = String::new();
        for part in &self.0 {
            match part {
                Part::Literal(text) => output.push_str(text),
                Part::Frame => output.push_str(&frame.to_string()),
                Part::Seconds(precision) => output.push_str(&format!("{seconds:.precision$}")),
            }
        }
        output
    }
}
