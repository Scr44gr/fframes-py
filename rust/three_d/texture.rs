//! Static and synchronized textures, including nested SVG/3D renders.

use crate::inspection::Source as _;
use crate::render::FrameCache;
use fframes::{
    SvgrRasterizer,
    media::ImageData,
    three_d::{Texture, Vec2},
};
use pyo3::{PyResult, exceptions::PyRuntimeError};
use serde::Deserialize;
use std::{path::PathBuf, sync::Arc};

#[derive(Deserialize)]
pub(super) struct Input {
    source: Source,
    repeat: [f32; 2],
    offset: [f32; 2],
}

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "lowercase")]
enum Source {
    Composition {
        plan: String,
    },
    Pixels {
        size: [u32; 2],
        pixels: Vec<u8>,
        srgb: bool,
    },
    Lottie {
        animation: crate::lottie::Input,
        size: [u32; 2],
    },
    Image {
        source: crate::buffers::Source,
        srgb: bool,
    },
    Video {
        source: crate::buffers::Source,
        offset: f64,
        r#loop: bool,
        size: Option<[u32; 2]>,
    },
    Svg {
        frames: Vec<String>,
        fps: usize,
        size: [u32; 2],
        fonts: Vec<PathBuf>,
        load_system_fonts: bool,
        #[serde(flatten)]
        media: crate::video::Media,
        shaders: Vec<crate::video::Binding>,
    },
    Scene {
        renderer: Box<super::Input>,
    },
}

enum Content {
    Composition {
        video: Box<crate::compose::SceneVideo>,
        fallback: Option<crate::backend::Rasterizer<'static>>,
    },
    Image(Arc<Texture>),
    Video {
        source: crate::clips::Source,
        size: Option<[u32; 2]>,
        fps: usize,
    },
    Svg {
        video: Box<crate::video::SvgVideo>,
        fps: usize,
        count: usize,
        size: [u32; 2],
        cacheable: bool,
        fallback: Option<crate::backend::Rasterizer<'static>>,
    },
    Lottie {
        program: Box<crate::lottie::Program>,
        size: [u32; 2],
    },
    Scene(Box<super::Program>),
}

pub(super) struct Program {
    content: Content,
    repeat: Vec2,
    offset: Vec2,
}

impl Input {
    pub fn compile(self, fps: usize, buffers: &crate::buffers::Buffers) -> PyResult<Program> {
        let content = match self.source {
            Source::Composition { plan } => {
                let video = crate::compose::from_plan(&plan, buffers)?;
                let fallback = (video.backend() != crate::backend::Backend::Cpu)
                    .then(crate::backend::Rasterizer::skia);
                Content::Composition {
                    video: Box::new(video),
                    fallback,
                }
            }
            Source::Image { source, srgb } => {
                let image = source.texture(srgb, buffers)?;
                Content::Image(Arc::new(image))
            }
            Source::Pixels {
                size: [width, height],
                pixels,
                srgb,
            } => {
                if pixels.len() != width as usize * height as usize * 4 {
                    return Err(pyo3::exceptions::PyValueError::new_err(
                        "pixels must contain width * height * 4 RGBA8 values",
                    ));
                }
                Content::Image(Arc::new(Texture::from_rgba8(width, height, &pixels, srgb)))
            }
            Source::Video {
                source,
                offset,
                r#loop,
                size,
            } => Content::Video {
                source: crate::clips::Source::open(
                    crate::clips::Input {
                        source,
                        offset,
                        r#loop,
                    },
                    fps,
                    buffers,
                )?
                .resize_buffers(size)?,
                size,
                fps,
            },
            Source::Svg {
                frames,
                fps,
                size,
                fonts,
                load_system_fonts,
                media,
                shaders,
            } => {
                let has_shaders = !shaders.is_empty();
                let cacheable = frames.len() == 1
                    && !has_shaders
                    && media.clips.is_empty()
                    && media.scenes.is_empty()
                    && media.lotties.is_empty();
                Content::Svg {
                    count: frames.len(),
                    fps,
                    size,
                    cacheable,
                    fallback: has_shaders.then(crate::backend::Rasterizer::skia),
                    video: Box::new(crate::video::build(
                        crate::video::Config {
                            width: size[0],
                            height: size[1],
                            fps,
                            fonts,
                            load_system_fonts,
                            backend: if has_shaders {
                                crate::backend::Backend::Skia
                            } else {
                                crate::backend::Backend::Cpu
                            },
                        },
                        frames,
                        shaders,
                        media,
                        Some(86400.),
                        buffers,
                    )?),
                }
            }
            Source::Lottie { animation, size } => Content::Lottie {
                program: Box::new(crate::lottie::Program::compile(animation, size)?),
                size,
            },
            Source::Scene { renderer } => Content::Scene(Box::new(super::Program::on_timeline(
                *renderer, fps, buffers,
            )?)),
        };
        Ok(Program {
            content,
            repeat: self.repeat.into(),
            offset: self.offset.into(),
        })
    }
}

