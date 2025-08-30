#!/usr/bin/env python3
# Author: Arun Brahma

#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

from enum import Enum
from pathlib import Path  # noqa: TC003  # Path needed at runtime for Pydantic models
from typing import Final

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator


class MediaTaskProcessor:
    """Handles media task processing and validation."""

    _MS_PER_SECOND: Final[int] = 1000
    _SECONDS_PER_MINUTE: Final[int] = 60
    _MINUTES_PER_HOUR: Final[int] = 60

    @classmethod
    def seconds_to_timestamp(cls, value: float | int | str) -> str:
        """Convert numeric seconds to HH:MM:SS[.ms] timestamp format."""
        try:
            seconds_float = float(value)
        except Exception:
            return str(value)

        total_ms = int(round(seconds_float * cls._MS_PER_SECOND))
        ms = total_ms % cls._MS_PER_SECOND
        total_seconds = total_ms // cls._MS_PER_SECOND
        s = total_seconds % cls._SECONDS_PER_MINUTE
        total_minutes = total_seconds // cls._SECONDS_PER_MINUTE
        m = total_minutes % cls._MINUTES_PER_HOUR
        h = total_minutes // cls._MINUTES_PER_HOUR

        if ms:
            return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
        return f"{h:02d}:{m:02d}:{s:02d}"


def _seconds_to_timestamp(value: float | int | str) -> str:
    """Convert numeric seconds to HH:MM:SS[.ms] timestamp format."""
    return MediaTaskProcessor.seconds_to_timestamp(value)


class Action(str, Enum):
    """Supported ffmpeg operations for natural language processing."""

    convert = "convert"  # General format conversion
    extract_audio = "extract_audio"  # Extract audio track to separate file
    remove_audio = "remove_audio"  # Remove audio track from video
    trim = "trim"  # Cut video to specific time range
    segment = "segment"  # Extract segment (alias for trim)
    thumbnail = "thumbnail"  # Extract single frame as image
    frames = "frames"  # Extract multiple frames at specified FPS
    extract_frames = "extract_frames"  # Extract frames at specified intervals
    compress = "compress"  # Compress with quality settings
    overlay = "overlay"  # Overlay image/video on top of video
    format_convert = "format_convert"  # Convert to specific format
    burn_subtitles = "burn_subtitles"  # Burn subtitles into video
    extract_subtitles = "extract_subtitles"  # Extract subtitles from video
    slideshow = "slideshow"  # Create video slideshow from images


class MediaIntent(BaseModel):
    """Parsed user intent for media operations."""

    action: Action
    inputs: list[Path] = Field(default_factory=list)
    output: Path | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    filters: list[str] = Field(default_factory=list)
    start: str | None = None
    end: str | None = None
    duration: float | None = None
    scale: str | None = None
    bitrate: str | None = None
    crf: int | None = None
    overlay_path: Path | None = None
    overlay_xy: str | None = None
    fps: str | None = None
    glob: str | None = None
    extra_flags: list[str] = Field(default_factory=list)
    quality: str | None = None  # For quality settings
    format: str | None = None  # For format conversion
    subtitle_path: Path | None = None  # For subtitle operations

    @model_validator(mode="before")
    @classmethod
    def _coerce_lists(cls, values: object) -> object:
        """Pre-validate data coercion for common patterns."""
        if not isinstance(values, dict):
            return values
        # inputs: allow scalar -> [scalar] for single file operations
        inputs = values.get("inputs")
        if inputs is not None and not isinstance(inputs, list):
            values["inputs"] = [inputs]
        # filters: allow scalar -> [str(scalar)] for single filter
        filters = values.get("filters")
        if filters is not None and not isinstance(filters, list):
            values["filters"] = [str(filters)]
        # extra_flags: allow scalar -> [str(scalar)] for single flag
        extra_flags = values.get("extra_flags")
        if extra_flags is not None and not isinstance(extra_flags, list):
            values["extra_flags"] = [str(extra_flags)]

        # Ensure None values are converted to empty lists
        if values.get("filters") is None:
            values["filters"] = []
        if values.get("extra_flags") is None:
            values["extra_flags"] = []

        # Filter out empty strings from filters and extra_flags lists
        if isinstance(values.get("filters"), list):
            values["filters"] = [f for f in values["filters"] if f and f.strip()]
        if isinstance(values.get("extra_flags"), list):
            values["extra_flags"] = [f for f in values["extra_flags"] if f and f.strip()]

        # Fix empty string values for numeric fields
        cls._clean_empty_numeric_fields(values)

        return values

    @classmethod
    def _clean_empty_numeric_fields(cls, values: dict) -> None:
        """Clean empty string values for numeric fields."""
        numeric_fields = ["crf", "duration"]
        for field in numeric_fields:
            if values.get(field) == "":
                values[field] = None

        # start/end: allow numeric seconds -> HH:MM:SS[.ms] for convenience
        if "start" in values and not isinstance(values.get("start"), str):
            values["start"] = MediaTaskProcessor.seconds_to_timestamp(values["start"])
        if "end" in values and not isinstance(values.get("end"), str):
            values["end"] = MediaTaskProcessor.seconds_to_timestamp(values["end"])

        # fps: allow numeric values -> string
        if "fps" in values and not isinstance(values.get("fps"), str):
            values["fps"] = str(values["fps"])

        # glob: allow any value -> string or None
        if "glob" in values and values.get("glob") is not None:
            values["glob"] = str(values["glob"])

        return values

    @model_validator(mode="after")
    def _validate(self) -> MediaIntent:
        """Post-validation checks for action-specific requirements."""
        if self.action == Action.overlay and not self.overlay_path:
            raise ValueError("overlay requires overlay_path")

        if self.action in {Action.trim, Action.segment} and not (self.duration or self.end or self.start):
            raise ValueError("trim/segment requires start+end or duration")

        if self.action in {Action.convert, Action.compress, Action.format_convert} and not self.inputs:
            raise ValueError("convert/compress/format_convert requires at least one input")

        if self.action == Action.extract_audio and not self.inputs:
            raise ValueError("extract_audio requires an input file")

        # Add validation for new actions
        if self.action == Action.extract_frames and not self.fps:
            raise ValueError("extract_frames requires fps parameter")

        if self.action == Action.format_convert and not self.format:
            raise ValueError("format_convert requires format parameter")

        # Ensure incompatible combos are caught
        if self.action == Action.thumbnail and self.fps:
            raise ValueError("thumbnail is incompatible with fps; use frames action")

        return self


class CommandEntry(BaseModel):
    """Single ffmpeg command execution unit."""

    input: Path
    output: Path
    args: list[str] = Field(default_factory=list)
    extra_inputs: list[Path] = Field(default_factory=list)


class CommandPlan(BaseModel):
    """Complete execution plan for ffmpeg operations."""

    summary: str
    entries: list[CommandEntry]
