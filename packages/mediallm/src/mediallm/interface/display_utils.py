#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import logging
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Final

from rich.console import Console
from rich.text import Text

from ..processing.media_file_handler import most_recent_file
from ..utils.table_factory import TableFactory
from ..utils.version import __version__

if TYPE_CHECKING:
    from rich.table import Table

    from ..utils.config import AppConfig

console = Console()
logger = logging.getLogger(__name__)


class DisplayConstants:
    """Constants for display utilities."""

    ASCII_LINES: Final[list[str]] = [
        "███╗   ███╗███████╗██████╗ ██╗ █████╗ ██╗     ██╗     ███╗   ███╗",
        "████╗ ████║██╔════╝██╔══██╗██║██╔══██╗██║     ██║     ████╗ ████║",
        "██╔████╔██║█████╗  ██║  ██║██║███████║██║     ██║     ██╔████╔██║",
        "██║╚██╔╝██║██╔══╝  ██║  ██║██║██╔══██║██║     ██║     ██║╚██╔╝██║",
        "██║ ╚═╝ ██║███████╗██████╔╝██║██║  ██║███████╗███████╗██║ ╚═╝ ██║",
        "╚═╝     ╚═╝╚══════╝╚═════╝ ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚═╝",
    ]

    MAX_FILES_DISPLAY: Final[int] = 5


def display_welcome_screen() -> None:
    """Display ASCII art welcome header for the interactive mode."""
    console.print()

    for line in DisplayConstants.ASCII_LINES:
        console.print(line, style="bold cyan", justify="center")

    console.print()
    _display_tagline()


def _display_tagline() -> None:
    """Display version tagline."""
    tagline = Text()
    tagline.append(f"v{__version__}", style="bold green")
    tagline.append(" • Convert media files using natural language", style="dim")
    console.print(tagline, justify="center")


def display_system_info() -> None:
    """Display compact system information."""
    info_text = Text()
    info_text.append("System: ", style="bold blue")
    info_text.append(
        f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} • ",
        style="white",
    )
    info_text.append(f"{platform.platform()} • ", style="white")
    info_text.append(f"CLI v{__version__} • ", style="white")
    info_text.append(datetime.now().strftime("%H:%M:%S"), style="white")

    console.print(info_text)


def display_context_info(context: dict, output_dir: Path | None = None) -> None:
    """Display context information in a beautiful table format."""
    if not context:
        return

    table = _create_context_table()
    _populate_context_table(table, context)

    if table.row_count > 0:
        console.print(table)

    if output_dir:
        _display_output_directory(output_dir)


def _create_context_table() -> Table:
    """Create context information table."""
    table = TableFactory.create_media_table("Available Media Files")
    table.add_column("Type", style="bold cyan", justify="center")
    table.add_column("Count", style="bold green", justify="center")
    table.add_column("Files", style="white")
    return table


def _populate_context_table(table: Table, context: dict) -> None:
    """Populate context table with media file information."""
    media_types = [
        ("Videos", "videos"),
        ("Audio", "audios"),
        ("Images", "images"),
    ]

    for display_name, key in media_types:
        files = context.get(key, [])
        if files:
            file_list = _format_file_list(files)
            table.add_row(display_name, str(len(files)), file_list)

    # Show most recent files for each media type
    media_recent = [
        ("Recent Video", "videos"),
        ("Recent Audio", "audios"),
        ("Recent Image", "images"),
    ]

    for display_name, key in media_recent:
        files = context.get(key, [])
        if files:
            most_recent = most_recent_file([Path(f) for f in files])
            if most_recent:
                table.add_row(display_name, "1", f"• {Path(most_recent).name}")


def _format_file_list(files: list) -> str:
    """Format file list for display with truncation."""
    file_names = [f"• {Path(f).name}" for f in files[: DisplayConstants.MAX_FILES_DISPLAY]]

    if len(files) > DisplayConstants.MAX_FILES_DISPLAY:
        file_names.append(f"• ... and {len(files) - DisplayConstants.MAX_FILES_DISPLAY} more")

    return "\n".join(file_names)


def _display_output_directory(output_dir: Path) -> None:
    """Display output directory information."""
    output_text = Text()
    output_text.append("Output Directory: ", style="bold blue")
    output_text.append(str(output_dir), style="white")
    console.print(output_text)


def display_completion_summary(output_dir: Path | None = None) -> None:
    """Display a summary of available media files after completion."""
    if not output_dir:
        return

    try:
        output_context = _scan_output_directory(output_dir)
        if not output_context:
            return

        _display_completion_table(output_context)

    except (OSError, PermissionError, FileNotFoundError) as e:
        logger.debug(f"Could not display completion summary: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error in completion summary: {e}")


def _scan_output_directory(output_dir: Path) -> dict:
    """Scan output directory for media files."""
    from ..analysis.workspace_scanner import discover_media

    return discover_media(cwd=output_dir, show_summary=False)


def _display_completion_table(output_context: dict) -> None:
    """Display completion summary table."""
    completion_table = _create_completion_table()
    _populate_completion_table(completion_table, output_context)

    if completion_table.row_count > 0:
        console.print(completion_table)
        console.print()
    else:
        console.print("[green]✅ Command completed successfully[/green]")
        console.print()


def _create_completion_table() -> Table:
    """Create completion summary table."""
    table = TableFactory.create_media_table("✅ Command Completed - Generated Files")
    table.add_column("Type", style="bold cyan", justify="center")
    table.add_column("Count", style="bold green", justify="center")
    table.add_column("Files", style="white")
    return table


def _populate_completion_table(table: Table, output_context: dict) -> None:
    """Populate completion table with generated files."""
    media_types = [
        ("Videos", "videos"),
        ("Audio", "audios"),
        ("Images", "images"),
    ]

    for display_name, key in media_types:
        files = output_context.get(key, [])
        if files and isinstance(files, list):
            file_list = _format_file_list([str(f) for f in files])
            table.add_row(display_name, str(len(files)), file_list)


def display_config_status(cfg: AppConfig) -> None:
    """Display compact configuration status."""
    config_text = Text()
    config_text.append("Configuration: ", style="bold yellow")
    config_text.append(f"model={cfg.model_name} • ", style="white")
    config_text.append(f"host={cfg.ollama_host} • ", style="white")
    config_text.append(f"timeout={cfg.timeout_seconds}s • ", style="white")
    config_text.append(f"dry_run={'on' if cfg.dry_run else 'off'} • ", style="white")

    dir_count = len(cfg.allowed_directories) if cfg.allowed_directories else 1
    config_text.append(f"directories={dir_count}", style="white")

    console.print(config_text)
