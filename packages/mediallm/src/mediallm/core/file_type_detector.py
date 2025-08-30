#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

from pathlib import Path
from typing import Final

from ..constants.media_formats import MEDIA_EXTENSIONS


class FileTypeDetector:
    """Detects file types based on extensions."""

    # Class constants for file extension mappings
    _VIDEO_EXTS: Final[set[str]] = MEDIA_EXTENSIONS["video"]
    _AUDIO_EXTS: Final[set[str]] = MEDIA_EXTENSIONS["audio"]
    _IMAGE_EXTS: Final[set[str]] = MEDIA_EXTENSIONS["image"]
    _SUBTITLE_EXTS: Final[set[str]] = MEDIA_EXTENSIONS["subtitle"]

    @classmethod
    def get_file_type(cls, file_path: Path | str) -> str:
        """Determine file type category based on extension."""
        if isinstance(file_path, str):
            file_path = Path(file_path)

        ext = file_path.suffix.lower()

        if ext in cls._VIDEO_EXTS:
            return "video"
        if ext in cls._AUDIO_EXTS:
            return "audio"
        if ext in cls._IMAGE_EXTS:
            return "image"
        if ext in cls._SUBTITLE_EXTS:
            return "subtitle"
        return "other"

    @classmethod
    def is_media_file(cls, file_path: Path | str) -> bool:
        """Check if file is a supported media file."""
        return cls.get_file_type(file_path) != "other"

    @classmethod
    def is_video_file(cls, file_path: Path | str) -> bool:
        """Check if file is a video file."""
        return cls.get_file_type(file_path) == "video"

    @classmethod
    def is_audio_file(cls, file_path: Path | str) -> bool:
        """Check if file is an audio file."""
        return cls.get_file_type(file_path) == "audio"

    @classmethod
    def is_image_file(cls, file_path: Path | str) -> bool:
        """Check if file is an image file."""
        return cls.get_file_type(file_path) == "image"

    @classmethod
    def is_subtitle_file(cls, file_path: Path | str) -> bool:
        """Check if file is a subtitle file."""
        return cls.get_file_type(file_path) == "subtitle"
