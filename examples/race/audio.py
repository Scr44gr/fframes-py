"""An original synthesized score and synchronized cartoon sound effects."""

import sys
import wave
from array import array
from math import exp, sin, sqrt, tanh, tau
from pathlib import Path
from typing import Literal

from .art import noise
from .scenes import DURATION

RATE = 48_000
Voice = Literal["bell", "bass", "pad", "kick", "hat", "snare", "sweep", "boing", "clack"]


def soundtrack(destination: Path) -> None:
    """Write a 48 kHz stereo PCM soundtrack without audio samples or dependencies."""
    left = array("f", [0.0]) * (RATE * DURATION)
    right = array("f", [0.0]) * (RATE * DURATION)

    def sound(
        start: float,
        duration: float,
        frequency: float,
        volume: float,
        voice: Voice = "bell",
        pan: float = 0,
        end_frequency: float = 0,
    ) -> None:
        first = round(start * RATE)
        count = min(round(duration * RATE), len(left) - first)
        left_gain, right_gain = sqrt((1 - pan) / 2), sqrt((1 + pan) / 2)
        phase = 0.0
        previous_noise = 0.0
        state = (first + round(frequency) * 17 + 1) & 0xFFFFFFFF
        for i in range(max(0, count)):
            t = i / RATE
            progress = t / duration
            state = (1664525 * state + 1013904223) & 0xFFFFFFFF
            white = state / 2147483648 - 1
            if voice == "kick":
                phase += tau * (47 + 120 * exp(-t * 30)) / RATE
                value = sin(phase) * exp(-t * 16)
            elif voice == "hat":
                value = (white - previous_noise) * exp(-t * 55) * 0.45
            elif voice == "snare":
                value = (white * 0.65 + sin(tau * 175 * t) * 0.35) * exp(-t * 18)
            elif voice == "clack":
                value = (sin(tau * frequency * t) * 0.6 + white * 0.4) * exp(-t * 90)
            elif voice == "sweep":
                phase += tau * (frequency + (end_frequency - frequency) * progress) / RATE
                envelope = sin(progress * 3.141592653589793) ** 1.7
                value = (white * 0.6 + sin(phase) * 0.3) * envelope
            elif voice == "boing":
                phase += tau * (frequency + 180 * sin(t * 21) * exp(-t * 5)) / RATE
                value = (sin(phase) + 0.22 * sin(phase * 2)) * exp(-t * 7)
            elif voice == "bass":
                phase = tau * frequency * t
                value = sin(phase) + 0.25 * sin(phase * 2) + 0.13 * sin(phase * 3)
                value *= min(1.0, t * 180) * exp(-t * 6) * min(1.0, (duration - t) * 80)
            elif voice == "pad":
                phase = tau * frequency * t
                value = sin(phase) + 0.3 * sin(phase * 1.004) + 0.15 * sin(phase * 2)
                value *= min(1.0, t * 3) * min(1.0, (duration - t) * 2)
            else:
                phase = tau * frequency * t
                value = sin(phase) * exp(-t * 5)
                value += 0.28 * sin(phase * 2.01) * exp(-t * 12)
                value *= min(1.0, t * 250) * min(1.0, (duration - t) * 100)
            previous_noise = white
            value *= volume
            left[first + i] += value * left_gain
            right[first + i] += value * right_gain

    def note(midi: int) -> float:
        return 440 * 2 ** ((midi - 69) / 12)

    # An airy opening resolves into an original, bouncy C-major race motif.
    for midi in (48, 55, 60, 64, 67):
        sound(0, 6.4, note(midi), 0.032, "pad", (midi - 60) / 30)
    for i, midi in enumerate((72, 79, 84, 88, 91, 88, 84, 79)):
        sound(0.2 + i * 0.42, 1.3, note(midi), 0.072, pan=sin(i) * 0.55)
    sound(3.8, 2.9, 90, 0.33, "sweep", end_frequency=1600)
    sound(6.4, 0.48, 180, 0.23, "boing")

    beat = 0.375  # 160 BPM, with a half-time introduction and a faster-feeling race.
    roots = (48, 45, 53, 55)
    melody = (72, 76, 79, 76, 81, 79, 76, 74, 72, 76, 79, 84, 83, 79, 76, 74)
    for step in range(40):
        start = 8.75 + step * beat
        root = roots[(step // 4) % len(roots)]
        if start >= 21.7:
            break
        sound(start, 0.30, note(root - 12), 0.19, "bass")
        sound(start, 0.24, 55, 0.20 if step % 2 == 0 else 0.12, "kick")
        sound(start + beat * 0.5, 0.10, 6000, 0.053, "hat", 0.27)
        if step % 2:
            sound(start, 0.20, 180, 0.13, "snare", -0.12)
        sound(start, 0.42, note(melody[step % 16]), 0.085, pan=sin(step) * 0.3)
        if step % 4 == 0:
            for interval in (0, 4 if root != 45 else 3, 7):
                sound(start, 1.35, note(root + interval + 12), 0.023, "pad")
    for i in range(10):
        start = 6.7 + i * 1.34
        sound(start, 0.12, 2400, 0.021, "sweep", pan=sin(i) * 0.8, end_frequency=3500)
        sound(start + 0.15, 0.10, 3100, 0.014, "sweep", pan=sin(i) * 0.8, end_frequency=2500)
    for i, start in enumerate((6.9, 7.6, 8.3)):
        sound(start, 0.16, note(72 + i * 2), 0.23)
    sound(9.0, 0.7, note(84), 0.26)
    for i in range(31):
        sound(9.1 + i * 0.31, 0.13, 210 + (i % 2) * 70, 0.072, "boing", -0.35)
    for i in range(57):
        sound(9.1 + i * 0.17, 0.06, 670 + (i % 3) * 180, 0.055, "clack", 0.2)
    sound(13.35, 0.8, 270, 0.31, "sweep", 0.25, 1900)
    for i in range(7):
        sound(13.65 + i * 0.085, 0.28, note(67 + i * 3), 0.095, pan=0.2)
    sound(18.45, 0.23, 1800, 0.27, "snare")
    for i, midi in enumerate((72, 76, 79, 84)):
        sound(18.47 + i * 0.12, 1.5, note(midi), 0.18, pan=(i - 1.5) * 0.18)
    for midi in (48, 60, 64, 67, 72, 76):
        sound(20.1, 3.8, note(midi), 0.045, "pad")
    for i, midi in enumerate((79, 84, 88, 91, 88, 84, 79, 84)):
        sound(20.2 + i * 0.3, 0.8, note(midi), 0.11, pan=sin(i) * 0.4)
    for i in range(17):
        sound(20.2 + i * 0.14, 0.12, 900 + noise(i) * 1300, 0.043, "snare", noise(i + 4) - 0.5)

    peak = max(max(abs(value) for value in left), max(abs(value) for value in right), 0.01)
    gain = 0.88 / peak
    pcm = array("h")
    for index, (lvalue, rvalue) in enumerate(zip(left, right, strict=True)):
        fade = min(1.0, index / (RATE * 0.04), (len(left) - index) / (RATE * 0.65))
        pcm.append(round(tanh(lvalue * gain) * 31000 * fade))
        pcm.append(round(tanh(rvalue * gain) * 31000 * fade))
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(destination), "wb") as output:
        output.setparams((2, 2, RATE, 0, "NONE", "not compressed"))
        output.writeframes(pcm.tobytes())
