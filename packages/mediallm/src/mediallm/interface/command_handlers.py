#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.panel import Panel

from ..analysis.workspace_scanner import discover_media
from ..core.command_builder import construct_operations
from ..core.llm import LLM
from ..core.llm import OllamaAdapter
from ..core.task_router import dispatch_task
from ..interface.command_handler import CommandHandler
from ..interface.confirm_dialog import confirm_prompt
from ..interface.interactive_prompt import create_input_box
from ..interface.spinner import show_llm_spinner
from ..processing.media_file_handler import most_recent_file
from ..utils.exceptions import BuildError
from ..utils.exceptions import ConfigError
from ..utils.exceptions import ConstructionError
from ..utils.exceptions import ExecError
from ..utils.exceptions import ParseError
from ..utils.exceptions import TranslationError
from ..utils.table_factory import TableFactory
from .display_utils import console
from .display_utils import display_welcome_screen
from .file_utils import filter_context_for_referenced_files
from .file_utils import parse_file_references
from .file_utils import validate_mentioned_files
from .file_utils import validate_non_media_files_in_input
from .system_utils import get_clean_error_message
from .system_utils import reset_terminal_state
from .system_utils import setup_logging

if TYPE_CHECKING:
    from ..utils.config import AppConfig

logger = logging.getLogger(__name__)


def nl_command(
    ctx: typer.Context | None = None,
    prompt: str | None = None,
) -> None:
    """Natural language media conversion interface."""
    if ctx is None:
        # Called from core_app without context, enter interactive mode
        _run_interactive_mode()
        return

    obj = ctx.obj or {}
    cfg: AppConfig = obj["config"]
    assume_yes: bool = obj["assume_yes"]

    try:
        context = discover_media(show_summary=False)
        llm = _make_llm(cfg)

        if prompt:
            # Single command execution
            code = _handle_single_command(prompt, context, llm, cfg, assume_yes)
            raise typer.Exit(code)
        # Interactive mode
        _run_interactive_session(cfg, context, llm, assume_yes)

    except (
        ConfigError,
        ParseError,
        BuildError,
        ExecError,
        ConstructionError,
        TranslationError,
    ) as e:
        reset_terminal_state()
        clean_msg = get_clean_error_message(e)
        console.print(f"[red]× Error:[/red] {clean_msg}")
        raise typer.Exit(1)
    except Exception as e:
        reset_terminal_state()
        error_msg = str(e).lower()
        if any(
            phrase in error_msg
            for phrase in [
                "application is not running",
                "application.exit() failed",
                "event loop",
            ]
        ):
            console.print("[red]× Error:[/red] Terminal session corrupted, please restart the application")
        else:
            console.print(f"[red]× Unexpected error:[/red] {e!s}")
        raise typer.Exit(1)


def _run_interactive_mode() -> None:
    """Run interactive mode without context (standalone)."""
    from ..utils.config import load_config

    setup_logging(False)  # Non-verbose for standalone mode

    try:
        cfg = load_config()
        context = discover_media(show_summary=False)
        llm = _make_llm(cfg)
        _run_interactive_session(cfg, context, llm, False)
    except Exception as e:
        reset_terminal_state()
        console.print(f"[red]× Error:[/red] {get_clean_error_message(e)}")


def _handle_single_command(prompt: str, context: dict, llm: LLM, cfg: AppConfig, assume_yes: bool) -> int:
    """Process a single natural language prompt."""
    # Parse @ file references from the prompt
    processed_prompt, referenced_files = parse_file_references(prompt)

    # Pre-LLM file validation
    existing_files, missing_files = validate_mentioned_files(processed_prompt)
    if missing_files:
        if len(missing_files) == 1:
            raise ValueError(f"File not found: {missing_files[0]}")
        raise ValueError(f"Files not found: {', '.join(missing_files)}")

    # Filter context to prioritize referenced files if any
    current_context = context
    if referenced_files:
        current_context = filter_context_for_referenced_files(context, referenced_files)

    # Show spinner while waiting for LLM response and processing
    try:
        with show_llm_spinner(console, "your ffmpeg command"):
            intent = llm.parse_query(processed_prompt, current_context, timeout=cfg.timeout_seconds)
            plan = dispatch_task(intent, output_dir=None)
            commands = construct_operations(plan, assume_yes=assume_yes)
    except (TranslationError, ParseError, BuildError, ExecError, ConstructionError):
        reset_terminal_state()
        raise

    return _execute_commands(commands, cfg, assume_yes)


