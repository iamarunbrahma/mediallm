#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import json
import logging
import shutil
import subprocess  # nosec B404: subprocess is used safely with explicit args and no shell
from pathlib import Path
from typing import Final

# Import media extensions from constants
from ..constants.media_formats import MEDIA_EXTENSIONS as MEDIA_EXTS

logger = logging.getLogger(__name__)

# Security constants for subprocess execution
DEFAULT_FFPROBE_TIMEOUT: Final[int] = 60  # 1 minute for metadata extraction
MAX_FFPROBE_OUTPUT_SIZE: Final[int] = 1024 * 1024  # 1MB for metadata


def _ffprobe_duration(path: Path, timeout: int | None = None) -> float | None:
    """Extract duration of media file using ffprobe.

    Args:
        path: Path to the media file.
        timeout: Timeout in seconds (defaults to DEFAULT_FFPROBE_TIMEOUT).

    Returns:
        Duration in seconds, or None if extraction fails.
    """
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path is None:
        logger.debug("ffprobe not found in PATH")
        return None

    effective_timeout = timeout or DEFAULT_FFPROBE_TIMEOUT

    try:
        # Call ffprobe with explicit args, no shell, and timeout for security
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
            timeout=effective_timeout,
        )

        # Check output size limit
        if len(result.stdout) > MAX_FFPROBE_OUTPUT_SIZE:
            logger.warning(f"ffprobe output exceeds size limit for {path}")
            return None

        data = json.loads(result.stdout)
        dur = data.get("format", {}).get("duration")
        return float(dur) if dur is not None else None

    except subprocess.TimeoutExpired:
        logger.warning(f"ffprobe timed out after {effective_timeout}s for {path}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse ffprobe JSON output for {path}: {e}")
        return None
    except subprocess.CalledProcessError as e:
        logger.debug(f"ffprobe failed for {path}: {e}")
        return None
    except OSError as e:
        logger.debug(f"OS error running ffprobe for {path}: {e}")
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
