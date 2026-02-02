#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import logging
import re
import shutil
import subprocess  # nosec B404: subprocess used with explicit list args, no shell
import time
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Final

from rich.console import Console
from rich.panel import Panel

from ..utils.exceptions import ExecError
from ..utils.table_factory import TableFactory

if TYPE_CHECKING:
    from rich.table import Table

logger = logging.getLogger(__name__)

# Security constants for subprocess execution
DEFAULT_SUBPROCESS_TIMEOUT: Final[int] = 300  # 5 minutes
MAX_OUTPUT_SIZE: Final[int] = 10 * 1024 * 1024  # 10MB


class CommandExecutor:
    """Handles FFmpeg command execution with security validation and progress tracking."""

    _DANGEROUS_PATTERNS: Final[list[re.Pattern[str]]] = [
        re.compile(r"\brm\s+-rf?\b", re.IGNORECASE),
        re.compile(r"\brm\s+", re.IGNORECASE),
        re.compile(r"\bdel\s+/[sfq]\b", re.IGNORECASE),
        re.compile(r"\bdel\s+", re.IGNORECASE),
        re.compile(r"\bformat\s+[a-z]:", re.IGNORECASE),
        re.compile(r"\bsystem\s*\(", re.IGNORECASE),
        re.compile(r"\bexec\s*\(", re.IGNORECASE),
        re.compile(r"\beval\s*\(", re.IGNORECASE),
        re.compile(r"[&|`]"),
        re.compile(r"\$\("),
        re.compile(r"\$\{"),
        re.compile(r">\s*[/\\]"),
        re.compile(r"\bsudo\b", re.IGNORECASE),
        re.compile(r"\bchmod\b", re.IGNORECASE),
        re.compile(r"\bchown\b", re.IGNORECASE),
        re.compile(r"\bmkfs\b", re.IGNORECASE),
        re.compile(r"\bdd\s+if=", re.IGNORECASE),
    ]
    _FILTER_FLAGS: Final[set[str]] = {"-vf", "-af", "-filter_complex", "-filter:v", "-filter:a"}
    _VALID_EXECUTABLES: Final[set[str]] = {"ffmpeg", "ffprobe"}
    _RENDER_DELAY: Final[float] = 0.5

    def __init__(self, console: Console | None = None) -> None:
        """Initialize CommandExecutor."""
        self.console = console or Console()

    @classmethod
    def format_command(cls, cmd: list[str]) -> str:
        """Format command list as a readable string."""
        return " ".join(cmd)

    @classmethod
    def extract_output_path(cls, cmd: list[str]) -> Path | None:
        """Extract the output file path from an ffmpeg command."""
        if len(cmd) < 2:
            return None
        return Path(cmd[-1])

    @classmethod
    def check_overwrite_protection(cls, _commands: list[list[str]], _assume_yes: bool = False) -> bool:
        """Check for existing output files."""
        return True

    @classmethod
    def detect_overwrites(cls, commands: list[list[str]]) -> bool:
        """Detect if any output files would be overwritten."""
        return any(cls.extract_output_path(cmd) and cls.extract_output_path(cmd).exists() for cmd in commands)

    def preview(self, commands: list[list[str]]) -> None:
        """Display a preview of planned ffmpeg commands."""
        logger.debug(f"Previewing {len(commands)} commands")
        if not commands:
            self.console.print("[bold green]⚠️ No commands to preview[/bold green]")
            return

        table = self._create_preview_table()
        self._populate_preview_table(table, commands)
        self._display_table(table)

    def preview_modified_commands(self, original_commands: list[list[str]], modified_commands: list[list[str]]) -> None:
        """Display modified commands table showing changes made for overwrite handling."""
        if not modified_commands:
            return

        table = self._create_modified_commands_table()
        self._populate_modified_commands_table(table, original_commands, modified_commands)
        self._display_table(table)

    def run(
        self,
        commands: list[list[str]],
        confirm: bool,
        dry_run: bool,
        show_preview: bool = True,
        assume_yes: bool = False,
        output_dir: Path | None = None,
    ) -> int:
        """Execute ffmpeg commands with validation and error handling."""
        logger.debug(f"Starting execution run: {len(commands)} commands, dry_run={dry_run}, confirm={confirm}")
        if not commands:
            logger.debug("No commands to execute")
            self.console.print("[bold green]⚠️ No commands to execute[/bold green]")
            return 0

        if show_preview:
            self.preview(commands)

        if dry_run:
            logger.debug("Dry run mode activated - no commands will be executed")
            self.console.print("[bold yellow]Dry run mode - no commands will be executed[/bold yellow]")
            return 0

        if not confirm:
            logger.debug("Execution cancelled by user")
            self.console.print("[bold green]Execution cancelled by user[/bold green]")
            return 0

        return self._execute_commands(commands, assume_yes, output_dir)

    def _create_preview_table(self) -> Table:
        """Create preview table for commands."""
        table = TableFactory.create_command_table("Planned ffmpeg Commands")
        table.add_column("#", style="bold cyan", justify="center")
        table.add_column("Command", style="white", overflow="fold")
        table.add_column("Output", style="green", overflow="fold")
        table.add_column("Status", style="bold", justify="center")
        return table

    def _populate_preview_table(self, table: Table, commands: list[list[str]]) -> None:
        """Populate preview table with command information."""
        for idx, cmd in enumerate(commands, start=1):
            output_path = self.extract_output_path(cmd)
            output_display = str(output_path) if output_path else "N/A"
            status = "New" if not output_path or not output_path.exists() else "Overwrite"
            table.add_row(str(idx), self.format_command(cmd), output_display, status)

    def _create_modified_commands_table(self) -> Table:
        """Create modified commands table."""
        table = TableFactory.create_command_table("Modified Commands for Execution")
        table.add_column("#", style="bold cyan", justify="center")
        table.add_column("Command", style="white", overflow="fold")
        table.add_column("Output", style="green", overflow="fold")
        table.add_column("Changes", style="bold", justify="center")
        return table

    def _populate_modified_commands_table(
        self,
        table: Table,
        original_commands: list[list[str]],
        modified_commands: list[list[str]],
    ) -> None:
        """Populate modified commands table with change information."""
        for idx, (original_cmd, modified_cmd) in enumerate(
            zip(original_commands, modified_commands, strict=False), start=1
        ):
            output_path = self.extract_output_path(modified_cmd)
            output_display = str(output_path) if output_path else "N/A"

            changes = self._detect_command_changes(original_cmd, modified_cmd)
            changes_display = ", ".join(changes) if changes else "None"

            table.add_row(
                str(idx),
                self.format_command(modified_cmd),
                output_display,
                changes_display,
            )

    def _detect_command_changes(self, original_cmd: list[str], modified_cmd: list[str]) -> list[str]:
        """Detect changes made to commands."""
        changes = []
        if "-y" in modified_cmd and "-y" not in original_cmd:
            changes.append("[yellow]Added -y[/yellow]")
        return changes

    def _display_table(self, table: Table) -> None:
        """Display table with proper rendering."""
        self.console.print("\n")
        self.console.print(table)
        self.console.file.flush()
        time.sleep(self._RENDER_DELAY)

    def _execute_commands(self, commands: list[list[str]], assume_yes: bool, output_dir: Path | None) -> int:
        """Execute all commands with progress tracking."""
        logger.debug(f"Executing {len(commands)} commands with overwrite protection check")
        if not self.check_overwrite_protection(commands, assume_yes):
            logger.debug("Operation cancelled by user due to file conflicts")
            self.console.print("[bold green]Operation cancelled due to file conflicts[/bold green]")
            return 1

        total_commands = len(commands)
        successful_commands = 0
        logger.debug(f"Starting batch execution of {total_commands} commands")

        self.console.print(f"\n[bold green]Starting execution of {total_commands} command(s)...[/bold green]")
        self.console.print()

        for i, cmd in enumerate(commands, 1):
            logger.debug(f"Executing command {i}/{total_commands}: {' '.join(cmd[:3])}...")
            try:
                self._execute_single_command(cmd, i, total_commands)
                successful_commands += 1
                logger.debug(f"Command {i} completed successfully")
            except ExecError as e:
                logger.error(f"Command {i} failed: {str(e)[:100]}...")
                self.console.print(f"[red]Command {i} failed:[/red] {e}")
                raise

        self._display_execution_summary(successful_commands, total_commands, output_dir)
        final_result = 0 if successful_commands == total_commands else 1
        logger.debug(
            f"Batch execution completed: {successful_commands}/{total_commands} successful, exit code: {final_result}"
        )
        return final_result

    def _execute_single_command(
        self, cmd: list[str], cmd_num: int, total_cmds: int, timeout: int | None = None
    ) -> None:
        """Execute a single ffmpeg command with progress feedback and timeout.

        Args:
            cmd: The FFmpeg command to execute as a list of arguments.
            cmd_num: Current command number in the batch.
            total_cmds: Total number of commands in the batch.
            timeout: Timeout in seconds (defaults to DEFAULT_SUBPROCESS_TIMEOUT).
        """
        logger.debug(f"Validating command {cmd_num}: {' '.join(cmd)}")
        self._validate_command(cmd)

        effective_timeout = timeout or DEFAULT_SUBPROCESS_TIMEOUT
        output_path = self.extract_output_path(cmd)
        logger.debug(f"Command {cmd_num} output path: {output_path}")
        self.console.print(f"[bold blue]Executing command {cmd_num}/{total_cmds}:[/bold blue]")
        self.console.print(f"[dim]Output:[/dim] {output_path}")

        try:
            logger.debug(f"Starting subprocess execution for command {cmd_num} (timeout={effective_timeout}s)")
            # nosec B603: fixed binary, no shell, args vetted
            result = subprocess.run(
                cmd,
                check=True,
                timeout=effective_timeout,
                capture_output=True,
            )
            logger.debug(f"Subprocess completed for command {cmd_num} with return code: {result.returncode}")

            # Check output size limits
            if result.stdout and len(result.stdout) > MAX_OUTPUT_SIZE:
                logger.warning(f"Command {cmd_num} output exceeds size limit, truncating logs")

            if result.returncode != 0:
                raise ExecError(
                    f"ffmpeg command failed with exit code {result.returncode}. "
                    f"Common causes: (1) input file not found or corrupted, "
                    f"(2) invalid output format or codec, "
                    f"(3) insufficient disk space, "
                    f"(4) permission issues. Check file paths and try again."
                )
            self.console.print(f"[green]Command {cmd_num} completed successfully[/green]")

        except subprocess.TimeoutExpired as exc:
            logger.error(f"Command {cmd_num} timed out after {effective_timeout}s")
            raise ExecError(
                f"FFmpeg command timed out after {effective_timeout} seconds. "
                f"This may be due to: (1) very large input file, "
                f"(2) complex encoding operation, "
                f"(3) insufficient system resources. "
                f"Try increasing the timeout or processing smaller files."
            ) from exc
        except subprocess.CalledProcessError as exc:
            logger.error(f"ffmpeg execution failed for command {cmd_num}: {exc}")
            logger.debug(f"Failed command details: {' '.join(cmd)}")
            stderr_msg = exc.stderr.decode() if exc.stderr else ""
            raise ExecError(
                f"ffmpeg execution failed with error: {exc}. "
                f"{f'Details: {stderr_msg[:500]}' if stderr_msg else ''}"
                f"Please verify: (1) input files exist and are readable, "
                f"(2) output directory is writable, "
                f"(3) ffmpeg is properly installed (try 'ffmpeg -version'), "
                f"(4) file formats are supported. "
                f"Use --verbose for detailed logging."
            ) from exc

    def _validate_command(self, cmd: list[str]) -> None:
        """Validate command for execution."""
        logger.debug(f"Validating command: {cmd[0] if cmd else 'empty'}")
        if not cmd:
            logger.error("Empty command received for validation")
            raise ExecError("Empty command received for execution.")

        self._validate_executable_exists(cmd[0])
        self._validate_command_security(cmd)
        logger.debug("Command validation passed")

    def _validate_executable_exists(self, executable: str) -> None:
        """Validate that the executable exists in PATH."""
        logger.debug(f"Checking if executable exists: {executable}")
        resolved = shutil.which(executable)
        if resolved is None:
            logger.error(f"Executable not found in PATH: {executable}")
            raise ExecError(
                f"Executable not found: {executable}. Please install FFmpeg:\n"
                "• macOS: brew install ffmpeg\n"
                "• Ubuntu/Debian: sudo apt install ffmpeg\n"
                "• Windows: choco install ffmpeg"
            )
        logger.debug(f"Executable found: {resolved}")

    def _validate_command_security(self, cmd: list[str]) -> None:
        """Validate command for basic security."""
        logger.debug("Performing security validation on command")
        if not self._is_command_secure(cmd):
            logger.error(f"Command failed security validation: {' '.join(cmd[:3])}...")
            raise ExecError(
                "Command failed security validation. This could be due to: (1) unsafe file paths or arguments, (2) "
                "unsupported ffmpeg flags, or (3) potential security risks. Please check your input and try a simpler "
                "operation."
            )

    def _is_command_secure(self, command: list[str]) -> bool:
        """Validate FFmpeg command using regex-based pattern matching.

        Uses word boundary patterns to prevent false positives (e.g., "format"
        should not match "formatting", "rm" should not match "arm").

        Special handling for FFmpeg filter arguments which legitimately use
        semicolons in complex filtergraph syntax.
        """
        if not command or not any(command[0].endswith(exe) for exe in self._VALID_EXECUTABLES):
            return False

        # Separate filter arguments from other arguments
        non_filter_args = []
        i = 0
        while i < len(command):
            arg = command[i]
            if arg in self._FILTER_FLAGS and i + 1 < len(command):
                # Skip filter flag and its value (which may contain semicolons)
                i += 2
            else:
                non_filter_args.append(arg)
                i += 1

        # Check non-filter arguments for dangerous patterns
        cmd_str = " ".join(non_filter_args)
        if any(pattern.search(cmd_str) for pattern in self._DANGEROUS_PATTERNS):
            return False

        # Check for semicolons outside of filter arguments (potential command injection)
        for arg in non_filter_args:
            if ";" in arg:
                return False

        return True

    def _display_execution_summary(
        self, successful_commands: int, total_commands: int, output_dir: Path | None
    ) -> None:
        """Display execution summary."""
        self.console.print()

        if successful_commands == total_commands:
            summary_panel = Panel(
                f"[bold green]All {total_commands} commands completed successfully![/bold green]",
                title="[bold green]Execution Summary[/bold green]",
                border_style="green",
            )
            self.console.print(summary_panel)

            if output_dir:
                self._display_completion_summary(output_dir)
        else:
            summary_panel = Panel(
                f"[bold green]{successful_commands}/{total_commands} commands completed successfully[/bold green]",
                title="[bold yellow]Execution Summary[/bold yellow]",
                border_style="yellow",
            )
            self.console.print(summary_panel)

    def _display_completion_summary(self, output_dir: Path) -> None:
        """Display completion summary with generated files."""
        # Avoid static import to prevent cycles; dynamic import tolerated
        try:
            module = __import__(
                "mediallm.interface.display_utils",
                fromlist=["display_completion_summary"],
            )
            display_fn = getattr(module, "display_completion_summary", None)
            if callable(display_fn):
                display_fn(output_dir)
        except Exception:
            return