fn image_texture(
    image: Arc<fframes::usvgr::PreloadedImageData>,
    width: u32,
    height: u32,
) -> Texture {
    Texture::from_image(&ImageData::new_from_raw_data(
        image,
        "fframes-py:texture".into(),
        fframes::media::ImageMetadata { width, height },
    ))
}

impl Program {
    pub fn at(
        &self,
        time: f64,
        cache: &mut FrameCache,
        rasterizer: &crate::backend::Rasterizer<'_>,
    ) -> PyResult<Arc<Texture>> {
        let key = std::ptr::from_ref(self) as usize;
        if let Some(texture) = cache.textures.get(&key) {
            return Ok(Arc::clone(texture));
        }
        let mut texture = match &self.content {
            Content::Composition { video, fallback } => {
                let rasterizer = if rasterizer.supports_shaders {
                    rasterizer
                } else {
                    fallback.as_ref().unwrap_or(rasterizer)
                };
                let index = ((time.max(0.) * video.fps() as f64 + 1e-9).floor() as usize)
                    .min(video.count() - 1);
                let tree =
                    crate::inspection::Source::tree(video.as_ref(), index, cache, rasterizer)?;
                let [w, h] = video.size();
                let image = rasterizer.rasterize(&tree, w, h).ok_or_else(|| {
                    PyRuntimeError::new_err("composition texture rasterization failed")
                })?;
                Texture::from_image(&image)
            }
            Content::Image(image) => (**image).clone(),
            Content::Video { source, size, fps } => {
                let options = size.map(|[width, height]| fframes::media::FrameConvertOptions {
                    resize: fframes::media::ResizeVideoFrame { width, height },
                });
                match source.image_resized(time, *fps, &mut cache.decoders, options.as_ref())? {
                    Some(image) => {
                        let (w, h) = (image.width, image.height);
                        image_texture(image, w, h)
                    }
                    None => Texture::from_rgba8(1, 1, &[0; 4], true),
                }
            }
            Content::Scene(program) => {
                Texture::from_image(&program.image(time, cache, rasterizer)?)
            }
            Content::Lottie { program, size } => {
                image_texture(program.image(time, cache, rasterizer)?, size[0], size[1])
            }
            Content::Svg {
                video,
                fps,
                count,
                size: [w, h],
                fallback,
                ..
            } => {
                let index = (time.max(0.) * *fps as f64 + 1e-9).floor() as usize;
                let rasterizer = if rasterizer.supports_shaders {
                    rasterizer
                } else {
                    fallback.as_ref().unwrap_or(rasterizer)
                };
                let tree = video.tree_at(index.min(count - 1), time, cache, rasterizer)?;
                let image = rasterizer
                    .rasterize(&tree, *w, *h)
                    .ok_or_else(|| PyRuntimeError::new_err("SVG texture rasterization failed"))?;
                Texture::from_image(&image)
            }
        };
        texture.repeat = self.repeat;
        texture.offset = self.offset;
        let texture = Arc::new(texture);
        if matches!(
            self.content,
            Content::Svg {
                cacheable: true,
                ..
            }
        ) && cache.textures.len() < 64
        {
            // GPU-backed mipmaps must not outlive this render's device.
            cache.textures.insert(key, Arc::clone(&texture));
        }
        Ok(texture)
    }
}
