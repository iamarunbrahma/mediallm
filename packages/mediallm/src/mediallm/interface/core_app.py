#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import typer

from .command_handlers import enhance_command
from .command_handlers import explain_command
from .command_handlers import nl_command
from .system_utils import reset_terminal_state

# Initialize Typer app with completion disabled and support for invocation without subcommands
app = typer.Typer(
    add_completion=False,
    help="Convert media files using natural language commands - powered by local LLMs for complete privacy and zero cost",
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Main entry point for MediaLLM CLI."""
    if ctx.invoked_subcommand is None:
        # If no subcommand is provided, run the natural language interface
        nl_command()


@app.command("nl")
def nl() -> None:
    """Natural language media conversion interface."""
    try:
        nl_command()
    except (KeyboardInterrupt, EOFError):
        reset_terminal_state()
        raise typer.Exit(130)
    except Exception as e:
        reset_terminal_state()
        raise typer.Exit(1) from e


@app.command("explain")
def explain() -> None:
    """Explain what a command would do without executing it."""
    try:
        explain_command()
    except (KeyboardInterrupt, EOFError):
        reset_terminal_state()
        raise typer.Exit(130)
    except Exception as e:
        reset_terminal_state()
        raise typer.Exit(1) from e


@app.command("enhance")
def enhance() -> None:
    """Enhance media processing capabilities."""
    try:
        enhance_command()
    except (KeyboardInterrupt, EOFError):
        reset_terminal_state()
        raise typer.Exit(130)
    except Exception as e:
        reset_terminal_state()
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
