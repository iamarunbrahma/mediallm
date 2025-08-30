#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import glob
import re
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Final

if TYPE_CHECKING:
    from collections.abc import Iterable


class MediaFileHandler:
    """Handles media file operations with security validation."""

    # Class constants
    _MAX_GLOB_RESULTS: Final[int] = 1000
    _MAX_FILENAME_LENGTH: Final[int] = 255
    _MAX_INPUT_LENGTH: Final[int] = 1000

    # Security patterns
    _DANGEROUS_SEQUENCES: Final[list[str]] = [
        "../",
        "..\\",
        "//",
        "\\\\",
        "*" * 10,
        "{" * 5,
    ]

    _DANGEROUS_ROOTS: Final[list[str]] = [
        "/etc",
        "/proc",
        "/sys",
        "/dev",
        "/boot",
        "c:\\windows",
        "c:\\system32",
        "c:\\program files",
        "~/.ssh",
        "~/.aws",
        "~/.config",
    ]

    _DANGEROUS_PATTERNS: Final[list[str]] = [
        "/etc",
        "/proc",
        "/sys",
        "/dev",
        "/boot",
        "C:\\Windows",
        "C:\\System32",
        "C:\\Program Files",
        "~/.ssh",
        "~/.aws",
        "~/.config",
    ]

    _RESERVED_NAMES: Final[set[str]] = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }

    _ALLOWED_FFMPEG_FLAGS: Final[set[str]] = {
        "-i",
        "-f",
        "-y",
        "-n",
        "-c:v",
        "-vcodec",
        "-codec:v",
        "-vf",
        "-filter:v",
        "-aspect",
        "-pix_fmt",
        "-r",
        "-s",
        "-vframes",
        "-vn",
        "-frame_pts",
        "-frame_pkt_pts",
        "-c:a",
        "-acodec",
        "-codec:a",
        "-af",
        "-filter:a",
        "-ar",
        "-ac",
        "-ab",
        "-aq",
        "-an",
        "-c",
        "-codec",
        "-ss",
        "-t",
        "-to",
        "-itsoffset",
        "-b:v",
        "-b:a",
        "-b",
        "-crf",
        "-qp",
        "-q:v",
        "-q:a",
        "-maxrate",
        "-bufsize",
        "-minrate",
        "-filter_complex",
        "-lavfi",
        "-map",
        "-map_metadata",
        "-map_chapters",
        "-metadata",
        "-disposition",
        "-movflags",
        "-preset",
        "-tune",
        "-profile:v",
        "-level",
        "-hwaccel",
        "-hwaccel_device",
    }

    @classmethod
    def expand_globs(cls, patterns: Iterable[str], allowed_dirs: list[Path] | None = None) -> list[Path]:
        """Expand glob patterns safely with path validation."""
        if allowed_dirs is None:
            allowed_dirs = [Path.cwd()]

        paths: list[Path] = []

        for pattern in patterns:
            if not cls._is_safe_glob_pattern(pattern):
                continue

            try:
                matches = glob.glob(pattern, recursive=True)
                if len(matches) > cls._MAX_GLOB_RESULTS:
                    matches = matches[: cls._MAX_GLOB_RESULTS]

                for match in matches:
                    path_obj = Path(match).resolve()
                    if cls.is_safe_path(path_obj, allowed_dirs):
                        paths.append(path_obj)

            except (OSError, ValueError):
                continue

        return cls._remove_duplicates(paths)

    @classmethod
    def is_safe_path(cls, path: object, allowed_dirs: list[Path] | None = None) -> bool:
        """Validate path is safe and within allowed directories."""
        try:
            if path is None:
                return False

            path_obj = cls._convert_to_path(path)
            if not path_obj:
                return False

            resolved_path = cls._resolve_path_safely(path_obj)
            if not resolved_path:
                return False

            if cls._is_dangerous_path(path_obj, resolved_path):
                return False

            return cls._is_within_allowed_dirs(resolved_path, allowed_dirs)

        except Exception:
            return False

    @classmethod
    def ensure_parent_dir(cls, path: Path) -> None:
        """Ensure parent directory exists, creating it if necessary."""
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def quote_path(cls, path: Path) -> str:
        """Quote path for safe display in preview text."""
        return str(path)

    @classmethod
    def most_recent_file(cls, paths: Iterable[Path]) -> Path | None:
        """Find the most recently modified file from a collection."""
        latest: tuple[float, Path] | None = None
        for p in paths:
            try:
                mtime = p.stat().st_mtime
            except OSError:
                continue
            if latest is None or mtime > latest[0]:
                latest = (mtime, p)
        return latest[1] if latest else None

    @classmethod
    def sanitize_filename(cls, filename: str, max_length: int | None = None) -> str:
        """Sanitize filename to prevent security issues."""
        if not filename or not isinstance(filename, str):
            return "sanitized_file"

        max_length = max_length or cls._MAX_FILENAME_LENGTH

        # Remove or replace dangerous characters
        sanitized = re.sub(r"[^a-zA-Z0-9\s\._-]", "_", filename)

        # Prevent multiple consecutive dots
        sanitized = re.sub(r"\.{2,}", ".", sanitized)

        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip(". ")

        # Check for reserved names
        sanitized = cls._handle_reserved_names(sanitized)

        # Truncate if too long
        sanitized = cls._truncate_filename(sanitized, max_length)

        return sanitized or "sanitized_file"

    @classmethod
    def validate_ffmpeg_command(cls, cmd: list[str]) -> bool:
        """Validate ffmpeg command arguments for security."""
        if not cmd or not isinstance(cmd, list) or cmd[0] != "ffmpeg":
            return False

        if cls._contains_dangerous_patterns(cmd):
            return False

        if cls._contains_dangerous_ampersand(cmd):
            return False

        return cls._validate_flags_and_paths(cmd)

    @classmethod
    def sanitize_user_input(cls, user_input: str, max_length: int | None = None) -> str:
        """Sanitize user input to prevent injection attacks."""
        if not user_input or not isinstance(user_input, str):
            return ""

        max_length = max_length or cls._MAX_INPUT_LENGTH

        if len(user_input) > max_length:
            user_input = user_input[:max_length]

        # Remove control characters
        sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", user_input)

        # Remove dangerous characters
        sanitized = cls._remove_dangerous_chars(sanitized)

        # Remove dangerous patterns
        sanitized = cls._remove_dangerous_patterns(sanitized)

        # Normalize whitespace
        return " ".join(sanitized.split())

    @classmethod
    def _is_safe_glob_pattern(cls, pattern: str) -> bool:
        """Validate glob pattern is safe to use."""
        if not pattern or not isinstance(pattern, str):
            return False

        pattern_lower = pattern.lower()

        for dangerous in cls._DANGEROUS_SEQUENCES:
            if dangerous in pattern_lower:
                return False

        return all(not pattern_lower.startswith(root.lower()) for root in cls._DANGEROUS_ROOTS)

    @classmethod
    def _remove_duplicates(cls, paths: list[Path]) -> list[Path]:
        """Remove duplicates while preserving order."""
        unique: list[Path] = []
        seen = set()
        for p in paths:
            if p not in seen:
                seen.add(p)
                unique.append(p)
        return unique

    @classmethod
    def _convert_to_path(cls, path: object) -> Path | None:
        """Convert object to Path, validating it's not empty."""
        if not isinstance(path, Path):
            path_str_check = str(path)
            if not path_str_check or not path_str_check.strip():
                return None
            return Path(path_str_check)
        return path

    @classmethod
    def _resolve_path_safely(cls, path_obj: Path) -> Path | None:
        """Safely resolve path to absolute path."""
        try:
            return path_obj.resolve()
        except (OSError, RuntimeError):
            return None

    @classmethod
    def _is_dangerous_path(cls, path_obj: Path, resolved_path: Path) -> bool:
        """Check if path contains dangerous patterns."""
        path_str = str(resolved_path)
        original_str = str(path_obj)

        if not path_str.strip() or not original_str.strip():
            return True

        if path_str in {"/", "\\", "C:\\", "C:/", "C:", "/root", "/home"}:
            return True

        if len(original_str.strip()) <= 3 and any(c in original_str for c in ["/", "\\"]):
            return True

        path_parts = path_obj.parts
        if ".." in path_parts or any("." * 3 in part for part in path_parts):
            return True

        path_lower = path_str.lower()
        for pattern in cls._DANGEROUS_PATTERNS:
            try:
                if path_str.startswith(pattern) or Path(pattern).resolve() in resolved_path.parents:
                    return True
            except (OSError, ValueError):
                if path_lower.startswith(pattern.lower()):
                    return True

        windows_indicators = ["windows", "system32", "program files"]
        return any(indicator in path_lower for indicator in windows_indicators)

    @classmethod
    def _is_within_allowed_dirs(cls, resolved_path: Path, allowed_dirs: list[Path] | None) -> bool:
        """Check if path is within allowed directories."""
        if allowed_dirs is None:
            allowed_dirs = [Path.cwd()]

        for allowed_dir in allowed_dirs:
            try:
                resolved_allowed = allowed_dir.resolve()
                if resolved_path == resolved_allowed or resolved_path.is_relative_to(resolved_allowed):
                    return True
            except (ValueError, OSError):
                continue

        return False

    @classmethod
    def _handle_reserved_names(cls, sanitized: str) -> str:
        """Handle Windows reserved names."""
        name_without_ext = sanitized.rsplit(".", 1)[0].upper()
        if name_without_ext in cls._RESERVED_NAMES:
            return f"safe_{sanitized}"
        return sanitized

    @classmethod
    def _truncate_filename(cls, sanitized: str, max_length: int) -> str:
        """Truncate filename if too long while preserving extension."""
        if len(sanitized) > max_length:
            name, ext = sanitized.rsplit(".", 1) if "." in sanitized else (sanitized, "")
            max_name_length = max_length - len(ext) - 1 if ext else max_length
            return name[:max_name_length] + ("." + ext if ext else "")
        return sanitized

    @classmethod
    def _contains_dangerous_patterns(cls, cmd: list[str]) -> bool:
        """Check for dangerous patterns in command."""
        dangerous_patterns = [
            "|",
            "&&",
            "||",
            "$",
            "`",
            "$(",
            "${",
            ">",
            "<",
            ">>",
            "<<",
            "\n",
            "\r",
        ]

        for i, arg in enumerate(cmd):
            is_filter_value = cls._is_filter_value(cmd, i)
            patterns_to_check = (
                [p for p in dangerous_patterns if p != ";"] if is_filter_value else [*dangerous_patterns, ";"]
            )

            if any(pattern in arg for pattern in patterns_to_check):
                return True
        return False

    @classmethod
    def _is_filter_value(cls, cmd: list[str], index: int) -> bool:
        """Check if current argument is a filter value."""
        return (
            index > 0
            and cmd[index - 1].startswith("-")
            and cmd[index - 1] in ["-vf", "-filter:v", "-af", "-filter:a", "-filter_complex", "-lavfi"]
        )

    @classmethod
    def _contains_dangerous_ampersand(cls, cmd: list[str]) -> bool:
        """Check for dangerous ampersand usage."""
        cmd_str = " ".join(cmd)
        return bool(re.search(r"(?<!H)\b&\b(?!H)", cmd_str))

    @classmethod
    def _validate_flags_and_paths(cls, cmd: list[str]) -> bool:
        """Validate flags against allowlist and paths for safety."""
        i = 1  # Skip 'ffmpeg'
        while i < len(cmd):
            arg = cmd[i]

            if arg.startswith("-"):
                if arg not in cls._ALLOWED_FFMPEG_FLAGS:
                    return False
                if i + 1 < len(cmd) and not cmd[i + 1].startswith("-"):
                    i += 1  # Skip the value
            elif not cls.is_safe_path(arg):
                return False
            i += 1

        return True

    @classmethod
    def _remove_dangerous_chars(cls, sanitized: str) -> str:
        """Remove dangerous shell characters."""
        dangerous_chars = [";", "|", "&", "$", "`", "<", ">", "\x00"]
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, " ")
        return sanitized

    @classmethod
    def _remove_dangerous_patterns(cls, sanitized: str) -> str:
        """Remove dangerous command patterns."""
        dangerous_patterns = [
            r"\brm\s+",
            r"\bmv\s+",
            r"\bcp\s+",
            r"\bchmod\s+",
            r"\bsudo\s+",
            r"\bsu\s+",
            r"\bcurl\s+",
            r"\bwget\s+",
            r"\bsh\s+",
            r"\bbash\s+",
            r"\beval\s+",
            r"\bexec\s+",
        ]

        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, " ", sanitized, flags=re.IGNORECASE)
        return sanitized


