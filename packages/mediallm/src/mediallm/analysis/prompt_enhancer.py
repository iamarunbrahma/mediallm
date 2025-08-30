#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from typing import Final


class PromptEnhancer:
    """Enhances user prompts to improve LLM command generation accuracy."""

    # Class constants for enhancement patterns
    _ENHANCEMENT_PATTERNS: Final[list[tuple[str, str]]] = [
        # Aspect ratio patterns
        (
            r"\b(?:make|convert|resize|scale)\s+(?:to\s+)?(\d+):(\d+)\s+(?:aspect\s+)?ratio\b",
            r"convert to \1:\2 aspect ratio",
        ),
        (r"\b(\d+):(\d+)\s+(?:aspect\s+)?ratio\b", r"\1:\2 aspect ratio"),
        # Resolution patterns
        (r"\b(\d{3,4})[xX](\d{3,4})\b", r"\1x\2 resolution"),
        (r"\b(\d{3,4})p\b", r"\1p resolution"),
        # Social media platform patterns
        (
            r"\b(?:for\s+)?(?:Instagram|IG)\s+(?:Reels?|Stories?|Posts?)\b",
            r"for Instagram Reels (9:16 aspect ratio, 1080x1920)",
        ),
        (
            r"\b(?:for\s+)?(?:TikTok|Tik\s+Tok)\b",
            r"for TikTok (9:16 aspect ratio, 1080x1920)",
        ),
        (
            r"\b(?:for\s+)?(?:YouTube|YT)\s+(?:Shorts?)\b",
            r"for YouTube Shorts (9:16 aspect ratio, 1080x1920)",
        ),
        (
            r"\b(?:for\s+)?(?:YouTube|YT)\s+(?:videos?)\b",
            r"for YouTube videos (16:9 aspect ratio, 1920x1080)",
        ),
        (
            r"\b(?:for\s+)?(?:Twitter|X)\s+(?:videos?)\b",
            r"for Twitter videos (16:9 aspect ratio, 1920x1080)",
        ),
        (
            r"\b(?:for\s+)?(?:Facebook|FB)\s+(?:videos?)\b",
            r"for Facebook videos (16:9 aspect ratio, 1920x1080)",
        ),
        # Quality patterns
        (r"\b(?:high|good|better)\s+quality\b", r"high quality (lower CRF value)"),
        (
            r"\b(?:low|small|compressed)\s+(?:file\s+)?size\b",
            r"small file size (higher CRF value)",
        ),
        (r"\b(?:compress|reduce\s+size)\b", r"compress for smaller file size"),
        # Audio patterns
        (r"\b(?:remove|delete|strip)\s+audio\b", r"remove audio track"),
        (r"\b(?:extract|get)\s+audio\b", r"extract audio to separate file"),
        (r"\b(?:mute|silence)\b", r"remove audio track"),
        # Video patterns
        (
            r"\b(?:trim|cut)\s+(?:from|at)\s+(\d+(?:\.\d+)?)\s+(?:to|until)\s+(\d+(?:\.\d+)?)\b",
            r"trim from \1 seconds to \2 seconds",
        ),
        (
            r"\b(?:trim|cut)\s+(?:from|at)\s+(\d+:\d+:\d+(?:\.\d+)?)\s+(?:to|until)\s+(\d+:\d+:\d+(?:\.\d+)?)\b",
            r"trim from \1 to \2",
        ),
        (r"\b(?:speed\s+up|fast|faster)\b", r"increase playback speed"),
        (r"\b(?:slow\s+down|slow|slower)\b", r"decrease playback speed"),
        # Subtitle patterns
        (
            r"\b(?:add|burn|embed)\s+(?:captions?|subtitles?)\b",
            r"burn in subtitles",
        ),
        (
            r"\b(?:hardcode|hard\s+code)\s+(?:captions?|subtitles?)\b",
            r"burn in subtitles",
        ),
        (r"\b(?:soft\s+)?subtitles?\b", r"subtitles"),
        # Format patterns - video formats
        (
            r"\b(?:convert\s+to|save\s+as)\s+(mp4|avi|mov|mkv|webm)\b",
            r"convert to \1 format",
        ),
        # Format patterns - audio formats (extract audio or convert audio)
        (
            r"\b(?:convert\s+to|save\s+as|extract\s+to|to)\s+(mp3|wav|aac|flac|ogg|m4a)\b",
            r"extract audio to \1 format",
        ),
        # Direct audio extraction patterns
        (
            r"\b(?:extract|get|rip)\s+(?:audio\s+)?(?:to\s+)?(mp3|wav|aac|flac|ogg|m4a)\b",
            r"extract audio to \1 format",
        ),
        # Convert between audio formats
        (
            r"\bconvert\s+(?:audio\s+)?(?:to\s+)?(mp3|wav|aac|flac|ogg|m4a)\b",
            r"convert audio to \1 format",
        ),
        # Common shortcuts
        (
            r"\b(?:make\s+it\s+)?vertical\b",
            r"convert to 9:16 aspect ratio (vertical)",
        ),
        (
            r"\b(?:make\s+it\s+)?horizontal\b",
            r"convert to 16:9 aspect ratio (horizontal)",
        ),
        (r"\b(?:make\s+it\s+)?square\b", r"convert to 1:1 aspect ratio (square)"),
        (r"\b(?:crop|fill)\s+(?:to\s+)?(\d+:\d+)\b", r"crop to \1 aspect ratio"),
        (r"\b(?:pad|letterbox)\s+(?:to\s+)?(\d+:\d+)\b", r"pad to \1 aspect ratio"),
        # Duration patterns
        (
            r"\b(\d+)\s+(?:second|sec)s?\s+(?:animated\s+)?gif\b",
            r"\1 second duration animated gif",
        ),
        (
            r"\b(\d+)\s+(?:second|sec)s?\s+(?:long\s+)?(?:video|clip)\b",
            r"\1 second duration video",
        ),
        (
            r"\b(\d+)\s+(?:second|sec)s?\s+(?:duration|length)\b",
            r"\1 second duration",
        ),
        (
            r"\b(?:for|with)\s+(\d+)\s+(?:second|sec)s?\b",
            r"with \1 second duration",
        ),
        (r"\b(\d+)s\s+(?:animated\s+)?gif\b", r"\1 second duration animated gif"),
        (r"\b(\d+)s\s+(?:long\s+)?(?:video|clip)\b", r"\1 second duration video"),
    ]

    # File extension patterns for better context
    _FILE_EXTENSIONS: Final[dict[str, list[str]]] = {
        "video": [".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".m4v"],
        "audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma"],
        "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"],
        "subtitle": [".srt", ".ass", ".ssa", ".vtt", ".sub"],
    }

    # Format categories for conversion detection
    _VIDEO_FORMATS: Final[set[str]] = {"mp4", "avi", "mov", "mkv", "webm"}
    _AUDIO_FORMATS: Final[set[str]] = {"mp3", "wav", "aac", "flac", "ogg", "m4a"}
    _IMAGE_FORMATS: Final[set[str]] = {"png", "jpg", "jpeg", "gif"}

    # Term normalization mappings
    _TERM_REPLACEMENTS: Final[dict[str, str]] = {
        "vid": "video",
        "aud": "audio",
        "sub": "subtitle",
        "cap": "caption",
        "res": "resolution",
        "fps": "frame rate",
        "bitrate": "bit rate",
        "codec": "encoding format",
    }

    # Vague terms that need improvement
    _VAGUE_TERMS: Final[list[str]] = [
        "better",
        "good",
        "nice",
        "proper",
        "correct",
        "right",
    ]

    def __init__(self) -> None:
        """Initialize the prompt enhancer."""

    def enhance_prompt(self, prompt: str, context: dict[str, Any]) -> str:
        """Enhance a user prompt to improve LLM understanding."""
        enhanced = prompt.strip()

        enhanced = self._apply_pattern_replacements(enhanced)
        enhanced = self._add_context_enhancements(enhanced, context)
        enhanced = self._add_missing_details(enhanced)
        enhanced = self._normalize_terms(enhanced)

        return enhanced.strip()

    def suggest_improvements(self, prompt: str) -> list[str]:
        """Suggest improvements for a given prompt."""
        suggestions = []

        suggestions.extend(self._check_vague_terms(prompt))
        suggestions.extend(self._check_missing_format_specs(prompt))
        suggestions.extend(self._check_missing_quality_specs(prompt))
        suggestions.extend(self._check_missing_aspect_ratio(prompt))

        return suggestions

    def _apply_pattern_replacements(self, prompt: str) -> str:
        """Apply pattern replacements in order of specificity."""
        enhanced = prompt
        for pattern, replacement in self._ENHANCEMENT_PATTERNS:
            enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
        return enhanced

    def _add_context_enhancements(self, prompt: str, context: dict[str, Any]) -> str:
        """Add context-aware enhancements based on available files."""
        enhancements = []

        target_format = self._detect_target_format(prompt)
        if target_format:
            input_type = self._detect_input_type(prompt, context)
            if input_type and target_format:
                conversion_type = self._get_conversion_type(input_type, target_format)
                if conversion_type:
                    enhancements.append(f"target format: {target_format} ({conversion_type})")

        mentioned_files = self._find_mentioned_files(prompt, context)
        if mentioned_files:
            enhancements.extend(self._format_mentioned_files(mentioned_files))
        else:
            enhancements.extend(self._add_general_file_context(prompt, context))

        return self._append_enhancements(prompt, enhancements)

    def _find_mentioned_files(self, prompt: str, context: dict[str, Any]) -> list[str]:
        """Find files specifically mentioned in the prompt."""
        mentioned_files = []
        for file_type in ["videos", "audios", "images", "subtitle_files"]:
            if context.get(file_type):
                for file_path in context[file_type]:
                    filename = Path(file_path).name
                    if filename in prompt:
                        mentioned_files.append(file_path)
        return mentioned_files

    def _format_mentioned_files(self, mentioned_files: list[str]) -> list[str]:
        """Format mentioned files for enhancement output."""
        if len(mentioned_files) == 1:
            return [f"specifically using file: {mentioned_files[0]}"]
        file_names = [Path(f).name for f in mentioned_files]
        return [f"specifically using files: {', '.join(file_names)}"]

    def _add_general_file_context(self, prompt: str, context: dict[str, Any]) -> list[str]:
        """Add general file context when no specific files are mentioned."""
        enhancements = []

        # Video files context
        video_files = context.get("videos", [])
        if video_files:
            if len(video_files) == 1:
                enhancements.append(f"using video file: {video_files[0]}")
            elif len(video_files) > 1:
                enhancements.append(f"using one of {len(video_files)} available video files")

        # Subtitle files context
        subtitle_files = context.get("subtitle_files", [])
        if subtitle_files and ("subtitle" in prompt.lower() or "caption" in prompt.lower()):
            if len(subtitle_files) == 1:
                enhancements.append(f"using subtitle file: {subtitle_files[0]}")
            elif len(subtitle_files) > 1:
                enhancements.append(f"using one of {len(subtitle_files)} available subtitle files")

        # Audio files context
        audio_files = context.get("audios", [])
        if audio_files and "audio" in prompt.lower():
            enhancements.append(f"using one of {len(audio_files)} available audio files")

        return enhancements

    def _append_enhancements(self, prompt: str, enhancements: list[str]) -> str:
        """Append enhancements to the prompt."""
        if enhancements:
            return f"{prompt} ({', '.join(enhancements)})"
        return prompt

    def _add_missing_details(self, prompt: str) -> str:
        """Add missing technical details that would help the LLM."""
        details = []

        details.extend(self._suggest_resolution_details(prompt))
        details.extend(self._suggest_quality_details(prompt))
        details.extend(self._suggest_codec_details(prompt))

        return self._append_enhancements(prompt, details)

    def _suggest_resolution_details(self, prompt: str) -> list[str]:
        """Suggest resolution when aspect ratio is mentioned but no resolution specified."""
        details = []
        if re.search(r"\b\d+:\d+\s+aspect\s+ratio\b", prompt, re.IGNORECASE):
            if "9:16" in prompt and "resolution" not in prompt.lower():
                details.append("suggest 1080x1920 resolution")
            elif "16:9" in prompt and "resolution" not in prompt.lower():
                details.append("suggest 1920x1080 resolution")
            elif "1:1" in prompt and "resolution" not in prompt.lower():
                details.append("suggest 1080x1080 resolution")
        return details

    def _suggest_quality_details(self, prompt: str) -> list[str]:
        """Suggest CRF values when quality is mentioned but no specific settings."""
        details = []
        if "quality" in prompt.lower() and "crf" not in prompt.lower():
            if "high" in prompt.lower():
                details.append("use CRF 18-23 for high quality")
            elif "low" in prompt.lower() or "small" in prompt.lower():
                details.append("use CRF 28-32 for smaller file size")
        return details

    def _suggest_codec_details(self, prompt: str) -> list[str]:
        """Suggest codec when format conversion is mentioned but no codec specified."""
        details = []
        if any(ext in prompt.lower() for ext in [".mp4", ".avi", ".mov", ".mkv"]) and "codec" not in prompt.lower():
            details.append("use appropriate codec for target format")
        return details

    def _normalize_terms(self, prompt: str) -> str:
        """Normalize common terms for consistency."""
        prompt = self._normalize_aspect_ratios(prompt)
        prompt = self._normalize_resolutions(prompt)
        return self._expand_abbreviations(prompt)

    def _normalize_aspect_ratios(self, prompt: str) -> str:
        """Normalize aspect ratio formatting."""
        return re.sub(r"\b(\d+)\s*:\s*(\d+)\b", r"\1:\2", prompt)

    def _normalize_resolutions(self, prompt: str) -> str:
        """Normalize resolution formatting."""
        return re.sub(r"\b(\d{3,4})\s*[xX]\s*(\d{3,4})\b", r"\1x\2", prompt)

    def _expand_abbreviations(self, prompt: str) -> str:
        """Expand common abbreviations to full terms."""
        for abbrev, full in self._TERM_REPLACEMENTS.items():
            prompt = re.sub(rf"\b{abbrev}\b", full, prompt, flags=re.IGNORECASE)
        return prompt

    def _detect_target_format(self, prompt: str) -> str | None:
        """Detect target format from prompt."""
        format_pattern = (
            r"\b(?:to\s+|convert\s+to\s+|save\s+as\s+|extract\s+to\s+)\.?"
            r"(mp4|avi|mov|mkv|webm|mp3|wav|aac|flac|ogg|m4a|png|jpg|jpeg|gif)\b"
        )
        match = re.search(format_pattern, prompt.lower())
        if match:
            return match.group(1)

        format_pattern2 = r"\b(mp4|avi|mov|mkv|webm|mp3|wav|aac|flac|ogg|m4a|png|jpg|jpeg|gif)\s+format\b"
        match2 = re.search(format_pattern2, prompt.lower())
        if match2:
            return match2.group(1)

        return None

    def _detect_input_type(self, prompt: str, context: dict[str, Any]) -> str | None:
        """Detect input file type from context."""
        for file_type in ["videos", "audios", "images"]:
            if context.get(file_type):
                for file_path in context[file_type]:
                    filename = Path(file_path).name
                    if filename in prompt:
                        return file_type.rstrip("s")

        if context.get("videos") and not context.get("audios") and not context.get("images"):
            return "video"
        if context.get("audios") and not context.get("videos") and not context.get("images"):
            return "audio"
        if context.get("images") and not context.get("videos") and not context.get("audios"):
            return "image"

        return None

    def _get_conversion_type(self, input_type: str, target_format: str) -> str | None:
        """Determine the type of conversion being requested."""
        target_is_video = target_format in self._VIDEO_FORMATS
        target_is_audio = target_format in self._AUDIO_FORMATS
        target_is_image = target_format in self._IMAGE_FORMATS

        if input_type == "video" and target_is_audio:
            return "extract audio"
        if input_type == "video" and target_is_video:
            return "transcode video"
        if input_type == "audio" and target_is_audio:
            return "convert audio"
        if input_type == "audio" and target_is_video:
            return "create video from audio"
        if input_type == "image" and target_is_video:
            return "create video from image"
        if input_type == "image" and target_is_image:
            return "convert image"

        return None

    def _check_vague_terms(self, prompt: str) -> list[str]:
        """Check for vague terms that lack specificity."""
        return [
            f"Replace '{term}' with specific requirements (e.g., 'high quality', 'small file size')"
            for term in self._VAGUE_TERMS
            if term in prompt.lower()
        ]

    def _check_missing_format_specs(self, prompt: str) -> list[str]:
        """Check for missing file format specifications."""
        suggestions = []
        if "file" in prompt.lower() and not re.search(r"\.[a-zA-Z0-9]+", prompt):
            suggestions.append("Specify file format (e.g., .mp4, .avi)")
        return suggestions

    def _check_missing_quality_specs(self, prompt: str) -> list[str]:
        """Check for missing quality specifications when quality is mentioned."""
        suggestions = []
        if "quality" in prompt.lower() and "crf" not in prompt.lower():
            suggestions.append("Specify quality level (e.g., 'high quality', 'small file size')")
        return suggestions

    def _check_missing_aspect_ratio(self, prompt: str) -> list[str]:
        """Check for missing aspect ratio when resizing operations are mentioned."""
        suggestions = []
        if any(word in prompt.lower() for word in ["resize", "scale", "convert"]) and not re.search(r"\d+:\d+", prompt):
            suggestions.append("Specify target aspect ratio (e.g., '16:9', '9:16', '1:1')")
        return suggestions


# Module-level convenience functions for backward compatibility
def refine_input(prompt: str, context: dict[str, Any]) -> str:
    """Convenience function to enhance a user prompt."""
    enhancer = PromptEnhancer()
    return enhancer.enhance_prompt(prompt, context)


def get_prompt_suggestions(prompt: str) -> list[str]:
    """Get suggestions for improving a user prompt."""
    enhancer = PromptEnhancer()
    return enhancer.suggest_improvements(prompt)
