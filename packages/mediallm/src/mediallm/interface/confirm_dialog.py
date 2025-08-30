#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

from typing import Final

from rich.console import Console
from rich.prompt import Confirm


class ConfirmDialog:
    """Handles user confirmation prompts with configurable defaults."""

    # Class constants
    _DEFAULT_PROMPT: Final[str] = "Confirmation Required"
    _CANCEL_MESSAGE: Final[str] = "[dim]Operation cancelled[/dim]"

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the confirm dialog with console instance."""
        self.console = console or Console()

    def confirm_prompt(
        self,
        question: str,
        default_yes: bool = True,
        assume_yes: bool = False,
        console_instance: Console | None = None,
    ) -> bool:
        """Prompt user for confirmation with configurable defaults."""
        if assume_yes:
            return True

        active_console = console_instance or self.console

        try:
            return self._display_confirmation_prompt(active_console, default_yes)
        except KeyboardInterrupt:
            return self._handle_keyboard_interrupt(active_console)

    def _display_confirmation_prompt(self, console: Console, default_yes: bool) -> bool:
        """Display the confirmation prompt to user."""
        return Confirm.ask(self._DEFAULT_PROMPT, default=default_yes, console=console)

    def _handle_keyboard_interrupt(self, console: Console) -> bool:
        """Handle Ctrl+C gracefully by returning False."""
        console.print(self._CANCEL_MESSAGE)
        return False


# Module-level convenience function for backward compatibility
_dialog = ConfirmDialog()


def confirm_prompt(
    question: str,
    default_yes: bool = True,
    assume_yes: bool = False,
    console_instance: Console | None = None,
) -> bool:
    """Prompt user for confirmation with configurable defaults."""
    return _dialog.confirm_prompt(question, default_yes, assume_yes, console_instance)
