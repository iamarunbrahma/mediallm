#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..constants.media_formats import ALL_EXTENSIONS
from ..constants.media_formats import AUDIO_CODEC_MAP
from ..constants.media_formats import VIDEO_AUDIO_CODEC_MAP
from ..constants.media_formats import VIDEO_CODEC_MAP
from ..processing.media_file_handler import most_recent_file
from ..safety.data_protection import create_secure_logger

logger = create_secure_logger(__name__)


def infer_action_from_query(user_query: str) -> str:
    """Infer the action based on user query patterns when model fails to provide it."""
    query_lower = user_query.lower()

    # Extract frames patterns (check before thumbnail for specificity)
    if any(
        pattern in query_lower
        for pattern in [
            "extract frames",
            "frames at",
            "every frame",
            "frame extraction",
            "fps",
        ]
    ):
        return "extract_frames"

    # Thumbnail/single frame patterns
    if any(
        pattern in query_lower
        for pattern in [
            "thumbnail",
            "single frame",
            "screenshot",
            "still image",
            "poster",
        ]
    ):
        return "thumbnail"

    # Audio extraction patterns (check before general convert)
    # But only if we're converting from video to audio format
    audio_formats = {
        "mp3",
        "wav",
        "flac",
        "ogg",
        "oga",
        "aac",
        "m4a",
        "wma",
        "opus",
        "ac3",
        "dts",
    }
    for audio_fmt in audio_formats:
        if any(pattern in query_lower for pattern in [f"to {audio_fmt}", f"into {audio_fmt}", f".{audio_fmt}"]):
            # Check if we're likely converting from video (common video extensions mentioned)
            if any(video_ext in query_lower for video_ext in ["mp4", "mov", "avi", "mkv", "webm", "flv"]):
                return "extract_audio"

    if any(
        pattern in query_lower
        for pattern in [
            "extract audio",
            "get audio",
            "audio only",
            "strip video",
            "audio track",
        ]
    ):
        return "extract_audio"

    # Subtitle burn-in patterns
    if any(
        pattern in query_lower
        for pattern in [
            "burn subtitles",
            "add subtitles",
            "subtitle",
            "captions",
            "hardcode subtitles",
            "bake subtitles",
        ]
    ):
        return "burn_subtitles"
    if any(
        pattern in query_lower
        for pattern in [
            "extract subtitles",
            "get subtitles",
            "rip subtitles",
            "subtitle extraction",
        ]
    ):
        return "extract_subtitles"

    # Slideshow patterns
    if any(
        pattern in query_lower
        for pattern in [
            "slideshow",
            "images to video",
            "photos to video",
            "image sequence",
            "picture slideshow",
        ]
    ):
        return "slideshow"

    # Overlay/watermark patterns
    if any(
        pattern in query_lower
        for pattern in [
            "overlay",
            "watermark",
            "add image",
            "on top",
            "superimpose",
            "composite",
        ]
    ):
        return "overlay"

    # Compression patterns
    if any(pattern in query_lower for pattern in ["compress", "reduce size", "make smaller", "optimize", "shrink"]):
        return "compress"

    # Trimming/segmentation patterns (be more specific)
    if any(pattern in query_lower for pattern in ["trim", "cut video", "clip video", "segment"]):
        return "trim"

    # Time-based patterns that clearly indicate trimming
    if any(pattern in query_lower for pattern in ["first", "last", "from", "between"]) and any(
        time_word in query_lower for time_word in ["second", "minute", "hour"]
    ):
        return "trim"

    # Duration-based patterns for clips/gifs but only if it's clearly a clip extraction
    if any(pattern in query_lower for pattern in ["second clip", "second video", "minute clip"]):
        return "trim"

    # Format conversion patterns (specific containers)
    if any(pattern in query_lower for pattern in ["change container", "remux", "recontainer", "format convert"]):
        return "format_convert"

    # Remove audio patterns
    if any(pattern in query_lower for pattern in ["remove audio", "mute", "no sound", "no audio", "silent"]):
        return "remove_audio"

    # Speed/timing modification patterns
    if any(
        pattern in query_lower
        for pattern in [
            "speed up",
            "slow down",
            "fast forward",
            "slow motion",
            "2x",
            "0.5x",
            "half speed",
            "double speed",
        ]
    ):
        return "convert"  # Speed changes are handled as convert with filters

    # Social media format patterns (Instagram, TikTok, etc.)
    if any(
        pattern in query_lower
        for pattern in [
            "instagram",
            "reels",
            "tiktok",
            "youtube shorts",
            "9:16",
            "vertical",
            "portrait",
        ]
    ):
        return "convert"  # Aspect ratio changes are convert operations

    # Resize/scale patterns
    if any(
        pattern in query_lower
        for pattern in [
            "resize",
            "scale",
            "1080p",
            "720p",
            "4k",
            "uhd",
            "hd",
            "resolution",
        ]
    ):
        return "convert"

    # Merge/concatenate patterns
    if any(pattern in query_lower for pattern in ["merge", "concatenate", "combine", "join", "concat"]):
        return "convert"  # Handled as convert with concat filters

    # Default fallback - most common action
    return "convert"


