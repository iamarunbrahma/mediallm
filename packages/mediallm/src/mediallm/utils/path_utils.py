#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

from pathlib import Path
from typing import Final


class PathUtils:
    """Centralized path resolution and validation utilities."""

    # Dangerous file patterns to reject
    DANGEROUS_PATTERNS: Final[list[str]] = [
        "..",  # Path traversal
        "://",  # URL schemes
        "<",
        ">",  # HTML/XML tags
    ]

    @classmethod
    def resolve_file_path(cls, filename: str) -> Path | None:
        """Resolve a file path, checking current directory and common locations."""
        # Handle absolute paths
        if Path(filename).is_absolute():
            path = Path(filename)
            return path if path.exists() else None

        # Check current directory first
        current_path = Path(filename)
        if current_path.exists():
            return current_path.resolve()

        # Check current working directory
        cwd_path = Path.cwd() / filename
        if cwd_path.exists():
            return cwd_path.resolve()

        return None

    @classmethod
    def is_safe_path(cls, path: Path | str) -> bool:
        """Check if a path is safe (no dangerous patterns)."""
        path_str = str(path)
        return not any(pattern in path_str for pattern in cls.DANGEROUS_PATTERNS)

    @classmethod
    def validate_file_exists(cls, file_path: Path | str) -> tuple[bool, str | None]:
        """Validate that a file exists and is safe."""
        if isinstance(file_path, str):
            file_path = Path(file_path)

        if not cls.is_safe_path(file_path):
            return False, "File path contains dangerous patterns"

        if not file_path.exists():
            return False, f"File does not exist: {file_path}"

        if not file_path.is_file():
            return False, f"Path is not a file: {file_path}"

        return True, None

    @classmethod
    def ensure_path_object(cls, path: Path | str) -> Path:
        """Ensure the input is a Path object."""
        return Path(path) if isinstance(path, str) else path


# Convenience functions for backward compatibility
def resolve_file_path(filename: str) -> Path | None:
    """Resolve a file path."""
    return PathUtils.resolve_file_path(filename)


def is_safe_path(path: Path | str) -> bool:
    """Check if a path is safe."""
    return PathUtils.is_safe_path(path)


def validate_file_exists(file_path: Path | str) -> tuple[bool, str | None]:
    """Validate that a file exists and is safe."""
    return PathUtils.validate_file_exists(file_path)


def ensure_path_object(path: Path | str) -> Path:
    """Ensure the input is a Path object."""
    return PathUtils.ensure_path_object(path)
