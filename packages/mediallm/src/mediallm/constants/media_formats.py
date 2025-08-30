#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

from typing import Final

# Video file extensions
VIDEO_EXTENSIONS: Final[set[str]] = {
    "mp4",
    "mov",
    "avi",
    "mkv",
    "webm",
    "flv",
    "wmv",
    "3gp",
    "m4v",
    "mpg",
    "mpeg",
    "ts",
    "m2ts",
    "mts",
    "vob",
    "ogv",
    "dv",
    "rm",
    "rmvb",
    "asf",
    "m2v",
    "f4v",
}

# Audio file extensions
AUDIO_EXTENSIONS: Final[set[str]] = {
    "mp3",
    "wav",
    "aac",
    "flac",
    "ogg",
    "opus",
    "wma",
    "m4a",
    "mp2",
    "oga",
    "amr",
    "ape",
    "wv",
    "au",
    "aiff",
    "aif",
    "ac3",
    "dts",
    "ra",
}

# Image file extensions
IMAGE_EXTENSIONS: Final[set[str]] = {"png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"}

# Subtitle file extensions
SUBTITLE_EXTENSIONS: Final[set[str]] = {"srt", "vtt", "ass", "ssa", "sub", "idx"}

# All supported extensions combined
ALL_EXTENSIONS: Final[set[str]] = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | IMAGE_EXTENSIONS | SUBTITLE_EXTENSIONS

# Media extensions grouped by category (compatible with existing scanner)
MEDIA_EXTENSIONS: Final[dict[str, set[str]]] = {
    "video": {f".{ext}" for ext in VIDEO_EXTENSIONS},
    "audio": {f".{ext}" for ext in AUDIO_EXTENSIONS},
    "image": {f".{ext}" for ext in IMAGE_EXTENSIONS},
    "subtitle": {f".{ext}" for ext in SUBTITLE_EXTENSIONS},
}

# Audio codec mappings
AUDIO_CODEC_MAP: Final[dict[str, str]] = {
    "mp3": "libmp3lame",
    "wav": "pcm_s16le",
    "flac": "flac",
    "ogg": "libvorbis",
    "oga": "libvorbis",
    "opus": "libopus",
    "m4a": "alac",
    "aac": "aac",
    "mp2": "mp2",
    "ac3": "ac3",
    "wv": "wavpack",
    "au": "pcm_mulaw",
    "aiff": "pcm_s16be",
    "aif": "pcm_s16be",
    "amr": "libopencore_amrnb",
    "dts": "dca",
    "ra": "real_144",
    "wma": "wmav2",
}

# Video codec mappings for specific formats
VIDEO_CODEC_MAP: Final[dict[str, str]] = {
    "mp4": "libx264",
    "avi": "libx264",
    "webm": "libvpx-vp9",
    "flv": "flv",
    "wmv": "wmv2",
    "mkv": "libx264",
    "mov": "libx264",
    "gif": "gif",
    "m4v": "libx264",
    "ogv": "libtheora",
}

# Default audio codec for video formats
VIDEO_AUDIO_CODEC_MAP: Final[dict[str, str]] = {
    "mp4": "aac",
    "avi": "mp3",
    "webm": "libopus",
    "flv": "mp3",
    "wmv": "wmav2",
    "mkv": "aac",
    "mov": "aac",
    "gif": "none",  # GIFs don't have audio
    "m4v": "aac",
    "ogv": "libvorbis",
}
