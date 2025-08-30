#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import json
import logging
import shutil
import subprocess  # nosec B404: subprocess is used safely with explicit args and no shell
from pathlib import Path
from typing import Any
from typing import Final

from rich.console import Console
from rich.table import Table

from ..constants.media_formats import MEDIA_EXTENSIONS
from ..utils.format_utils import FormatUtils
from ..utils.table_factory import TableFactory

logger = logging.getLogger(__name__)


class MediaDiscovery:
    """Handles media file discovery and analysis with rich display output."""

    # Use centralized media extensions
    _MEDIA_EXTS: Final[dict[str, set[str]]] = MEDIA_EXTENSIONS

    def __init__(self, console: Console | None = None) -> None:
        """Initialize MediaDiscovery."""
        self.console = console or Console()

    @classmethod
    def format_file_size(cls, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        return FormatUtils.format_file_size(size_bytes)

    @classmethod
    def format_duration(cls, seconds: float | None) -> str:
        """Format duration in human-readable format."""
        return FormatUtils.format_duration(seconds)

    @classmethod
    def extract_duration(cls, path: Path) -> float | None:
        """Extract duration of a media file using ffprobe."""
        logger.debug(f"Extracting duration from: {path}")
        ffprobe_path = shutil.which("ffprobe")
        if ffprobe_path is None:
            logger.debug("ffprobe not found in PATH")
            return None

        try:
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
            )
            data = json.loads(result.stdout)
            dur = data.get("format", {}).get("duration")
            duration = float(dur) if dur is not None else None
            logger.debug(f"Extracted duration: {duration}s from {path}")
            return duration
        except Exception as e:
            logger.debug(f"Failed to extract duration from {path}: {e}")
            return None

    def discover_media(self, cwd: Path | None = None, show_summary: bool = True) -> dict[str, Any]:
        """Scan current directory and subdirectories for media files and build context."""
        base = cwd or Path.cwd()
        logger.debug(f"Starting media discovery in: {base}")
        files = self._scan_directory(base)
        logger.debug(f"Found {len(files)} total files")
        categorized_files = self._categorize_files(files)
        context = self._build_context(base, categorized_files)
        media_count = sum(len(v) if isinstance(v, list) else 0 for v in context.values() if isinstance(v, list))
        logger.debug(f"Media discovery completed: {media_count} media files")

        if show_summary:
            self._display_scan_summary(context)
            self._display_detailed_file_info(context)

        return context

    def _scan_directory(self, base: Path) -> list[Path]:
        """Scan directory for all non-hidden files."""
        logger.debug(f"Scanning directory recursively: {base}")
        files = [
            p
            for p in base.rglob("*")
            if p.is_file() and not p.name.startswith(".") and not any(part.startswith(".") for part in p.parts)
        ]
        logger.debug(f"Directory scan found {len(files)} non-hidden files")
        return files

    def _categorize_files(self, files: list[Path]) -> dict[str, list[Path]]:
        """Categorize files by media type."""
        logger.debug(f"Categorizing {len(files)} files by media type")
        categorized = {media_type: [] for media_type in self._MEDIA_EXTS}

        for file_path in files:
            ext = file_path.suffix.lower()
            for media_type, extensions in self._MEDIA_EXTS.items():
                if ext in extensions:
                    categorized[media_type].append(file_path)
                    break

        # Log categorization results
        for media_type, file_list in categorized.items():
            if file_list:
                logger.debug(f"Found {len(file_list)} {media_type} files")

        return categorized

    def _build_context(self, base: Path, categorized_files: dict[str, list[Path]]) -> dict[str, Any]:
        """Build context dictionary with file information."""
        logger.debug("Building context from categorized files")
        info = self._build_file_info(categorized_files["video"] + categorized_files["audio"])
        logger.debug(f"Built detailed info for {len(info)} media files")

        return {
            "cwd": str(base),
            "videos": [str(p) for p in categorized_files["video"]],
            "audios": [str(p) for p in categorized_files["audio"]],
            "images": [str(p) for p in categorized_files["image"]],
            "subtitle_files": [str(p) for p in categorized_files["subtitle"]],
            "info": info,
        }

    def _build_file_info(self, files: list[Path]) -> list[dict[str, Any]]:
        """Build detailed info for video and audio files."""
        logger.debug(f"Building detailed info for {len(files)} media files")
        return [
            {
                "path": str(file_path),
                "size": file_path.stat().st_size if file_path.exists() else None,
                "duration": self.extract_duration(file_path),
            }
            for file_path in files
        ]

    def _display_scan_summary(self, context: dict[str, Any]) -> None:
        """Display a summary of the scan results using Rich."""
        table = self._create_summary_table()
        self._populate_summary_table(table, context)

        if table.row_count > 0:
            self.console.print(table)
            self.console.print()

    def _create_summary_table(self) -> Table:
        """Create summary table structure."""
        table = TableFactory.create_summary_table("Scan Summary")
        table.add_column("Category", style="bold cyan")
        table.add_column("Count", style="bold green", justify="center")
        table.add_column("Details", style="white")
        return table

    def _populate_summary_table(self, table: Table, context: dict[str, Any]) -> None:
        """Populate summary table with media file information."""
        media_types = [
            ("Videos", "videos"),
            ("Audio", "audios"),
            ("Images", "images"),
        ]

        for display_name, key in media_types:
            files = context.get(key, [])
            if files:
                total_size = self._calculate_total_size(files)
                table.add_row(
                    display_name,
                    str(len(files)),
                    f"Total size: {self.format_file_size(total_size)}",
                )

        subtitle_files = context.get("subtitle_files", [])
        if subtitle_files:
            table.add_row("Subtitles", str(len(subtitle_files)), "Ready for processing")

    def _calculate_total_size(self, file_paths: list[str]) -> int:
        """Calculate total size of files."""
        return sum(Path(file_path).stat().st_size for file_path in file_paths if Path(file_path).exists())

    def _display_detailed_file_info(self, context: dict[str, Any]) -> None:
        """Display detailed file information in a table format."""
        info = context.get("info", [])
        if not info:
            return

        table = self._create_file_info_table()
        self._populate_file_info_table(table, info)

        if table.row_count > 0:
            self.console.print(table)
            self.console.print()

    def _create_file_info_table(self) -> Table:
        """Create detailed file info table structure."""
        table = TableFactory.create_media_table("File Details")
        table.add_column("File", style="bold white")
        table.add_column("Size", style="cyan", justify="right")
        table.add_column("Duration", style="yellow", justify="center")
        table.add_column("Type", style="bold", justify="center")
        return table

    def _populate_file_info_table(self, table: Table, info: list[dict[str, Any]]) -> None:
        """Populate file info table with detailed information."""
        for file_info in info:
            path = Path(file_info["path"])
            size = file_info.get("size", 0)
            duration = file_info.get("duration")
            file_type = self._determine_file_type(path)

            table.add_row(
                path.name,
                self.format_file_size(size) if size else "Unknown",
                self.format_duration(duration),
                file_type,
            )

    def _determine_file_type(self, path: Path) -> str:
        """Determine file type based on extension."""
        ext = path.suffix.lower()
        if ext in self._MEDIA_EXTS["video"]:
            return "Video"
        if ext in self._MEDIA_EXTS["audio"]:
            return "Audio"
        return "Other"


# Module-level convenience functions for backward compatibility
_discovery = MediaDiscovery()

# Export MEDIA_EXTS for backward compatibility
MEDIA_EXTS = MediaDiscovery._MEDIA_EXTS


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    return FormatUtils.format_file_size(size_bytes)


def format_duration(seconds: float | None) -> str:
    """Format duration in human-readable format."""
    return FormatUtils.format_duration(seconds)


def extract_duration(path: Path) -> float | None:
    """Extract duration of a media file using ffprobe."""
    return MediaDiscovery.extract_duration(path)


def display_scan_summary(context: dict) -> None:
    """Display a summary of the scan results using Rich."""
    _discovery._display_scan_summary(context)


def display_detailed_file_info(context: dict) -> None:
    """Display detailed file information in a table format."""
    _discovery._display_detailed_file_info(context)


def discover_media(cwd: Path | None = None, show_summary: bool = True) -> dict[str, Any]:
    """Scan current directory and subdirectories for media files and build context."""
    return _discovery.discover_media(cwd, show_summary)
