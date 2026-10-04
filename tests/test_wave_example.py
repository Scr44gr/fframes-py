import numpy as np
import pytest

import fframes
from examples.compose.audio_announce import wave_path
from examples.native.audio_announce import path
from examples.shared.audio_announce import controls, waves
from fframes import compose as c


def test_wave_solver_has_continuous_derivatives_and_natural_endpoints() -> None:
    points = np.array(((0, 2, -1, 4, 0), (3, 3, 3, 3, 3)), dtype=np.float32)
    original = points.copy()
    a, b = controls(points)
    np.testing.assert_array_equal(points, original)
    np.testing.assert_allclose(points[:, 1:-1] - b[:, :-1], a[:, 1:] - points[:, 1:-1], atol=1e-6)
    np.testing.assert_allclose(-2 * b[:, :-1] + a[:, :-1], -2 * a[:, 1:] + b[:, 1:], atol=2e-6)
    np.testing.assert_allclose(points[:, 0] - 2 * a[:, 0] + b[:, 0], 0, atol=1e-6)
    np.testing.assert_allclose(points[:, -1] - 2 * b[:, -1] + a[:, -1], 0, atol=1e-6)
    np.testing.assert_allclose(a[1], 3)
    np.testing.assert_allclose(b[1], 3)
    with pytest.raises(ValueError, match="three"):
        controls(points[:, :2])


def test_wave_ports_preserve_four_profiles_and_sampled_curves() -> None:
    values = np.zeros((3, 256), dtype=np.float32)
    values[1, 1::3], values[2, 2::4] = 0.2, 0.5
    original = values.copy()
    profiles = waves(values)
    np.testing.assert_array_equal(values, original)
    native = fframes.Video(
        config=fframes.VideoConfig(width=1920, height=1080, fps=30),
        frames=tuple(
            '<svg width="1920" height="1080"><g opacity=".5" stroke="white" stroke-width="6">'
            + "".join(path(wave, i) for wave in profiles)
            + "</g></svg>"
            for i in range(3)
        ),
    )
    composed = c.Video(
        resolution=(1920, 1080),
        fps=30,
        load_system_fonts=False,
        composition=c.Composition(
            duration=0.1,
            children=(c.Composition(opacity=0.5, children=tuple(map(wave_path, profiles))),),
        ),
    ).compile()
    frames = []
    for index in (2, 0, 1):
        a = np.frombuffer(native.rgba(index), np.uint8).astype(np.int16)
        b = np.frombuffer(composed.rgba(index), np.uint8)
        assert np.abs(a - b).mean() < 0.02
        frames.append(b)
    assert not np.array_equal(frames[0], frames[1])
