"""Render reusable components and generated audio: python -m examples.composition."""

import math
import struct
import wave
from pathlib import Path

from fframes.compose import (
    Audio,
    Circle,
    Component,
    Composition,
    Position,
    Rectangle,
    RenderOptions,
    Text,
    Tween,
    Video,
)


class Badge(Component):
    """A reusable label with its own local canvas."""

    label: str

    def compose(self) -> Composition:
        """Center the label over a rounded background."""
        return Composition(
            size=(480, 112),
            position=Position(x="center", y="center"),
            children=(
                Rectangle(size=(480, 112), radius=24, fill="#FFD43B"),
                Text(
                    content=self.label,
                    position=Position(x="center", y="center"),
                    font_size=42,
                    fill="#172033",
                ),
            ),
        )


def main() -> None:
    """Generate a short tone and let Rust animate, mix and encode the video."""
    output = Path("output/composition")
    output.mkdir(parents=True, exist_ok=True)
    sound = output / "tone.wav"
    rate = 48_000
    samples = tuple(
        round(6000 * math.sin(2 * math.pi * 440 * index / rate)) for index in range(rate // 3)
    )
    with wave.open(str(sound), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    video = Video(
        resolution=(1280, 720),
        fps=30,
        composition=Composition(
            duration=3,
            children=(
                Rectangle(size=(1280, 720), fill="#172033"),
                Circle(
                    radius=110,
                    fill="#3776AB",
                    position=Position(
                        x=Tween(from_value=-220, to_value=1280, duration=3), y="center"
                    ),
                ),
                Badge(label="Python + Rust").at(0.5, duration=2),
                Audio(source=sound, fade_in=0.01, fade_out=0.15).at(0.5),
            ),
        ),
    )
    compiled = video.compile()
    compiled.save_png(output / "preview.png", index=30)
    compiled.render(output / "video.mp4", options=RenderOptions(concurrency=4))


if __name__ == "__main__":
    main()
