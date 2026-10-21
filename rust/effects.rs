//! Convert validated effect descriptions without introducing another DSP implementation.

use serde::Deserialize;

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub(crate) enum Effect {
    NormalizeLufs {
        lufs: f32,
    },
    Highpass {
        hz: f32,
        q: f32,
    },
    Lowpass {
        hz: f32,
        q: f32,
    },
    LowShelf {
        hz: f32,
        db: f32,
    },
    HighShelf {
        hz: f32,
        db: f32,
    },
    Peak {
        hz: f32,
        db: f32,
        q: f32,
    },
    Compressor {
        threshold_db: f32,
        ratio: f32,
        attack: f32,
        release: f32,
        knee_db: f32,
        makeup_db: f32,
    },
    Width {
        width: f32,
    },
}

impl Effect {
    pub fn native(self) -> fframes::Effect {
        match self {
            Self::NormalizeLufs { lufs } => fframes::Effect::NormalizeLufs { lufs },
            Self::Highpass { hz, q } => fframes::Effect::Highpass { hz, q },
            Self::Lowpass { hz, q } => fframes::Effect::Lowpass { hz, q },
            Self::LowShelf { hz, db } => fframes::Effect::LowShelf { hz, db },
            Self::HighShelf { hz, db } => fframes::Effect::HighShelf { hz, db },
            Self::Peak { hz, db, q } => fframes::Effect::Peak { hz, db, q },
            Self::Width { width } => fframes::Effect::Width { width },
            Self::Compressor {
                threshold_db,
                ratio,
                attack,
                release,
                knee_db,
                makeup_db,
            } => fframes::Effect::Compress(fframes::Compressor {
                threshold_db,
                ratio,
                attack,
                release,
                knee_db,
                makeup_db,
            }),
        }
    }
}

#[derive(Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub(crate) enum FadeCurve {
    Linear,
    #[default]
    EqualPower,
    SCurve,
    Exponential,
}

impl FadeCurve {
    pub fn native(self) -> fframes::FadeCurve {
        match self {
            Self::Linear => fframes::FadeCurve::Linear,
            Self::EqualPower => fframes::FadeCurve::EqualPower,
            Self::SCurve => fframes::FadeCurve::SCurve,
            Self::Exponential => fframes::FadeCurve::Exponential,
        }
    }
}

#[derive(Deserialize)]
pub(crate) struct Ducking {
    depth_db: f32,
    attack: f32,
    hold: f32,
    release: f32,
    merge_gap: f32,
}

impl Ducking {
    pub fn native(self) -> fframes::Ducking {
        fframes::Ducking {
            depth_db: self.depth_db,
            attack: self.attack,
            hold: self.hold,
            release: self.release,
            merge_gap: self.merge_gap,
        }
    }
}
