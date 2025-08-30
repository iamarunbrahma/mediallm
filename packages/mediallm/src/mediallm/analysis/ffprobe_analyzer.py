#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404: subprocess is used safely with explicit args and no shell
from pathlib import Path

# Import media extensions from constants
from ..constants.media_formats import MEDIA_EXTENSIONS as MEDIA_EXTS


def _ffprobe_duration(path: Path) -> float | None:
    """Extract duration of media file using ffprobe."""
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path is None:
        return None
    try:
        # Call ffprobe with explicit args and no shell for security
        result = subprocess.run(  # nosec B603, B607
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            check=True,
            text=True,
        )
        data = json.loads(result.stdout)
        dur = data.get("format", {}).get("duration")
        return float(dur) if dur is not None else None
    except Exception:
        # Return None for any ffprobe errors (file not found, invalid format, etc.)
        return None


def discover_media_extended(cwd: Path | None = None) -> dict[str, object]:
    """Scan current directory for media files and extract context information."""
    base = cwd or Path.cwd()
    files: list[Path] = [p for p in base.iterdir() if p.is_file()]

    # Categorize files by media type using extension matching
    videos = [p for p in files if p.suffix.lower() in MEDIA_EXTS["video"]]
    audios = [p for p in files if p.suffix.lower() in MEDIA_EXTS["audio"]]
    images = [p for p in files if p.suffix.lower() in MEDIA_EXTS["image"]]

    # Collect detailed metadata for videos and audio files
    info = [
        {
            "path": str(p),
            "size": p.stat().st_size if p.exists() else None,
            "duration": _ffprobe_duration(p),
        }
        for p in videos + audios
    ]

    return {
        "cwd": str(base),
        "videos": [str(p) for p in videos],
        "audios": [str(p) for p in audios],
        "images": [str(p) for p in images],
        "info": info,
    }
