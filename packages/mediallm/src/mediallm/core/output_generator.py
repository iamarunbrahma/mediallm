#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Final

from ..utils.data_models import Action
from ..utils.data_models import MediaIntent
from .file_type_detector import FileTypeDetector

if TYPE_CHECKING:
    from pathlib import Path


class OutputGenerator:
    """Generates output filenames based on task and input file."""

    # Format extension mappings
    _FORMAT_EXTENSIONS: Final[dict[str, str]] = {
        "mp4": ".mp4",
        "avi": ".avi",
        "mov": ".mov",
        "mkv": ".mkv",
        "webm": ".webm",
        "flv": ".flv",
        "wmv": ".wmv",
        "3gp": ".3gp",
        "m4v": ".m4v",
        "mpg": ".mpg",
        "mpeg": ".mpeg",
        "ts": ".ts",
        "m2ts": ".m2ts",
        "mts": ".mts",
        "vob": ".vob",
        "ogv": ".ogv",
        "dv": ".dv",
        "rm": ".rm",
        "rmvb": ".rmvb",
        "asf": ".asf",
        "m2v": ".m2v",
        "f4v": ".f4v",
        "mp3": ".mp3",
        "wav": ".wav",
        "aac": ".aac",
        "flac": ".flac",
        "ogg": ".ogg",
        "m4a": ".m4a",
        "opus": ".opus",
        "wma": ".wma",
        "mp2": ".mp2",
        "oga": ".oga",
        "amr": ".amr",
        "ape": ".ape",
        "wv": ".wv",
        "au": ".au",
        "aiff": ".aiff",
        "aif": ".aif",
        "ac3": ".ac3",
        "dts": ".dts",
        "ra": ".ra",
        "png": ".png",
        "jpg": ".jpg",
        "jpeg": ".jpeg",
        "gif": ".gif",
        "bmp": ".bmp",
        "tiff": ".tiff",
        "webp": ".webp",
        "srt": ".srt",
        "vtt": ".vtt",
        "ass": ".ass",
        "ssa": ".ssa",
        "sub": ".sub",
        "idx": ".idx",
    }

    # Codec to extension mappings
    _AUDIO_CODEC_EXTENSIONS: Final[dict[tuple[str, ...], str]] = {
        ("mp3", "libmp3lame"): ".mp3",
        ("aac",): ".aac",
        ("libvorbis", "vorbis", "libogg"): ".ogg",
        ("flac",): ".flac",
        ("pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_f32le", "pcm_f64le"): ".wav",
        ("libopus", "opus"): ".opus",
        ("wmav2", "wma"): ".wma",
        ("mp2", "libtwolame"): ".mp2",
        ("ac3", "ac3_fixed"): ".ac3",
        ("wavpack", "libwavpack"): ".wv",
        ("libopencore_amrnb", "amr_nb", "amr"): ".amr",
        ("dca",): ".dts",
        ("pcm_mulaw", "pcm_alaw"): ".au",
        ("pcm_s16be", "pcm_s24be", "pcm_s32be"): ".aiff",
        ("alac",): ".m4a",
        ("real_144",): ".ra",
    }

    _VIDEO_CODEC_EXTENSIONS: Final[dict[tuple[str, ...], str]] = {
        ("libx264", "libx265", "h264", "h265"): ".mp4",
        ("libvpx", "libvpx-vp9"): ".webm",
        ("flv",): ".flv",
        ("wmv2",): ".wmv",
    }

    def __init__(self) -> None:
        """Initialize the output name generator."""
        self._file_type_detector = FileTypeDetector()

    def derive_output_name(self, input_path: Path, task: MediaIntent, output_dir: Path | None = None) -> Path:
        """Derive output filename based on task and input file."""
        if task.output and task.output != input_path:
            # If output is specified, use it but potentially move to output directory
            if output_dir:
                return output_dir / task.output.name
            return task.output

        stem = input_path.stem
        suffix = input_path.suffix

        # Determine output directory
        target_dir = output_dir if output_dir else input_path.parent

        return self._generate_action_specific_name(task, target_dir, stem, suffix, input_path)

    def _generate_action_specific_name(
        self,
        task: MediaIntent,
        target_dir: Path,
        stem: str,
        suffix: str,
        input_path: Path,
    ) -> Path:
        """Generate action-specific output names."""
        if task.action == Action.extract_audio:
            return target_dir / f"{stem}.mp3"
        if task.action == Action.thumbnail:
            return target_dir / "thumbnail.png"
        if task.action == Action.frames:
            return target_dir / f"{stem}_frame_%04d.png"
        if task.action == Action.extract_frames:
            return target_dir / f"{stem}_frames_%04d.png"
        if task.action == Action.trim:
            return target_dir / "clip.mp4"
        if task.action == Action.remove_audio:
            return target_dir / f"{stem}_mute.mp4"
        if task.action == Action.overlay:
            return target_dir / f"{stem}_overlay.mp4"
        if task.action == Action.burn_subtitles:
            return target_dir / f"{stem}_subtitled.mp4"
        if task.action == Action.extract_subtitles:
            return target_dir / f"{stem}.srt"
        if task.action == Action.slideshow:
            return target_dir / "slideshow.mp4"
        if task.action in {Action.convert, Action.compress}:
            return self._generate_convert_name(task, target_dir, stem, suffix, input_path)
        if task.action == Action.format_convert:
            return self._generate_format_convert_name(task, target_dir, stem, suffix)

        return target_dir / f"{stem}{suffix}"

    def _generate_convert_name(
        self,
        task: MediaIntent,
        target_dir: Path,
        stem: str,
        suffix: str,
        input_path: Path,
    ) -> Path:
        """Generate convert action output name."""
        # First check if target format is specified in task
        target_extension = self._detect_target_format_from_task(task)

        if target_extension:
            # Use the detected target format
            return target_dir / f"{stem}_converted{target_extension}"
        # Fall back to input-type-based naming
        file_type = self._file_type_detector.get_file_type(input_path)

        if file_type == "video":
            return target_dir / f"{stem}_converted.mp4"
        if file_type == "audio":
            # For audio files, maintain audio format or convert to common format
            if task.audio_codec == "none":  # Removing audio
                return target_dir / f"{stem}_video.mp4"
            return target_dir / f"{stem}_converted.mp3"
        if file_type == "image":
            # For image files, maintain image format unless converting to video
            if task.video_codec or "video" in str(task.filters or "").lower():
                return target_dir / f"{stem}_converted.mp4"
            return target_dir / f"{stem}_converted{suffix}"
        if file_type == "subtitle":
            # For subtitle files, use the target format if specified, otherwise default to SRT
            if target_extension:
                return target_dir / f"{stem}_converted{target_extension}"
            return target_dir / f"{stem}_converted.srt"
        # For non-media files, keep original extension to indicate unsupported conversion
        return target_dir / f"{stem}_converted{suffix}"

    def _generate_format_convert_name(self, task: MediaIntent, target_dir: Path, stem: str, suffix: str) -> Path:
        """Generate format convert action output name."""
        # Use the format from the task to determine the extension
        if task.format:
            extension = self._FORMAT_EXTENSIONS.get(task.format, f".{task.format}")
            return target_dir / f"{stem}{extension}"
        return target_dir / f"{stem}{suffix}"

    def _detect_target_format_from_task(self, task: MediaIntent) -> str | None:
        """Detect target format from ffmpeg task."""
        # Check if format field is specified
        if task.format:
            # Strip any leading dots before lookup to avoid double dots in output
            cleaned_format = task.format.lstrip(".")
            return self._FORMAT_EXTENSIONS.get(cleaned_format, f".{cleaned_format}")

        # Infer format from codecs
        if task.audio_codec and not task.video_codec:
            # Audio-only output - use the helper function with mapping
            return self._get_extension_for_codec(task.audio_codec, self._AUDIO_CODEC_EXTENSIONS, ".mp3")
        if task.video_codec and task.audio_codec:
            # Video output - use the helper function with mapping
            return self._get_extension_for_codec(task.video_codec, self._VIDEO_CODEC_EXTENSIONS, ".mp4")

        return None

    def _get_extension_for_codec(self, codec: str, codec_map: dict[tuple[str, ...], str], default: str) -> str:
        """Helper function to find extension for a codec using the mapping."""
        for codecs, extension in codec_map.items():
            if codec in codecs:
                return extension
        return default
