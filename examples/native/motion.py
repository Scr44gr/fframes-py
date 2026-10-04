"""Render a moving square without Python callbacks in the render loop."""

from pathlib import Path

import fframes


def main() -> None:
    """Render the animation and a preview to output/native/."""
    output = Path("output/native")
    output.mkdir(parents=True, exist_ok=True)
    motion = fframes.compile_animation(
        (fframes.Keyframe(start=0, end=1, from_value=0, to_value=48),)
    )
    positions = motion.sample_many(range(30), 30)
    video = fframes.compile_video(
        fframes.VideoConfig(width=64, height=64, fps=30),
        tuple(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
            f'<rect x="{x}" y="20" width="16" height="16" fill="red"/></svg>'
            for x in positions
        ),
    )
    video.save_png(15, output / "motion.png")
    fframes.render(video, output / "motion.mp4")


if __name__ == "__main__":
    main()
