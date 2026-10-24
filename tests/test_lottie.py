from pathlib import Path

import pytest

import fframes
from fframes import compose
from fframes import three_d as d
from tests.test_three_d import pixel, renderer


@pytest.fixture
def animation(tmp_path: Path) -> fframes.Lottie:
    source = tmp_path / "moving.json"
    source.write_text(
        """{
      "v":"5.7.4", "fr":10, "ip":0, "op":10, "w":64, "h":64,
      "assets":[], "layers":[{
        "ty":4, "ind":1, "ip":0, "op":10, "st":0, "sr":1,
        "ks":{"o":{"a":0,"k":100}, "r":{"a":0,"k":0},
          "p":{"a":1,"k":[{"t":0,"s":[16,32,0],"e":[48,32,0],
             "o":{"x":0,"y":0},"i":{"x":1,"y":1}}, {"t":10,"s":[48,32,0]}]},
          "a":{"a":0,"k":[0,0,0]}, "s":{"a":0,"k":[100,100,100]}},
        "shapes":[{"ty":"rc","d":1,"s":{"a":0,"k":[20,20]},
          "p":{"a":0,"k":[0,0]},"r":{"a":0,"k":0}},
          {"ty":"fl","c":{"a":0,"k":[1,0,0,1]},"o":{"a":0,"k":100},"r":1}]
      }]
    }""",
        encoding="utf-8",
    )
    return fframes.Lottie(source=source)


def test_lottie_metadata_timing_and_pixels_match_between_apis(animation: fframes.Lottie) -> None:
    assert (animation.info.width, animation.info.height, animation.info.duration) == (64, 64, 1)
    svg = '<svg width="64" height="64"><image href="lottie:shape" width="64" height="64"/></svg>'
    native = fframes.Video(
        config=fframes.VideoConfig(width=64, height=64, fps=10),
        frames=(svg,) * 15,
        lotties=(
            fframes.LottieBinding(name="shape", animation=animation, size=(64, 64), start_at=0.2),
        ),
    )
    compiled = compose.Video(
        resolution=(64, 64),
        fps=10,
        composition=compose.Composition(
            duration=1.5,
            children=(compose.LottieLayer(animation=animation, size=(64, 64)).at(0.2),),
        ),
    ).compile()
    for frame in (0, 2, 7, 14):
        assert native.rgba(frame) == compiled.rgba(frame)
    assert pixel(native.rgba(2), 16) == (255, 0, 0, 255)
    assert pixel(native.rgba(7)) == (255, 0, 0, 255)
    assert pixel(native.rgba(14), 48) == (255, 0, 0, 255)
    assert not any(native.rgba(0))


def test_lottie_texture_loop_speed_offset_and_invalid_source(animation: fframes.Lottie) -> None:
    looping = fframes.Lottie(source=animation.source, offset=0.2, speed=2, loop=True)
    scene = renderer(
        d.Scene(
            nodes=(
                d.Mesh(
                    geometry=d.Plane(size=(3, 3)),
                    material=d.Material(
                        shading="unlit",
                        map=d.Texture(source=d.LottieTexture(animation=looping, size=(64, 64))),
                    ),
                ),
            )
        )
    )
    assert scene.rgba(0.1) == scene.rgba(0.5)
    assert scene.rgba(0) != scene.rgba(0.1)
    with pytest.raises(ValueError, match=r"offset.*EOF"):
        compose.Video(
            composition=compose.Composition(
                duration=1,
                children=(
                    compose.LottieLayer(
                        animation=fframes.Lottie(source=animation.source, offset=2), size=(64, 64)
                    ),
                ),
            )
        ).compile()
    Path(animation.source).write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError):
        _ = fframes.Lottie(source=animation.source).info
