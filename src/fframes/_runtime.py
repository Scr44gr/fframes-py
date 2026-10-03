"""Locate explicitly configured FFmpeg DLLs for Windows source installations."""

import os
import sys
from pathlib import Path

if sys.platform == "win32" and (directory := os.environ.get("FFMPEG_DIR")):
    # Keep the handle alive: closing it removes the DLL search directory.
    dll_directory = os.add_dll_directory(str(Path(directory) / "bin"))
