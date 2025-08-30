#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

from typing import Any
from typing import Final


class MediaLLMError(Exception):
    """Base exception class for all MediaLLM errors."""

    ERROR_CODE: str = "MEDIALLM_ERROR"

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Initialize MediaLLM error."""
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.error_code = self.ERROR_CODE

    def __str__(self) -> str:
        """Return string representation of the error."""
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        """Return detailed representation of the error."""
        return f"{self.__class__.__name__}(message={self.message!r}, context={self.context!r})"


class SettingsError(MediaLLMError):
    """Raised when configuration or environment validation fails."""

    ERROR_CODE: Final[str] = "SETTINGS_ERROR"


class TranslationError(MediaLLMError):
    """Raised when the LLM fails to produce a valid task."""

    ERROR_CODE: Final[str] = "TRANSLATION_ERROR"


class ConstructionError(MediaLLMError):
    """Raised when a task cannot be dispatched or converted into operations."""

    ERROR_CODE: Final[str] = "CONSTRUCTION_ERROR"


class ExecutionError(MediaLLMError):
    """Raised when operation execution fails."""

    ERROR_CODE: Final[str] = "EXECUTION_ERROR"


class ConfigError(MediaLLMError):
    """Raised when configuration or initialization fails."""

    ERROR_CODE: Final[str] = "CONFIG_ERROR"


class ParseError(MediaLLMError):
    """Raised when parsing fails."""

    ERROR_CODE: Final[str] = "PARSE_ERROR"


class BuildError(MediaLLMError):
    """Raised when building commands fails."""

    ERROR_CODE: Final[str] = "BUILD_ERROR"


class ExecError(MediaLLMError):
    """Raised when command execution fails."""

    ERROR_CODE: Final[str] = "EXEC_ERROR"


class ValidationError(MediaLLMError):
    """Raised when input validation fails."""

    ERROR_CODE: Final[str] = "VALIDATION_ERROR"


class SecurityError(MediaLLMError):
    """Raised when security validation fails."""

    ERROR_CODE: Final[str] = "SECURITY_ERROR"
