#!/usr/bin/env python3
# Author: Arun Brahma

"""FFmpeg command validation and retry logic with LLM regeneration."""

from __future__ import annotations

import logging
import subprocess  # nosec B404: subprocess used with explicit list args, no shell
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Final

from rich.console import Console
from rich.panel import Panel

from ..core.command_builder import construct_operations
from ..core.task_router import dispatch_task
from ..safety.data_protection import create_secure_logger
from ..utils.exceptions import ExecError

if TYPE_CHECKING:
    from ..core.llm import LLM
    from ..utils.data_models import CommandPlan

logger = create_secure_logger(__name__)

# Constants
MAX_RETRY_ATTEMPTS: Final[int] = 3
FFMPEG_VALIDATION_TIMEOUT: Final[int] = 10  # seconds


class CommandRetryHandler:
    """Handles FFmpeg command validation and retry with LLM regeneration."""

    def __init__(self, llm: LLM, console: Console | None = None) -> None:
        """Initialize the retry handler."""
        self._llm = llm
        self._console = console or Console()

    def validate_ffmpeg_command(self, cmd: list[str]) -> tuple[bool, str]:
        """Validate an FFmpeg command by performing a dry-run check."""
        if not cmd or cmd[0] not in ("ffmpeg", "ffprobe"):
            return False, "Command must start with ffmpeg or ffprobe"

        validation_cmd = cmd.copy()
        if "-v" not in validation_cmd:
            validation_cmd.insert(1, "-v")
            validation_cmd.insert(2, "error")

        input_check_errors = self._check_input_files(cmd)
        if input_check_errors:
            return False, input_check_errors

        try:
            quick_check_cmd = self._build_quick_validation_cmd(cmd)
            if quick_check_cmd:
                result = subprocess.run(  # nosec B603
                    quick_check_cmd,
                    capture_output=True,
                    timeout=FFMPEG_VALIDATION_TIMEOUT,
                )
                if result.returncode != 0:
                    stderr = result.stderr.decode("utf-8", errors="replace")
                    error_lines = [
                        line for line in stderr.split("\n")
                        if line.strip() and not line.startswith("[")
                    ]
                    error_msg = error_lines[0] if error_lines else stderr[:200]
                    return False, f"FFmpeg validation failed: {error_msg}"

        except subprocess.TimeoutExpired:
            logger.debug("Validation timed out - proceeding with command")
            return True, ""
        except FileNotFoundError:
            return False, "FFmpeg executable not found. Please install FFmpeg."
        except Exception as e:
            logger.debug(f"Validation check failed with exception: {e}")
            return True, ""

        return True, ""

    def _check_input_files(self, cmd: list[str]) -> str:
        """Check if input files specified in the command exist."""
        missing_files = []
        i = 0
        while i < len(cmd):
            if cmd[i] == "-i" and i + 1 < len(cmd):
                input_path = cmd[i + 1]
                if not input_path.startswith(("pipe:", "http://", "https://", "-")):
                    if not Path(input_path).exists():
                        missing_files.append(input_path)
                i += 2
            else:
                i += 1

        if missing_files:
            return f"Input file(s) not found: {', '.join(missing_files)}"
        return ""

    def _build_quick_validation_cmd(self, cmd: list[str]) -> list[str] | None:
        """Build a quick validation command for syntax checking."""
        if not cmd or cmd[0] != "ffmpeg":
            return None

        validation_cmd = cmd.copy()
        last_input_idx = -1
        for i, arg in enumerate(validation_cmd):
            if arg == "-i":
                last_input_idx = i + 1

        if last_input_idx > 0 and last_input_idx < len(validation_cmd):
            validation_cmd.insert(last_input_idx + 1, "-t")
            validation_cmd.insert(last_input_idx + 2, "0.001")

        return validation_cmd

    def execute_with_retry(
        self,
        original_prompt: str,
        workspace: dict[str, Any],
        plan: CommandPlan,
        commands: list[list[str]],
        executor_func,
        timeout: int = 60,
        assume_yes: bool = False,
    ) -> tuple[int, list[list[str]]]:
        """Execute commands with retry logic on failure."""
        current_commands = commands
        current_plan = plan
        last_error = ""

        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            logger.debug(f"Execution attempt {attempt}/{MAX_RETRY_ATTEMPTS}")

            for i, cmd in enumerate(current_commands):
                is_valid, error_msg = self.validate_ffmpeg_command(cmd)
                if not is_valid:
                    logger.warning(f"Command {i+1} validation failed: {error_msg}")
                    if attempt < MAX_RETRY_ATTEMPTS:
                        self._console.print(
                            f"[yellow]Command validation failed: {error_msg}[/yellow]"
                        )
                        self._console.print(
                            f"[yellow]Attempting to regenerate (attempt {attempt}/{MAX_RETRY_ATTEMPTS})...[/yellow]"
                        )
                        current_commands, current_plan = self._regenerate_commands(
                            original_prompt, workspace, error_msg, timeout, assume_yes
                        )
                        if current_commands is None:
                            return 1, commands
                        break
            else:
                try:
                    exit_code = executor_func(current_commands)
                    if exit_code == 0:
                        return 0, current_commands
                    return exit_code, current_commands

                except ExecError as e:
                    last_error = str(e)
                    logger.warning(f"Execution failed on attempt {attempt}: {last_error}")

                    if attempt < MAX_RETRY_ATTEMPTS:
                        self._console.print(
                            Panel(
                                f"[yellow]Execution failed: {last_error[:200]}...[/yellow]\n\n"
                                f"Attempting to regenerate command (attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS})...",
                                title="[bold yellow]Retry[/bold yellow]",
                                border_style="yellow",
                            )
                        )
                        current_commands, current_plan = self._regenerate_commands(
                            original_prompt, workspace, last_error, timeout, assume_yes
                        )
                        if current_commands is None:
                            raise
                    else:
                        raise

        return 1, current_commands

    def _regenerate_commands(
        self,
        original_prompt: str,
        workspace: dict[str, Any],
        error_message: str,
        timeout: int,
        assume_yes: bool,
    ) -> tuple[list[list[str]] | None, CommandPlan | None]:
        """Regenerate commands using the LLM with error context."""
        enhanced_prompt = self._build_retry_prompt(original_prompt, error_message)

        try:
            logger.debug(f"Regenerating with enhanced prompt: {enhanced_prompt[:100]}...")

            # Parse the enhanced query
            intent = self._llm.parse_query(enhanced_prompt, workspace, timeout=timeout)

            # Build new plan and commands
            new_plan = dispatch_task(intent, output_dir=None)
            new_commands = construct_operations(new_plan, assume_yes=assume_yes)

            logger.debug(f"Regenerated {len(new_commands)} commands")

            # Show preview of regenerated commands
            self._console.print("\n[bold green]Regenerated commands:[/bold green]")
            for i, cmd in enumerate(new_commands, 1):
                self._console.print(f"  {i}. {' '.join(cmd[:10])}...")

            return new_commands, new_plan

        except Exception as e:
            logger.error(f"Command regeneration failed: {e}")
            self._console.print(f"[red]Failed to regenerate command: {e}[/red]")
            return None, None

    def _build_retry_prompt(self, original_prompt: str, error_message: str) -> str:
        """Build an enhanced prompt for retry that includes error context."""
        error_summary = self._extract_error_summary(error_message)
        return (
            f"{original_prompt}\n\n"
            f"IMPORTANT: The previous FFmpeg command failed with this error:\n"
            f"{error_summary}\n\n"
            f"Please generate a corrected command that avoids this error. "
            f"Consider:\n"
            f"- Check codec compatibility with the output format\n"
            f"- Verify input file paths are correct\n"
            f"- Ensure filter syntax is valid\n"
            f"- Use appropriate codecs for the target container"
        )

    def _extract_error_summary(self, error_message: str) -> str:
        """Extract the most relevant part of an error message."""
        error_patterns = [
            "Invalid data found",
            "Unknown encoder",
            "Unknown decoder",
            "Encoder not found",
            "Decoder not found",
            "No such file or directory",
            "Permission denied",
            "Invalid argument",
            "Unrecognized option",
            "does not support",
            "codec not currently supported",
            "Invalid option",
            "Error while opening",
            "Output file",
            "cannot be used together",
        ]

        lines = error_message.split("\n")
        relevant_lines = []

        for line in lines:
            line_lower = line.lower()
            if any(pattern.lower() in line_lower for pattern in error_patterns):
                relevant_lines.append(line.strip())
            elif "error" in line_lower:
                relevant_lines.append(line.strip())

        if relevant_lines:
            return "\n".join(relevant_lines[:3])

        return error_message[:200] if len(error_message) > 200 else error_message


def create_retry_handler(llm: LLM, console: Console | None = None) -> CommandRetryHandler:
    """Factory function to create a CommandRetryHandler."""
    return CommandRetryHandler(llm, console)
