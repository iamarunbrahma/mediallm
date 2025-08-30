#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import logging

import typer

from ..utils.config import AppConfig
from ..utils.config import load_config
from ..utils.exceptions import ConfigError
from .command_handlers import enhance_command
from .command_handlers import explain_command
from .command_handlers import nl_command
from .display_utils import console
from .system_utils import get_clean_error_message
from .system_utils import reset_terminal_state
from .system_utils import setup_logging

logger = logging.getLogger(__name__)

# Initialize Typer app with completion disabled and support for invocation without subcommands
app = typer.Typer(
    add_completion=False,
    help="Convert media files using natural language commands - powered by local LLMs for complete privacy and zero cost",
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True)
def cli_main(
    ctx: typer.Context,
    prompt: str | None = typer.Argument(None, help="Natural language prompt; if provided, runs once and exits"),
    yes: bool = typer.Option(False, "--yes/--no-yes", help="Skip confirmation and overwrite"),
    model: str | None = typer.Option(None, "--model", help="LLM model override"),
    dry_run: bool = typer.Option(None, "--dry-run/--no-dry-run", help="Preview only"),
    timeout: int = typer.Option(60, "--timeout", help="LLM timeout seconds"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose logging"),
    output_dir: str | None = typer.Option(None, "--output-dir", help="Output directory for generated files"),
) -> None:
    """Main CLI entry point with global options."""
    _main_impl(ctx, prompt, yes, model, dry_run, timeout, verbose, output_dir)


def main(
    ctx: typer.Context | None = None,
    prompt: str | None = None,
    yes: bool = False,
    model: str | None = None,
    dry_run: bool | None = None,
    timeout: int = 60,
    verbose: bool = False,
    output_dir: str | None = None,
) -> None:
    """Programmatic entry point for the application."""
    _main_impl(ctx, prompt, yes, model, dry_run, timeout, verbose, output_dir)


def _main_impl(
    ctx: typer.Context | None,
    prompt: str | None,
    yes: bool,
    model: str | None,
    dry_run: bool | None,
    timeout: int,
    verbose: bool,
    output_dir: str | None,
) -> None:
    """Initialize global options and optionally run one-shot prompt."""
    setup_logging(verbose)

    try:
        # Load and validate configuration
        cfg = _load_and_configure(model, dry_run, output_dir, timeout)

        # Store configuration in context for subcommands
        if ctx is not None:
            ctx.obj = {"config": cfg, "assume_yes": yes}

        # Handle command execution
        _handle_command_execution(ctx, prompt, cfg, yes)

    except ConfigError as e:
        clean_msg = get_clean_error_message(e)
        console.print(f"[red]× Configuration Error:[/red] {clean_msg}")
        raise typer.Exit(1) from e


def _load_and_configure(
    model: str | None,
    dry_run: bool | None,
    output_dir: str | None,
    timeout: int,
) -> AppConfig:
    """Load and configure application settings."""
    cfg = load_config()
    original_model = cfg.model_name

    # Apply CLI overrides
    if model:
        cfg.model_name = model
    if dry_run is not None:
        cfg.dry_run = dry_run
    if output_dir:
        cfg.output_directory = output_dir
    cfg.timeout_seconds = timeout

    # Handle model availability after CLI overrides
    cfg.ensure_model_available_after_override(original_model)

    return cfg


def _handle_command_execution(
    ctx: typer.Context | None,
    prompt: str | None,
    cfg: AppConfig,
    yes: bool,
) -> None:
    """Handle command execution logic."""
    # Determine if this is a one-shot invocation (no subcommand specified)
    invoked_none = (ctx is None) or (ctx.invoked_subcommand is None)

    if invoked_none:
        if prompt is not None:
            _execute_one_shot_command(prompt, cfg, yes)
        # No subcommand and no prompt: enter interactive mode
        elif ctx is not None:
            nl_command(ctx=ctx, prompt=None)


def _execute_one_shot_command(prompt: str, cfg: AppConfig, yes: bool) -> None:
    """Execute a single one-shot command."""
    try:
        from ..analysis.workspace_scanner import discover_media
        from ..core.command_builder import construct_operations
        from ..core.llm import LLM
        from ..core.llm import OllamaAdapter
        from ..core.task_router import dispatch_task
        from ..interface.confirm_dialog import confirm_prompt
        from ..interface.spinner import show_llm_spinner
        from .file_utils import filter_context_for_referenced_files
        from .file_utils import parse_file_references
        from .file_utils import validate_non_media_files_in_input

        # Validate for non-media files before processing
        validate_non_media_files_in_input(prompt)

        # Parse @ file references from the prompt
        processed_prompt, referenced_files = parse_file_references(prompt)

        # Execute one-shot command: scan context, parse intent, build and execute
        context = discover_media(show_summary=False)

        # Filter context to prioritize referenced files if any
        if referenced_files:
            context = filter_context_for_referenced_files(context, referenced_files)

        # Create LLM instance
        adapter = OllamaAdapter(host=cfg.ollama_host, model_name=cfg.model_name)
        llm = LLM(adapter)

        # Show spinner while waiting for LLM response and processing
        try:
            with show_llm_spinner(console, "your ffmpeg command"):
                intent = llm.parse_query(processed_prompt, context, timeout=cfg.timeout_seconds)
                plan = dispatch_task(intent, output_dir=None)
                commands = construct_operations(plan, assume_yes=yes)
        except Exception:
            reset_terminal_state()
            raise

        from ..processing.command_executor import detect_overwrites
        from ..processing.command_executor import preview
        from ..processing.command_executor import preview_modified_commands
        from ..processing.command_executor import run

        # Always show preview before asking for confirmation
        preview(commands)

        # Check for overwrites and show modified commands if needed
        has_overwrites = detect_overwrites(commands)
        if has_overwrites and not yes:
            # Rebuild commands with -y flag for overwrite handling
            modified_commands = construct_operations(plan, assume_yes=True)
            preview_modified_commands(commands, modified_commands)
            commands = modified_commands

        confirmed = (
            True
            if yes
            else confirm_prompt(
                "Run these commands?",
                cfg.confirm_default,
                yes,
                console_instance=console,
            )
        )

        code = run(
            commands,
            confirm=confirmed,
            dry_run=cfg.dry_run,
            show_preview=False,
            assume_yes=yes,
            output_dir=None,
        )
        raise typer.Exit(code)

    except ValueError as e:
        clean_msg = get_clean_error_message(e)
        console.print(f"[red]× Error:[/red] {clean_msg}")
        raise typer.Exit(1)
    except Exception as e:
        clean_msg = get_clean_error_message(e)
        console.print(f"[red]× Error:[/red] {clean_msg}")
        raise typer.Exit(1)
    except KeyboardInterrupt as e:
        interrupt_msg = str(e) if str(e) else "Operation interrupted"
        console.print(f"\n[bold green]⏹ {interrupt_msg}[/bold green]")
        raise typer.Exit(130) from e


@app.command()
def nl(
    ctx: typer.Context,
    prompt: str | None = typer.Argument(None, help="Natural language prompt"),
) -> None:
    """Translate NL to ffmpeg, preview, confirm, and execute."""
    try:
        nl_command(ctx=ctx, prompt=prompt)
    except (KeyboardInterrupt, EOFError):
        reset_terminal_state()
        raise typer.Exit(130)
    except Exception as e:
        reset_terminal_state()
        raise typer.Exit(1) from e


@app.command()
def explain(
    ffmpeg_command: str | None = typer.Argument(None, help="Existing ffmpeg command to explain"),
) -> None:
    """Explain an existing ffmpeg command in natural language."""
    try:
        explain_command(ffmpeg_command)
    except (KeyboardInterrupt, EOFError):
        reset_terminal_state()
        raise typer.Exit(130)
    except Exception as e:
        reset_terminal_state()
        raise typer.Exit(1) from e


@app.command()
def enhance(
    prompt: str = typer.Argument(..., help="User prompt to enhance and analyze"),
    show_suggestions: bool = typer.Option(True, "--suggestions/--no-suggestions", help="Show improvement suggestions"),
) -> None:
    """Enhance and analyze a user prompt for better LLM understanding."""
    try:
        enhance_command(prompt, show_suggestions)
    except (KeyboardInterrupt, EOFError):
        reset_terminal_state()
        raise typer.Exit(130)
    except Exception as e:
        reset_terminal_state()
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
