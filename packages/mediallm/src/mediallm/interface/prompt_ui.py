#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

from typing import Final


class SimplePromptUI:
    """Simple text-based prompt interface for user confirmations."""

    # Class constants
    _AFFIRMATIVE_RESPONSES: Final[set[str]] = {"y", "yes"}
    _DEFAULT_YES_INDICATOR: Final[str] = "Y/n"
    _DEFAULT_NO_INDICATOR: Final[str] = "y/N"

    def __init__(self) -> None:
        """Initialize the simple prompt UI."""

    def confirm_prompt(self, question: str, default_yes: bool = True, assume_yes: bool = False) -> bool:
        """Prompt user for confirmation with configurable defaults."""
        if assume_yes:
            return True

        default_indicator = self._get_default_indicator(default_yes)

        try:
            response = self._get_user_input(question, default_indicator)
            return self._process_response(response, default_yes)
        except KeyboardInterrupt:
            return False

    def _get_default_indicator(self, default_yes: bool) -> str:
        """Get the default indicator string."""
        return self._DEFAULT_YES_INDICATOR if default_yes else self._DEFAULT_NO_INDICATOR

    def _get_user_input(self, question: str, default_indicator: str) -> str:
        """Get user input with formatted prompt."""
        return input(f"{question} [{default_indicator}] ").strip().lower()

    def _process_response(self, response: str, default_yes: bool) -> bool:
        """Process the user response."""
        if not response:
            return default_yes

        return response in self._AFFIRMATIVE_RESPONSES


# Module-level convenience function for backward compatibility
_prompt_ui = SimplePromptUI()


def confirm_prompt(question: str, default_yes: bool = True, assume_yes: bool = False) -> bool:
    """Prompt user for confirmation with configurable defaults."""
    return _prompt_ui.confirm_prompt(question, default_yes, assume_yes)