def _execute_commands(commands: list, cfg: AppConfig, assume_yes: bool) -> int:
    """Execute commands with preview and confirmation."""
    from ..processing.command_executor import detect_overwrites
    from ..processing.command_executor import preview
    from ..processing.command_executor import preview_modified_commands
    from ..processing.command_executor import run

    # Always show preview before asking for confirmation
    preview(commands)

    # Check for overwrites and show modified commands if needed
    has_overwrites = detect_overwrites(commands)
    if has_overwrites and not assume_yes:
        # Rebuild commands with -y flag for overwrite handling
        # Note: We would need the plan here, but for now we'll use the commands as-is
        preview_modified_commands(commands, commands)  # Simplified for now

    confirmed = (
        True
        if assume_yes
        else confirm_prompt(
            "Run these commands?",
            cfg.confirm_default,
            assume_yes,
            console_instance=console,
        )
    )

    return_code = 0
    if confirmed:
        return_code = run(
            commands,
            confirm=True,
            dry_run=cfg.dry_run,
            show_preview=False,
            assume_yes=assume_yes,
            output_dir=None,
        )
    return return_code


def _run_interactive_session(cfg: AppConfig, context: dict, llm: LLM, assume_yes: bool) -> None:
    """Run interactive session with enhanced UI and commands."""
    display_welcome_screen()
    console.print()

    # Initialize command handler and enhanced prompt
    command_handler = CommandHandler(console)
    prompt_session = None

    # Prepare context for commands
    command_context = {
        "config": cfg,
        "media_context": context,
        "llm": llm,
    }

    # Get media files for autocomplete
    media_files = _get_media_files_for_autocomplete(context)

    # Show initial help hint
    console.print("[dim]💡 Type [cyan]/help[/cyan] for available commands, or start typing your request[/dim]")
    console.print("[dim]💡 Use [cyan]@[/cyan] to reference files (e.g., convert @video.mp4 to audio.mp3)[/dim]")
    console.print(
        "[dim]💡 Press [cyan]TAB[/cyan] to autocomplete commands/file references and [cyan]ENTER[/cyan] to submit your command[/dim]"
    )
    console.print()

    while True:
        try:
            line, prompt_session = create_input_box(
                placeholder="Type your command (e.g., convert video.mp4 to .mp3) or /help for commands",
                slash_commands=command_handler.get_command_completions(),
                media_files=media_files,
                session=prompt_session,
            )

            # Handle session corruption
            if prompt_session is None:
                reset_terminal_state()

            # Handle empty input
            if not line.strip():
                console.print("[red]Input cannot be empty[/red]")
                continue

            # Check for exit commands
            if line.lower() in {"quit", "/quit"}:
                console.print("[bold green]Goodbye![/bold green]")
                break

            # Handle slash commands
            if command_handler.is_command(line):
                result = command_handler.handle_command(line, command_context)
                if result is None:  # Exit command
                    break
                if result:  # Command returned a prompt for processing
                    line = result
                else:  # Command handled internally
                    console.print()
                    continue

            # Process natural language commands
            if line.strip():
                _process_interactive_command(line, context, llm, cfg, assume_yes)

            # Add spacing after successful command execution
            console.print()

        except KeyboardInterrupt:
            console.print("\n[bold green]Goodbye![/bold green]")
            break
        except EOFError:
            console.print("\n[bold green]Goodbye![/bold green]")
            break


def _get_media_files_for_autocomplete(context: dict) -> list[str]:
    """Get media files for autocomplete."""
    media_files = []
    if context:
        media_files.extend(context.get("videos", []))
        media_files.extend(context.get("audios", []))
        media_files.extend(context.get("images", []))
    return media_files


def _process_interactive_command(line: str, context: dict, llm: LLM, cfg: AppConfig, assume_yes: bool) -> None:
    """Process a single interactive command."""
    try:
        # Validate for non-media files before processing
        validate_non_media_files_in_input(line)
        _handle_single_command(line, context, llm, cfg, assume_yes)
    except ValueError as e:
        reset_terminal_state()
        clean_msg = get_clean_error_message(e)
        console.print(f"[red]× Error:[/red] {clean_msg}")
        console.print()
    except (
        ParseError,
        BuildError,
        ExecError,
        ConstructionError,
        TranslationError,
    ) as e:
        reset_terminal_state()
        clean_msg = get_clean_error_message(e)
        console.print(f"[red]× Error:[/red] {clean_msg}")
        console.print()
    except KeyboardInterrupt as e:
        reset_terminal_state()
        interrupt_msg = str(e) if str(e) else "Operation interrupted"
        console.print(f"[bold green]⏹ {interrupt_msg}[/bold green]")
        console.print()