def infer_inputs_from_query(repaired: dict[str, Any], user_query: str, workspace: dict[str, Any]) -> None:
    """Try to infer input files from the user query and workspace."""
    query_lower = user_query.lower()

    # Create comprehensive file extension pattern from our constants
    all_extensions_str = "|".join(ALL_EXTENSIONS)

    # Enhanced file patterns with all supported extensions
    file_patterns = [
        # @-prefixed files (e.g., @video.mp4)
        rf"@(\w+\.(?:{all_extensions_str}))",
        # Standard filenames with extensions
        rf"(\w+\.(?:{all_extensions_str}))",
        # Quoted filenames (handling spaces)
        rf'["\']([^"\']*\.(?:{all_extensions_str}))["\']',
        # Paths with directories
        rf"([^\s]+/[^\s]*\.(?:{all_extensions_str}))",
        # Files without explicit extension but common names
        r"(\w*(?:video|audio|image|movie|clip|track|song|photo|picture)\w*)",
    ]

    found_files = []
    for pattern in file_patterns:
        matches = re.findall(pattern, query_lower, re.IGNORECASE)
        for match in matches:
            # Handle tuple results from groups
            filename = match[1] if isinstance(match, tuple) and len(match) > 1 else match
            if isinstance(filename, str) and filename.strip():
                found_files.append(filename.strip())

    # Try to match found files with workspace
    for filename in found_files:
        # Check in all workspace categories including subtitles
        workspace_lists = [
            workspace.get("videos", []),
            workspace.get("audios", []),
            workspace.get("images", []),
            workspace.get("subtitle_files", []),
        ]

        for file_list in workspace_lists:
            for workspace_file in file_list:
                workspace_file_str = str(workspace_file).lower()
                # Check exact match or partial match
                if (
                    filename == workspace_file_str.split("/")[-1]  # exact filename match
                    or filename in workspace_file_str
                ):  # partial path match
                    repaired["inputs"] = [str(workspace_file)]
                    logger.debug(f"Inferred input file: {workspace_file}")
                    return

    # Smart fallback based on action type
    action = repaired.get("action", "convert")

    if action in ["extract_audio", "compress", "convert", "trim", "overlay"]:
        # Prefer video files for these actions
        videos = workspace.get("videos", [])
        if videos:
            most_recent_video = most_recent_file([Path(v) for v in videos])
            if most_recent_video:
                repaired["inputs"] = [str(most_recent_video)]
                logger.debug(f"Using most recent video for {action}: {most_recent_video}")
            else:
                repaired["inputs"] = [str(videos[0])]
                logger.debug(f"Using first video for {action}: {videos[0]}")

    elif action == "slideshow":
        # Use all images for slideshow
        if workspace.get("images") and len(workspace["images"]) > 0:
            repaired["inputs"] = [str(img) for img in workspace["images"]]
            repaired["glob"] = True  # Enable glob for multiple images
            logger.debug(f"Using all images for slideshow: {len(workspace['images'])} files")

    elif action in ["burn_subtitles", "extract_subtitles"]:
        # For subtitle operations, need both video and subtitle
        if workspace.get("videos") and workspace.get("subtitle_files"):
            repaired["inputs"] = [str(workspace["videos"][0])]
            if not repaired.get("subtitle_path") and workspace.get("subtitle_files"):
                repaired["subtitle_path"] = str(workspace["subtitle_files"][0])
                logger.debug(f"Added subtitle file: {workspace['subtitle_files'][0]}")

    elif action == "thumbnail":
        # Use video for thumbnail extraction
        videos = workspace.get("videos", [])
        if videos:
            most_recent_video = most_recent_file([Path(v) for v in videos])
            if most_recent_video:
                repaired["inputs"] = [str(most_recent_video)]
            else:
                repaired["inputs"] = [str(videos[0])]

    # Final fallback: use any available media file (prefer most recent)
    if not repaired.get("inputs"):
        for media_type in ["videos", "audios", "images"]:
            media_files = workspace.get(media_type, [])
            if media_files:
                # Use most recent file for each media type
                most_recent = most_recent_file([Path(f) for f in media_files])
                if most_recent:
                    repaired["inputs"] = [str(most_recent)]
                    logger.debug(f"Final fallback: using most recent {media_type[:-1]}: {most_recent}")
                else:
                    repaired["inputs"] = [str(media_files[0])]
                    logger.debug(f"Final fallback: using first {media_type[:-1]}: {media_files[0]}")
                break


