#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

from typing import Final


class FormatUtils:
    """Centralized formatting utilities for file sizes, durations, etc."""

    _SIZE_UNITS: Final[list[tuple[str, int]]] = [
        ("GB", 1024 * 1024 * 1024),
        ("MB", 1024 * 1024),
        ("KB", 1024),
        ("B", 1),
    ]

    @classmethod
    def format_file_size(cls, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit, divisor in cls._SIZE_UNITS:
            if size_bytes >= divisor:
                if unit == "B":
                    return f"{size_bytes} {unit}"
                return f"{size_bytes / divisor:.1f} {unit}"
        return "0 B"

    @classmethod
    def format_duration(cls, duration_seconds: float | None) -> str:
        """Format duration in human-readable format (HH:MM:SS)."""
        if duration_seconds is None:
            return "Unknown"

        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        seconds = int(duration_seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"


# Convenience functions for backward compatibility
def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    return FormatUtils.format_file_size(size_bytes)


def format_duration(duration_seconds: float | None) -> str:
    """Format duration in human-readable format."""
    return FormatUtils.format_duration(duration_seconds)
