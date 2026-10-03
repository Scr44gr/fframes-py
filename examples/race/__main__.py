"""Render with ``uv run python -m examples.race`` after native setup."""

import argparse
import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from fframes import Video, VideoConfig

from .art import paper_texture
from .audio import soundtrack
from .scenes import DURATION, frame


class Settings(BaseModel):
    """Validated export settings; width preserves an even 16:9 raster."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    width: Annotated[int, Field(ge=640, le=3840, multiple_of=32)] = 1920
    workers: Annotated[int, Field(ge=1, le=16)] = 4
    output: Path = Path("output/race")
    preview: bool = False

    @property
    def height(self) -> int:
        """Return the corresponding 16:9 height."""
        return self.width * 9 // 16


class Arguments(argparse.Namespace):
    """Concrete argparse field types."""

    width: int
    workers: int
    output: Path
    preview: bool


def ffmpeg_path() -> str:
    """Resolve the existing FFmpeg installation without invoking a shell."""
    executable = shutil.which("ffmpeg")
    if executable is not None:
        return executable
    directory = os.environ.get("FFMPEG_DIR")
    if directory:
        candidate = Path(directory) / "bin" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if candidate.is_file():
            return str(candidate)
    msg = "FFmpeg is required; run scripts/setup-native.ps1 or put ffmpeg on PATH."
    raise FileNotFoundError(msg)


def previews(settings: Settings, texture: str) -> None:
    """Save representative frames before spending time on the complete render."""
    times = (1.0, 3.5, 5.3, 7.0, 10.8, 15.2, 18.7, 22.0)
    video = Video(
        config=VideoConfig(width=settings.width, height=settings.height, load_system_fonts=True),
        frames=tuple(frame(time, texture, settings.width, settings.height) for time in times),
    )
    for index, time in enumerate(times):
        video.save_png(settings.output / f"scene-{time:04.1f}.png", index=index)
    print(f"Saved {len(times)} storyboard frames to {settings.output}", flush=True)


def render(settings: Settings, texture: str) -> None:
    """Rasterize SVGs with fframes and encode bounded batches of RGBA frames."""
    executable = ffmpeg_path()
    wav = settings.output / "soundtrack.wav"
    print("Synthesizing the original music and sound effects...", flush=True)
    soundtrack(wav)
    fps = 30
    print("Preparing 720 SVG frames...", flush=True)
    video = Video(
        config=VideoConfig(
            width=settings.width, height=settings.height, fps=fps, load_system_fonts=True
        ),
        frames=tuple(
            frame(i / fps, texture, settings.width, settings.height) for i in range(DURATION * fps)
        ),
    )
    native = video.native
    destination = settings.output / "python-rust-race.mp4"
    temporary = settings.output / "rendering.mp4"
    command = [
        executable,
        "-hide_banner",
        "-loglevel",
        "warning",
        "-y",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgba",
        "-video_size",
        f"{settings.width}x{settings.height}",
        "-framerate",
        str(fps),
        "-i",
        "pipe:0",
        "-i",
        str(wav),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libopenh264",
        "-b:v",
        "12M",
        "-maxrate",
        "16M",
        "-bufsize",
        "24M",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-g",
        "60",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-colorspace",
        "bt709",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-t",
        str(DURATION),
        "-movflags",
        "+faststart",
        str(temporary),
    ]
    started = perf_counter()
    # All arguments are passed directly to a resolved local executable, without a shell.
    with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:  # noqa: S603
        if encoder.stdin is None:
            msg = "FFmpeg did not open its input pipe"
            raise RuntimeError(msg)
        try:
            with ThreadPoolExecutor(max_workers=settings.workers) as pool:
                for start in range(0, len(video), settings.workers):
                    stop = min(start + settings.workers, len(video))
                    for pixels in pool.map(native.rgba, range(start, stop)):
                        encoder.stdin.write(pixels)
                    if stop % 60 < settings.workers or stop == len(video):
                        elapsed = perf_counter() - started
                        print(f"Rendered {stop}/{len(video)} frames in {elapsed:.1f}s", flush=True)
            encoder.stdin.close()
            code = encoder.wait()
            if code:
                raise subprocess.CalledProcessError(code, command)
        except BaseException:
            encoder.kill()
            raise
    temporary.replace(destination)
    video.save_png(settings.output / "poster.png", index=22 * fps)
    metadata = {
        "video": destination.name,
        "width": settings.width,
        "height": settings.height,
        "fps": fps,
        "duration_seconds": DURATION,
        "soundtrack": wav.name,
        "artwork": "Procedural SVG drawings and paper texture generated in Python",
        "audio": "Original Python synthesis; no borrowed samples or music",
        "rasterizer": "fframes-py CPU rendering",
        "encoding": "FFmpeg libopenh264 + AAC-LC, YUV420P, faststart",
    }
    (settings.output / "export.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Finished: {destination}", flush=True)


def main() -> None:
    """Parse demo settings and generate a storyboard or the final video."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path("output/race"))
    parser.add_argument("--preview", action="store_true")
    args = Arguments()
    parser.parse_args(namespace=args)
    settings = Settings(
        width=args.width, workers=args.workers, output=args.output, preview=args.preview
    )
    settings.output.mkdir(parents=True, exist_ok=True)
    texture = paper_texture(settings.output / "paper.svg")
    if settings.preview:
        previews(settings, texture)
    else:
        render(settings, texture)


if __name__ == "__main__":
    main()
