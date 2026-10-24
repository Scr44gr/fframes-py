from typing import Literal

import pytest
from pydantic import ValidationError

import fframes as f
from fframes import compose as c
from fframes.compose.filters import DistantLight, PointLight, SpotLight, Step
from fframes.models import Backend
from tests.backends import BACKENDS

CASES: tuple[tuple[tuple[Step, ...], str], ...] = (
    (
        (c.Morphology(result="m", radius=(2, 1), operator="dilate"),),
        '<feMorphology in="SourceGraphic" operator="dilate" radius="2 1"/>',
    ),
    (
        (
            c.ConvolveMatrix(
                result="k",
                order=(3, 1),
                kernel=(0.25, 0.5, 0.25),
                divisor=1,
                target=(1, 0),
                edge="none",
                preserve_alpha=True,
            ),
        ),
        '<feConvolveMatrix in="SourceGraphic" order="3 1" kernelMatrix=".25 '
        '.5 .25" divisor="1" targetX="1" targetY="0" edgeMode="none" '
        'preserveAlpha="true"/>',
    ),
    (
        (
            c.ComponentTransfer(
                result="t",
                red=c.LinearTransfer(slope=0.5, intercept=0.2),
                green=c.GammaTransfer(exponent=2),
                blue=c.TableTransfer(values=(1, 0)),
                alpha=c.TableTransfer(kind="discrete", values=(0, 1)),
            ),
        ),
        '<feComponentTransfer in="SourceGraphic"><feFuncR type="linear" '
        'slope=".5" intercept=".2"/><feFuncG type="gamma" amplitude="1" '
        'exponent="2" offset="0"/><feFuncB type="table" tableValues="1 0"/>'
        '<feFuncA type="discrete" tableValues="0 1"/></feComponentTransfer>',
    ),
    (
        (
            c.Flood(result="f", color="#2080ff"),
            c.Blend(result="b", source="SourceGraphic", destination="f", mode="screen"),
        ),
        '<feFlood flood-color="#2080ff" result="f"/><feBlend '
        'in="SourceGraphic" in2="f" mode="screen"/>',
    ),
    (
        (
            c.Flood(result="f", color="#2080ff"),
            c.Composite(
                result="a",
                source="SourceGraphic",
                destination="f",
                operator="arithmetic",
                coefficients=(0, 0.75, 0.25, 0),
            ),
        ),
        '<feFlood flood-color="#2080ff" result="f"/><feComposite '
        'in="SourceGraphic" in2="f" operator="arithmetic" k1="0" k2=".75" '
        'k3=".25" k4="0"/>',
    ),
    (
        (
            c.Turbulence(
                result="noise",
                frequency=(0.1, 0.08),
                octaves=2,
                seed=7,
                noise="fractalNoise",
                stitch=True,
            ),
            c.DisplacementMap(
                result="d", destination="noise", scale=8, x_channel="R", y_channel="G"
            ),
        ),
        '<feTurbulence baseFrequency=".1 .08" numOctaves="2" seed="7" '
        'type="fractalNoise" stitchTiles="stitch" result="noise"/>'
        '<feDisplacementMap in="SourceGraphic" in2="noise" scale="8" '
        'xChannelSelector="R" yChannelSelector="G"/>',
    ),
    (
        (c.Flood(result="f", color="#10ff30", region=(4, 4, 5, 7)), c.Tile(result="t", source="f")),
        '<feFlood flood-color="#10ff30" x="4" y="4" width="5" height="7" '
        'result="f"/><feTile in="f"/>',
    ),
    (
        (
            c.Lighting(
                result="l",
                light=DistantLight(azimuth=45, elevation=30),
                color="#80ffff",
                surface_scale=3,
            ),
        ),
        '<feDiffuseLighting in="SourceAlpha" lighting-color="#80ffff" '
        'surfaceScale="3" diffuseConstant="1"><feDistantLight azimuth="45" '
        'elevation="30"/></feDiffuseLighting>',
    ),
    (
        (
            c.Lighting(
                result="l", mode="specular", exponent=8, light=PointLight(position=(16, 10, 20))
            ),
        ),
        '<feSpecularLighting in="SourceAlpha" specularExponent="8" '
        'specularConstant="1" surfaceScale="1" lighting-color="#ffffff">'
        '<fePointLight x="16" y="10" z="20"/></feSpecularLighting>',
    ),
    (
        (
            c.Lighting(
                result="l",
                light=SpotLight(position=(16, 16, 20), target=(16, 16, 0), cone=50, exponent=2),
            ),
        ),
        '<feDiffuseLighting in="SourceAlpha" diffuseConstant="1" '
        'surfaceScale="1" lighting-color="#ffffff"><feSpotLight x="16" y="16" '
        'z="20" pointsAtX="16" pointsAtY="16" pointsAtZ="0" '
        'limitingConeAngle="50" specularExponent="2"/></feDiffuseLighting>',
    ),
)


