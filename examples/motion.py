"""Render a moving square without Python callbacks in the render loop."""

from pathlib import Path

import fframes

motion = fframes.compile_animation((fframes.Keyframe(start=0, end=1, from_value=0, to_value=48),))
positions = motion.sample_many(range(30), 30)
video = fframes.compile_video(
    fframes.VideoConfig(width=64, height=64, fps=30),
    tuple(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
        f'<rect x="{x}" y="20" width="16" height="16" fill="red"/></svg>'
        for x in positions
    ),
)
video.save_png(15, Path("frame.png"))
fframes.render(video, "video.mp4")
