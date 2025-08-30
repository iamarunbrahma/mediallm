#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Final

from rich.panel import Panel

from ..utils.table_factory import TableFactory

if TYPE_CHECKING:
    from rich.console import Console


class CommandHandler:
    """Handler for processing slash commands in the interactive CLI."""

    # Class constants
    _MAX_HISTORY_SIZE: Final[int] = 50
    _MAX_RECENT_HISTORY: Final[int] = 10
    _MAX_FILES_DISPLAY: Final[int] = 5
    _CLEAR_SEQUENCE: Final[str] = "\033[H\033[2J\033[3J"
    _MODEL_SWITCH_DELAY: Final[float] = 0.5

    # Command information for help display
    _COMMANDS_INFO: Final[list[tuple[str, str, str]]] = [
        ("/help", "Show this help message", "/help"),
        (
            "/generate <prompt>",
            "Generate command from natural language",
            "/generate convert video to mp3",
        ),
        ("/clear", "Clear the screen", "/clear"),
        ("/history", "Show command history", "/history"),
        ("/examples", "Show example commands", "/examples"),
        ("/config", "Show current configuration", "/config"),
        ("/files", "List available media files", "/files"),
        ("/model [name]", "Show or switch current model", "/model gemma2:2b"),
        ("/quit", "Exit the application", "/quit"),
    ]

    # Example commands for demonstration
    _EXAMPLE_COMMANDS: Final[list[tuple[str, str]]] = [
        ("Convert video to audio", "convert video.mp4 to audio.mp3"),
        ("Resize video", "resize video.mp4 to 720p"),
        ("Extract audio from video", "extract audio from movie.mp4"),
        ("Extract subtitles from video", "extract subtitles from video.mp4"),
        ("Compress video", "compress large_video.mp4 by 50%"),
        ("Add subtitles", "add subtitles.srt to video.mp4"),
        ("Create GIF from video", "convert first 10 seconds of video.mp4 to gif"),
        ("Merge videos", "merge video1.mp4 and video2.mp4"),
        ("Trim video", "trim video.mp4 from 0:30 to 2:15"),
        ("Change video speed", "speed up video.mp4 by 2x"),
        ("Convert image format", "convert image.png to jpeg"),
    ]

    def __init__(self, console: Console) -> None:
        """Initialize the command handler."""
        self.console = console
        self.commands = {
            "help": self._show_help,
            "generate": self._generate_command,
            "clear": self._clear_screen,
            "history": self._show_history,
            "quit": self._exit_app,
            "examples": self._show_examples,
            "config": self._show_config,
            "files": self._list_files,
            "model": self._switch_model,
        }
        self.command_history: list[str] = []

    def is_command(self, text: str) -> bool:
        """Check if the input is a slash command."""
        return text.strip().startswith("/")

    def handle_command(self, text: str, context: dict[str, Any] | None = None) -> str | None:
        """Process a slash command."""
        text = text.strip()
        if not text.startswith("/"):
            return text

        # Parse command and arguments
        parts = text[1:].split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Add to history (except for history command itself)
        if command != "history":
            self._add_to_history(text)

        # Execute command
        if command in self.commands:
            return self.commands[command](args, context)
        self.console.print(f"[red]× Unknown command: /{command}[/red]")
        self.console.print("Type [bold cyan]/help[/bold cyan] to see available commands.")
        return ""

    def get_command_completions(self) -> list[str]:
        """Get list of available slash commands for autocomplete."""
        return [f"/{cmd}" for cmd in self.commands]

    def _add_to_history(self, command: str) -> None:
        """Add command to history with size limiting."""
        self.command_history.append(command)
        if len(self.command_history) > self._MAX_HISTORY_SIZE:
            self.command_history = self.command_history[-self._MAX_HISTORY_SIZE :]

    def _create_help_table(self) -> Table:
        """Create help table with command information."""
        help_table = TableFactory.create_command_table("Available Commands")
        help_table.add_column("Command", style="bold cyan", min_width=15)
        help_table.add_column("Description", style="white")
        help_table.add_column("Usage", style="dim")

        for cmd, desc, usage in self._COMMANDS_INFO:
            help_table.add_row(cmd, desc, usage)

        return help_table

    def _create_shortcuts_panel(self) -> Panel:
        """Create keyboard shortcuts panel."""
        return Panel(
            "[bold]Keyboard Shortcuts:[/bold]\n"
            "• [cyan]Tab[/cyan] - Autocomplete commands and file paths\n"
            "• [cyan]↑/↓[/cyan] - Navigate command history\n"
            "• [cyan]Esc[/cyan] - Interrupt running operation\n"
            "• [cyan]Ctrl+C[/cyan] - Cancel operation / Exit application\n"
            "• [cyan]Ctrl+D[/cyan] - Exit application\n"
            "• [cyan]Ctrl+J[/cyan] - Add new line (multiline input)\n"
            "• [cyan]Enter[/cyan] - Submit command",
            title="[bold blue]Help[/bold blue]",
            border_style="blue",
        )

    def _show_help(self, args: str, context: dict[str, Any] | None = None) -> str:
        """Show help information."""
        self.console.print()

        help_table = self._create_help_table()
        self.console.print(help_table)

        shortcuts_panel = self._create_shortcuts_panel()
        self.console.print(shortcuts_panel)
        self.console.print()
        return ""

    def _generate_command(self, args: str, context: dict[str, Any] | None = None) -> str:
        """Handle generate command - return the prompt for normal processing."""
        if not args.strip():
            self.console.print("[red]× Error:[/red] Please provide a prompt after /generate")
            self.console.print("[dim]Example: /generate convert video.mp4 to audio.mp3[/dim]")
            return ""
        return args.strip()

    def _clear_screen(self, args: str, context: dict[str, Any] | None = None) -> str:
        """Clear the terminal screen completely."""
        try:
            sys.stdout.write(self._CLEAR_SEQUENCE)
            sys.stdout.flush()
        except OSError:
            self._fallback_clear_screen()

        return ""

    def _fallback_clear_screen(self) -> None:
        """Fallback screen clearing method."""
        try:
            if os.name == "nt":
                os.system("cls")
            else:
                os.system("clear")
        except OSError:
            sys.stdout.write("\n" * 50)
            sys.stdout.flush()

    def _show_history(self, args: str, context: dict[str, Any] | None = None) -> str:
        """Show command history."""
        if not self.command_history:
            self.console.print("[bold green]No command history available.[/bold green]")
            return ""

        history_table = TableFactory.create_command_table("Command History")
        history_table.add_column("#", style="bold cyan", justify="center", min_width=4)
        history_table.add_column("Command", style="white")

        # Show last commands
        recent_history = self.command_history[-self._MAX_RECENT_HISTORY :]
        for i, cmd in enumerate(recent_history, 1):
            history_table.add_row(str(i), cmd)

        self.console.print(history_table)
        return ""

    def _exit_app(self, args: str, context: dict[str, Any] | None = None) -> None:
        """Exit the application."""
        self.console.print("[bold green]Goodbye![/bold green]")

    def _show_examples(self, args: str, context: dict[str, Any] | None = None) -> str:
        """Show example commands."""
        examples_table = TableFactory.create_command_table("Example Commands")
        examples_table.add_column("Task", style="bold green", min_width=20)
        examples_table.add_column("Example Command", style="cyan")

        for task, example in self._EXAMPLE_COMMANDS:
            examples_table.add_row(task, example)

        self.console.print(examples_table)
        return ""

    def _show_config(self, args: str, context: dict[str, Any] | None = None) -> str:
        """Show current configuration."""
        if not context or "config" not in context:
            self.console.print("[bold green]Configuration not available[/bold green]")
            return ""

        config = context["config"]
        config_table = TableFactory.create_config_table("Current Configuration")
        config_table.add_column("Setting", style="bold cyan", min_width=20)
        config_table.add_column("Value", style="white")

        settings = [
            ("Model", getattr(config, "model_name", "Unknown")),
            ("Host", getattr(config, "ollama_host", "Unknown")),
            ("Timeout", f"{getattr(config, 'timeout_seconds', 'Unknown')}s"),
            ("Dry Run", "Yes" if getattr(config, "dry_run", False) else "No"),
        ]

        for setting, value in settings:
            config_table.add_row(setting, str(value))

        self.console.print(config_table)
        return ""

    def _list_files(self, args: str, context: dict[str, Any] | None = None) -> str:
        """List available media files."""
        if not context or "media_context" not in context:
            self.console.print("[bold green]No media context available[/bold green]")
            return ""

        media_context = context["media_context"]
        files_table = TableFactory.create_media_table("Available Media Files")
        files_table.add_column("Type", style="bold cyan", justify="center")
        files_table.add_column("Count", style="bold green", justify="center")
        files_table.add_column("Files", style="white")

        # Add video files
        videos = media_context.get("videos", [])
        if videos:
            video_files = "\n".join([f"• {Path(v).name}" for v in videos[:5]])
            if len(videos) > 5:
                video_files += f"\n• ... and {len(videos) - 5} more"
            files_table.add_row("Videos", str(len(videos)), video_files)

        # Add audio files
        audios = media_context.get("audios", [])
        if audios:
            audio_files = "\n".join([f"• {Path(a).name}" for a in audios[:5]])
            if len(audios) > 5:
                audio_files += f"\n• ... and {len(audios) - 5} more"
            files_table.add_row("Audio", str(len(audios)), audio_files)

        # Add image files
        images = media_context.get("images", [])
        if images:
            image_files = "\n".join([f"• {Path(i).name}" for i in images[:5]])
            if len(images) > 5:
                image_files += f"\n• ... and {len(images) - 5} more"
            files_table.add_row("Images", str(len(images)), image_files)

        if files_table.row_count > 0:
            self.console.print(files_table)
        else:
            self.console.print("[bold green]No media files found in the current directory[/bold green]")

        return ""

    def _switch_model(self, args: str, context: dict[str, Any] | None = None) -> str:
        """Show current model or switch to a new one."""
        if not context or "config" not in context:
            self.console.print("[red]× Error:[/red] Configuration not available")
            return ""

        config = context["config"]

        # If no arguments, show current model
        if not args.strip():
            self.console.print(f"[bold green]Current model:[/bold green] [white]{config.model_name}[/white]")
            return ""

        new_model = args.strip()

        # Check if it's the same model
        if new_model == config.model_name:
            self.console.print(f"[yellow]Already using model:[/yellow] [white]{new_model}[/white]")
            return ""

        # Switch to new model
        self.console.print(f"[cyan]Switching to model:[/cyan] [white]{new_model}[/white]")

        try:
            from ..core.llm import LLM
            from ..core.llm import OllamaAdapter
            from ..utils.model_manager import ensure_model_available

            # Try to ensure the model is available (will download if needed)
            if not ensure_model_available(new_model, use_spinner=True):
                self.console.print(f"[red]× Failed to obtain model:[/red] [white]{new_model}[/white]")
                return ""

            # Create new LLM instance with the new model
            old_model = config.model_name
            config.model_name = new_model

            # Test the new model by creating an adapter
            adapter = OllamaAdapter(host=config.ollama_host, model_name=config.model_name)
            new_llm = LLM(adapter)

            # Update the LLM in context if available
            if "llm" in context:
                context["llm"] = new_llm

            self.console.print(f"[green]✓[/green] Model switched to: [white]{new_model}[/white]")

        except Exception as e:
            # Restore original model on failure
            config.model_name = old_model if "old_model" in locals() else config.model_name
            self.console.print(f"[red]× Error switching model:[/red] {e!s}")
            self.console.print("[dim]The original model is still active[/dim]")

        # Allow terminal to clean up before returning to prompt
        time.sleep(0.5)
        return ""