def _make_llm(cfg: AppConfig) -> LLM:
    """Create model interface with Ollama provider."""
    try:
        adapter = OllamaAdapter(host=cfg.ollama_host, model_name=cfg.model_name)
        return LLM(adapter)
    except Exception as e:
        raise ConfigError(f"Failed to initialize model interface: {e}") from e


def explain_command(ffmpeg_command: str | None = None) -> None:
    """Explain an existing ffmpeg command in natural language."""
    if not ffmpeg_command:
        console.print("[red]× Error:[/red] Provide an ffmpeg command to explain.")
        raise typer.Exit(2)
    console.print("[bold green]⚠️ Warning:[/bold green] Explanation is not implemented in MVP.")


def enhance_command(
    prompt: str | None = None,
    show_suggestions: bool = True,
) -> None:
    """Enhance and analyze a user prompt for better LLM understanding."""
    if not prompt:
        console.print("[red]× Error:[/red] Provide a prompt to enhance.")
        raise typer.Exit(2)

    try:
        from ..analysis.prompt_enhancer import enhance_user_prompt

        # Enhance the prompt using context-aware processing
        context = discover_media()
        enhanced = enhance_user_prompt(prompt, context)

        # Display original and enhanced prompts in a panel
        prompt_panel = Panel(
            f"[bold]Original:[/bold] {prompt}\n\n[bold]Enhanced:[/bold] {enhanced}",
            title="[bold green]Prompt Enhancement[/bold green]",
            border_style="green",
        )
        console.print(prompt_panel)

        # Show improvement suggestions if requested
        if show_suggestions:
            _display_suggestions(prompt)

        # Display available file context information
        _display_context_table(context)

    except Exception as e:
        clean_msg = get_clean_error_message(e)
        console.print(f"[red]× Error:[/red] {clean_msg}")
        raise typer.Exit(1) from e


def _display_suggestions(prompt: str) -> None:
    """Display improvement suggestions for prompt."""
    from ..analysis.prompt_enhancer import get_prompt_suggestions

    suggestions = get_prompt_suggestions(prompt)
    if suggestions:
        suggestion_table = TableFactory.create_suggestion_table("Improvement Suggestions")
        suggestion_table.add_column("#", style="bold cyan", justify="center")
        suggestion_table.add_column("Suggestion", style="white")

        for i, suggestion in enumerate(suggestions, 1):
            suggestion_table.add_row(str(i), suggestion)

        console.print(suggestion_table)
    else:
        console.print("\n[green]Prompt looks good![/green]")


def _display_context_table(context: dict) -> None:
    """Display available file context information."""
    context_table = TableFactory.create_info_table("Available Files")
    context_table.add_column("Type", style="bold cyan", justify="center")
    context_table.add_column("Count", style="bold green", justify="center")
    context_table.add_column("Details", style="white")

    # Add videos
    videos = context.get("videos")
    if videos and isinstance(videos, list):
        most_recent_video = most_recent_file([Path(v) for v in videos])
        most_recent_name = Path(str(most_recent_video)).name if most_recent_video else "None"
        context_table.add_row(
            "Videos",
            str(len(videos)),
            f"Most recent: {most_recent_name}",
        )

    # Add audios
    audios = context.get("audios")
    if audios and isinstance(audios, list):
        most_recent_audio = most_recent_file([Path(a) for a in audios])
        most_recent_name = Path(str(most_recent_audio)).name if most_recent_audio else "None"
        context_table.add_row(
            "Audio",
            str(len(audios)),
            f"Most recent: {most_recent_name}",
        )

    # Add images
    images = context.get("images")
    if images and isinstance(images, list):
        most_recent_image = most_recent_file([Path(img) for img in images])
        most_recent_name = Path(str(most_recent_image)).name if most_recent_image else "None"
        context_table.add_row(
            "Images",
            str(len(images)),
            f"Most recent: {most_recent_name}",
        )

    # Add subtitles
    subtitle_files = context.get("subtitle_files")
    if subtitle_files and isinstance(subtitle_files, list):
        subtitle_names = [Path(str(s)).name for s in subtitle_files[:3]]
        context_table.add_row(
            "Subtitles",
            str(len(subtitle_files)),
            f"Files: {', '.join(subtitle_names)}",
        )

    if context_table.row_count > 0:
        console.print(context_table)