# Module-level convenience functions for backward compatibility
def expand_globs(patterns: Iterable[str], allowed_dirs: list[Path] | None = None) -> list[Path]:
    """Expand glob patterns safely with path validation."""
    return MediaFileHandler.expand_globs(patterns, allowed_dirs)


def is_safe_path(path: object, allowed_dirs: list[Path] | None = None) -> bool:
    """Validate path is safe and within allowed directories."""
    return MediaFileHandler.is_safe_path(path, allowed_dirs)


def ensure_parent_dir(path: Path) -> None:
    """Ensure parent directory exists, creating it if necessary."""
    return MediaFileHandler.ensure_parent_dir(path)


def quote_path(path: Path) -> str:
    """Quote path for safe display in preview text."""
    return MediaFileHandler.quote_path(path)


def most_recent_file(paths: Iterable[Path]) -> Path | None:
    """Find the most recently modified file from a collection."""
    return MediaFileHandler.most_recent_file(paths)


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize filename to prevent security issues."""
    return MediaFileHandler.sanitize_filename(filename, max_length)


def validate_ffmpeg_command(cmd: list[str]) -> bool:
    """Validate ffmpeg command arguments for security."""
    return MediaFileHandler.validate_ffmpeg_command(cmd)


def sanitize_user_input(user_input: str, max_length: int = 1000) -> str:
    """Sanitize user input to prevent injection attacks."""
    return MediaFileHandler.sanitize_user_input(user_input, max_length)
