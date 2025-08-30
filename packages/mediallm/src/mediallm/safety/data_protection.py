#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING
from typing import Any
from typing import Final

if TYPE_CHECKING:
    from pydantic_core.core_schema import AfterValidatorFunctionSchema

logger = logging.getLogger(__name__)


class DataProtector:
    """Handles data protection and sanitization operations."""

    # Sanitization patterns
    _MIN_KEY_DISPLAY_LENGTH: Final[int] = 8
    _MASKED_SHORT_KEY: Final[str] = "***SHORT_KEY***"
    _MASKED_NO_KEY: Final[str] = "***NO_KEY***"
    _VISIBLE_CHARS_COUNT: Final[int] = 3
    _MIN_VALID_KEY_LENGTH: Final[int] = 32

    _SANITIZATION_PATTERNS: Final[list[tuple[str, str]]] = [
        (r"sk-[a-zA-Z0-9]{10,}", "***API_KEY***"),
        (r"OPENAI_API_KEY[=\s:]+[^\s]+", "OPENAI_API_KEY=***MASKED***"),
        (r"/Users/[^/\s]+", "/Users/***USER***"),
        (r"C:\\\\Users\\\\[^\\\\s]+", r"C:\\Users\\***USER***"),
        (r"password[=\s:]+[^\s]+", "password=***MASKED***"),
        (r"token[=\s:]+[^\s]+", "token=***MASKED***"),
        (r"secret[=\s:]+[^\s]+", "secret=***MASKED***"),
    ]

    @classmethod
    def mask_api_key(cls, api_key: str | None) -> str:
        """Mask API key for safe display in logs and errors."""
        if not api_key or not isinstance(api_key, str):
            return cls._MASKED_NO_KEY

        if len(api_key) <= cls._MIN_KEY_DISPLAY_LENGTH:
            return cls._MASKED_SHORT_KEY

        # Show first 3 and last 3 characters, mask the rest
        return f"{api_key[:cls._VISIBLE_CHARS_COUNT]}***{api_key[-cls._VISIBLE_CHARS_COUNT:]}"

    @classmethod
    def validate_api_key_format(cls, api_key: str | None) -> bool:
        """Validate API key has expected format without logging the key."""
        if not api_key or not isinstance(api_key, str):
            return False

        # OpenAI API keys start with 'sk-' and can include various formats
        if api_key.startswith("sk-"):
            key_body = api_key[3:]
            # Allow alphanumeric characters, hyphens, and underscores
            if len(key_body) >= cls._MIN_VALID_KEY_LENGTH and re.match(r"^[a-zA-Z0-9_-]+$", key_body):
                return True

        return False

    @classmethod
    def sanitize_error_message(cls, message: str) -> str:
        """Remove sensitive information from error messages."""
        if not message:
            return ""

        sanitized = message
        for pattern, replacement in cls._SANITIZATION_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        return sanitized


class SecureLogger:
    """Logger wrapper that automatically sanitizes sensitive data."""

    def __init__(self, logger_name: str):
        """Initialize secure logger with the given name."""
        self.logger = logging.getLogger(logger_name)

    def _sanitize_args(self, args: tuple[Any, ...]) -> tuple[Any, ...]:
        """Sanitize logging arguments to remove sensitive data."""
        return tuple((DataProtector.sanitize_error_message(str(arg)) if isinstance(arg, str) else arg) for arg in args)

    def debug(self, msg: str, *args: Any) -> None:
        """Log debug message with sanitized arguments."""
        self.logger.debug(DataProtector.sanitize_error_message(msg), *self._sanitize_args(args))

    def info(self, msg: str, *args: Any) -> None:
        """Log info message with sanitized arguments."""
        self.logger.info(DataProtector.sanitize_error_message(msg), *self._sanitize_args(args))

    def warning(self, msg: str, *args: Any) -> None:
        """Log warning message with sanitized arguments."""
        self.logger.warning(DataProtector.sanitize_error_message(msg), *self._sanitize_args(args))

    def error(self, msg: str, *args: Any) -> None:
        """Log error message with sanitized arguments."""
        self.logger.error(DataProtector.sanitize_error_message(msg), *self._sanitize_args(args))

    def critical(self, msg: str, *args: Any) -> None:
        """Log critical message with sanitized arguments."""
        self.logger.critical(DataProtector.sanitize_error_message(msg), *self._sanitize_args(args))


class SecretStr:
    """String wrapper that prevents accidental exposure of sensitive data."""

    _SECRET_DISPLAY: Final[str] = "***SECRET***"
    _SECRET_REPR: Final[str] = "SecretStr('***SECRET***')"

    def __init__(self, value: str | None):
        """Initialize with a sensitive string value."""
        self._value = value

    def get_secret_value(self) -> str | None:
        """Get the actual secret value. Use with caution."""
        return self._value

    def __str__(self) -> str:
        """String representation that masks the secret."""
        return self._SECRET_DISPLAY

    def __repr__(self) -> str:
        """Representation that masks the secret."""
        return self._SECRET_REPR

    def __bool__(self) -> bool:
        """Boolean evaluation based on whether value exists."""
        return bool(self._value)

    def __eq__(self, other: object) -> bool:
        """Equality comparison with other SecretStr instances."""
        if isinstance(other, SecretStr):
            return self._value == other._value
        return False

    def mask(self) -> str:
        """Get masked version of the secret."""
        return DataProtector.mask_api_key(self._value)

    def is_valid_format(self) -> bool:
        """Check if secret has valid format."""
        return DataProtector.validate_api_key_format(self._value)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> AfterValidatorFunctionSchema:
        """Pydantic v2 compatibility for schema generation."""
        from pydantic_core import core_schema

        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
        )


# Backward compatibility wrapper functions
def mask_api_key(api_key: str | None) -> str:
    """Mask API key for safe display in logs and errors."""
    return DataProtector.mask_api_key(api_key)


def validate_api_key_format(api_key: str | None) -> bool:
    """Validate API key has expected format without logging the key."""
    return DataProtector.validate_api_key_format(api_key)


def sanitize_error_message(message: str) -> str:
    """Remove sensitive information from error messages."""
    return DataProtector.sanitize_error_message(message)


def create_secure_logger(name: str) -> SecureLogger:
    """Create a logger that automatically sanitizes sensitive data."""
    return SecureLogger(name)
