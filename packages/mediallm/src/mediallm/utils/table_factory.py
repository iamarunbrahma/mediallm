#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

from typing import Any

from rich.table import Table


class TableFactory:
    """Centralized factory for creating Rich tables with consistent styling."""

    @staticmethod
    def create_command_table(title: str) -> Table:
        """Create a table for displaying commands."""
        return Table(title=f"[bold green]{title}[/bold green]")

    @staticmethod
    def create_info_table(title: str, show_header: bool = True) -> Table:
        """Create a table for displaying information."""
        return Table(title=f"[bold blue]{title}[/bold blue]", show_header=show_header)

    @staticmethod
    def create_summary_table(title: str) -> Table:
        """Create a table for displaying summaries."""
        return Table(title=f"[bold blue]{title}[/bold blue]", show_header=False, box=None)

    @staticmethod
    def create_suggestion_table(title: str) -> Table:
        """Create a table for displaying suggestions."""
        return Table(title=f"[bold yellow]{title}[/bold yellow]")

    @staticmethod
    def create_media_table(title: str) -> Table:
        """Create a table for displaying media files."""
        return Table(title=f"[bold green]{title}[/bold green]", show_header=True)

    @staticmethod
    def create_config_table(title: str) -> Table:
        """Create a table for displaying configuration."""
        return Table(title=f"[bold green]{title}[/bold green]")

    @staticmethod
    def create_custom_table(
        title: str,
        color: str = "green",
        show_header: bool | None = True,
        box: Any = "default",
    ) -> Table:
        """Create a custom table with specified styling."""
        table_kwargs = {"title": f"[bold {color}]{title}[/bold {color}]"}

        if show_header is not None:
            table_kwargs["show_header"] = show_header

        if box != "default":
            table_kwargs["box"] = box

        return Table(**table_kwargs)


# Convenience functions for backward compatibility
def create_command_table(title: str) -> Table:
    """Create a table for displaying commands."""
    return TableFactory.create_command_table(title)


def create_info_table(title: str, show_header: bool = True) -> Table:
    """Create a table for displaying information."""
    return TableFactory.create_info_table(title, show_header)


def create_summary_table(title: str) -> Table:
    """Create a table for displaying summaries."""
    return TableFactory.create_summary_table(title)


def create_media_table(title: str) -> Table:
    """Create a table for displaying media files."""
    return TableFactory.create_media_table(title)