def infer_format_and_codec(repaired: dict[str, Any], user_query: str) -> None:
    """Infer format and codec from user query using comprehensive mappings."""
    query_lower = user_query.lower()

    # Build format detection patterns for all supported formats
    detected_format = None

    # Check for all extensions in our format maps (prioritize longest matches)
    all_formats = set(AUDIO_CODEC_MAP.keys()) | set(VIDEO_CODEC_MAP.keys())

    # Sort formats by length (longer first) to match specific formats like "jpeg" before "jpg"
    sorted_formats = sorted(all_formats, key=len, reverse=True)

    for fmt in sorted_formats:
        patterns = [
            f"to {fmt}",
            f"into {fmt}",
            f".{fmt}",
            f"as {fmt}",
            f"convert to {fmt}",
            f"save as {fmt}",
        ]
        if any(pattern in query_lower for pattern in patterns):
            detected_format = fmt
            logger.debug(f"Detected format from pattern: {fmt}")
            break

    if detected_format and not repaired.get("format"):
        repaired["format"] = detected_format
        logger.debug(f"Detected format: {detected_format}")

    # Set codecs based on format and action
    fmt = repaired.get("format")
    action = repaired.get("action", "convert")

    if fmt and fmt in AUDIO_CODEC_MAP:
        # Audio format
        if not repaired.get("audio_codec"):
            repaired["audio_codec"] = AUDIO_CODEC_MAP[fmt]

        # For audio extraction, don't set video codec
        if action == "extract_audio":
            repaired["video_codec"] = None

    elif fmt and fmt in VIDEO_CODEC_MAP:
        # Video format
        if not repaired.get("video_codec"):
            repaired["video_codec"] = VIDEO_CODEC_MAP[fmt]

        if not repaired.get("audio_codec") and fmt in VIDEO_AUDIO_CODEC_MAP:
            audio_codec = VIDEO_AUDIO_CODEC_MAP[fmt]
            if audio_codec != "none":
                repaired["audio_codec"] = audio_codec

    # Special handling for common cases
    if action == "extract_audio" and not fmt:
        # Default to MP3 for audio extraction if no format specified
        repaired["format"] = "mp3"
        repaired["audio_codec"] = "libmp3lame"
        repaired["video_codec"] = None

    elif action == "compress" and not repaired.get("video_codec"):
        # Default compression settings
        repaired["video_codec"] = "libx265"
        repaired["crf"] = 28
        if not repaired.get("audio_codec"):
            repaired["audio_codec"] = "aac"

    elif fmt == "gif":
        # Special GIF handling
        repaired["video_codec"] = "gif"
        repaired["audio_codec"] = "none"
        if not repaired.get("filters"):
            # Add default GIF conversion filter
            repaired["filters"] = [
                "fps=10,scale=320:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
            ]

    # Handle duration for GIF or clips
    if any(
        duration_pattern in query_lower for duration_pattern in ["second", "seconds", "sec", "minute", "minutes", "min"]
    ):
        duration_match = extract_duration_from_query(query_lower)
        if duration_match and not repaired.get("duration"):
            repaired["duration"] = duration_match


def extract_duration_from_query(query_lower: str) -> float | None:
    """Extract duration value from query text."""

    # Patterns for different duration formats
    patterns = [
        r"(\d+(?:\.\d+)?)\s*seconds?",
        r"(\d+(?:\.\d+)?)\s*secs?",
        r"(\d+(?:\.\d+)?)\s*minutes?",
        r"(\d+(?:\.\d+)?)\s*mins?",
        r"(\d+(?:\.\d+)?)\s*s\b",
        r"first\s+(\d+(?:\.\d+)?)\s*seconds?",
        r"(\d+(?:\.\d+)?)\s*second\s+\w+",  # "5 second gif"
    ]

    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            value = float(match.group(1))
            # Convert minutes to seconds
            if "minute" in pattern or "min" in pattern:
                value *= 60
            return value

    return None


def fix_action_validation_issues(repaired: dict[str, Any], user_query: str) -> None:
    """Fix common validation issues based on action requirements."""
    action = repaired.get("action")

    # Fix trim/segment validation issues
    if action in ["trim", "segment"]:
        # If we don't have duration/start/end, this probably shouldn't be trim
        if not any(repaired.get(field) for field in ["duration", "start", "end"]):
            # Check if it's actually a format conversion
            query_lower = user_query.lower()
            if any(pattern in query_lower for pattern in ["to", "into", "convert", "as"]):
                repaired["action"] = "convert"
                logger.debug("Changed trim to convert due to missing timing parameters")

    # Fix slideshow validation
    elif action == "slideshow":
        if not repaired.get("inputs"):
            # Need images for slideshow
            repaired["action"] = "convert"
            logger.debug("Changed slideshow to convert due to missing image inputs")

    # Fix overlay validation
    elif action == "overlay" and not repaired.get("overlay_path"):
        # Need overlay path for overlay action
        repaired["action"] = "convert"
        logger.debug("Changed overlay to convert due to missing overlay_path")