@pytest.mark.parametrize(("steps", "xml"), CASES)
@pytest.mark.parametrize("backend", BACKENDS)
def test_filter_primitives_match_native_svg(
    steps: tuple[Step, ...], xml: str, backend: Backend
) -> None:
    effect = c.Filter(steps=steps, units="user", region=(0, 0, 32, 32), color_space="srgb")
    composed = c.Video(
        resolution=(32, 32),
        backend=backend,
        composition=c.Composition(
            duration=1,
            children=(
                c.Composition(
                    filter=effect,
                    children=(
                        c.Rectangle(size=(16, 16), position=c.Position(x=8, y=8), fill="#d08040"),
                    ),
                ),
            ),
        ),
    ).rgba()
    raw = f.Video(
        config=f.VideoConfig(width=32, height=32, backend=backend),
        frames=(
            '<svg width="32" height="32"><defs><filter id="f" '
            'filterUnits="userSpaceOnUse" x="0" y="0" width="32" height="32" '
            'color-interpolation-filters="sRGB">' + xml + '</filter></defs><g filter="url(#f)">'
            '<rect x="8" y="8" width="16" height="16" fill="#d08040"/></g></svg>',
        ),
    ).rgba()
    assert composed == raw
    assert any(composed)


@pytest.mark.parametrize("backend", BACKENDS)
def test_filter_image_uses_explicit_buffer_and_region(backend: Backend) -> None:
    source = f.ImageBuffer(data=bytes((0, 255, 0, 255)) * 4, size=(2, 2))
    video = c.Video(
        resolution=(32, 32),
        backend=backend,
        composition=c.Composition(
            duration=1,
            children=(
                c.Rectangle(
                    size=(32, 32),
                    fill="#ff0000",
                    filter=c.Filter(
                        units="user",
                        region=(0, 0, 32, 32),
                        steps=(
                            c.FilterImage(
                                result="image", source=source, region=(4, 4, 8, 8), fit="stretch"
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    pixels = video.rgba()
    assert pixels[(8 * 32 + 8) * 4 : (8 * 32 + 9) * 4] == bytes((0, 255, 0, 255))
    assert pixels[:4] == bytes(4)


@pytest.mark.parametrize("mode", ["alpha", "luminance"])
@pytest.mark.parametrize("backend", BACKENDS)
def test_animated_layer_mask_matches_svg_and_uses_local_clock(
    mode: Literal["alpha", "luminance"], backend: Backend
) -> None:
    mask = c.LayerMask(
        mode=mode,
        content=c.Circle(
            radius=4,
            fill="#80808080",
            position=c.Position(x=c.Tween(from_value=0, to_value=8, duration=1), y=4),
        ),
    )
    video = c.Video(
        resolution=(32, 32),
        fps=2,
        backend=backend,
        composition=c.Composition(
            duration=2,
            children=(
                c.Rectangle(
                    size=(16, 16), fill="#ffffff", position=c.Position(x=8, y=8), mask=mask
                ).at(0.5),
            ),
        ),
    ).compile()
    assert not any(video.rgba(0))
    for frame, x in ((3, 8), (1, 0), (2, 4)):
        reference = f.Video(
            config=f.VideoConfig(width=32, height=32, backend=backend),
            frames=(
                f'<svg width="32" height="32"><defs><mask id="m" mask-type="{mode}" '
                f'x="-10%" y="-10%" width="120%" height="120%"><circle cx="{x + 4}" '
                f'cy="8" r="4" fill="#808080" fill-opacity="0.5019608"/></mask></defs>'
                f'<g transform="translate(8 8)" mask="url(#m)"><rect width="16" '
                f'height="16" fill="white"/></g></svg>',
            ),
        )
        assert video.rgba(frame) == reference.rgba()


def test_filter_contracts_reject_silently_ignored_settings() -> None:
    with pytest.raises(ValidationError, match="coefficients"):
        c.Composite(
            result="c", source="SourceGraphic", destination="SourceAlpha", coefficients=(0, 1, 1, 0)
        )
    with pytest.raises(ValidationError, match="kernel length"):
        c.ConvolveMatrix(result="c", order=(3, 1), kernel=(1,))
    with pytest.raises(ValidationError, match="divisor"):
        c.ConvolveMatrix(result="c", order=(1, 1), kernel=(1,), divisor=0)
    with pytest.raises(ValidationError, match="target"):
        c.ConvolveMatrix(result="c", order=(1, 1), kernel=(1,), target=(1, 0))
    with pytest.raises(ValidationError, match="exponent"):
        c.Lighting(result="l", light=DistantLight(), exponent=8)
    with pytest.raises(ValidationError, match="positive"):
        c.Tile(result="t", source="SourceGraphic", region=(0, 0, 0, 1))
    with pytest.raises(ValidationError, match="positive"):
        c.LayerMask(content=c.Circle(radius=1), region=(0, 0, 0, 1))
    sound = c.Audio(source=f.Pcm(data=bytes(4800 * 4), channels=1))
    video = c.Video(composition=c.Composition(duration=1, mask=c.LayerMask(content=sound)))
    with pytest.raises(ValueError, match="visuals only"):
        video.compile()


@pytest.mark.parametrize("backend", BACKENDS)
def test_content_mask_alignment_uses_target_canvas_not_video_canvas(backend: Backend) -> None:
    mask = c.LayerMask(
        content=c.Circle(radius=4, fill="#ffffff", position=c.Position(x="center", y="center"))
    )
    video = c.Video(
        resolution=(64, 64),
        backend=backend,
        composition=c.Composition(
            duration=1,
            children=(
                c.Rectangle(
                    size=(16, 16), fill="#ff0000", mask=mask, position=c.Position(x=8, y=8)
                ),
            ),
        ),
    )
    pixels = video.rgba()
    assert pixels[(16 * 64 + 16) * 4 : (16 * 64 + 17) * 4] == bytes((255, 0, 0, 255))
    assert pixels[(8 * 64 + 8) * 4 : (8 * 64 + 9) * 4] == bytes(4)