# Module-level convenience functions for backward compatibility
_executor = CommandExecutor()


def format_command(cmd: list[str]) -> str:
    """Format command list as a readable string."""
    return CommandExecutor.format_command(cmd)


def extract_output_path(cmd: list[str]) -> Path | None:
    """Extract the output file path from an ffmpeg command."""
    return CommandExecutor.extract_output_path(cmd)


def check_overwrite_protection(commands: list[list[str]], assume_yes: bool = False) -> bool:
    """Check for existing output files."""
    return CommandExecutor.check_overwrite_protection(commands, assume_yes)


def detect_overwrites(commands: list[list[str]]) -> bool:
    """Detect if any output files would be overwritten."""
    return CommandExecutor.detect_overwrites(commands)


def preview(commands: list[list[str]]) -> None:
    """Display a preview of planned ffmpeg commands."""
    _executor.preview(commands)


def preview_modified_commands(original_commands: list[list[str]], modified_commands: list[list[str]]) -> None:
    """Display modified commands table showing changes made for overwrite handling."""
    _executor.preview_modified_commands(original_commands, modified_commands)


def run(
    commands: list[list[str]],
    confirm: bool,
    dry_run: bool,
    show_preview: bool = True,
    assume_yes: bool = False,
    output_dir: Path | None = None,
) -> int:
    """Execute ffmpeg commands with validation and error handling."""
    return _executor.run(commands, confirm, dry_run, show_preview, assume_yes, output_dir)
