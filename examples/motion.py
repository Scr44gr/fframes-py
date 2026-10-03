"""Render a moving square without Python callbacks in the render loop."""

from fframes import Keyframe, Timeline, Video, VideoConfig

motion = Timeline(keyframes=(Keyframe(start=0, end=1, from_value=0, to_value=48),))
positions = motion.sample_many(range(30), fps=30)
video = Video(
    config=VideoConfig(width=64, height=64, fps=30),
    frames=tuple(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
        f'<rect x="{x}" y="20" width="16" height="16" fill="red"/></svg>'
        for x in positions
    ),
)
video.save_png("frame.png", index=15)
video.render("video.mp4")
