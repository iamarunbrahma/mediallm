#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import logging
import sys
import time
from typing import Final

from ..utils.exceptions import BuildError
from ..utils.exceptions import ConfigError
from ..utils.exceptions import ConstructionError
from ..utils.exceptions import ExecError
from ..utils.exceptions import ExecutionError
from ..utils.exceptions import ParseError
from ..utils.exceptions import SettingsError
from ..utils.exceptions import TranslationError


class SystemConstants:
    """Constants for system utilities."""

    TERMINAL_RESET_DELAY: Final[float] = 1.0
    TERMINAL_RESET_SEQUENCE: Final[str] = "\033[0m\033[?25h\033[?1000l\033[?47l"


def reset_terminal_state() -> None:
    """Reset terminal state to prevent corruption after errors."""
    try:
        _write_reset_sequence()
        _flush_output_streams()
        _delay_for_cleanup()
        _flush_input_stream()
    except OSError:
        _fallback_flush()


def _write_reset_sequence() -> None:
    """Write terminal reset sequence to stdout."""
    sys.stdout.write(SystemConstants.TERMINAL_RESET_SEQUENCE)


def _flush_output_streams() -> None:
    """Flush stdout and stderr streams."""
    sys.stdout.flush()
    sys.stderr.flush()


def _delay_for_cleanup() -> None:
    """Add delay to allow prompt-toolkit cleanup."""
    time.sleep(SystemConstants.TERMINAL_RESET_DELAY)


def _flush_input_stream() -> None:
    """Clear any pending input on Unix-like systems."""
    try:
        import select
        import termios

        if hasattr(select, "select") and sys.stdin.isatty():
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except (ImportError, OSError, AttributeError):
        # Not available on all platforms, continue without flushing
        pass


def _fallback_flush() -> None:
    """Fallback flush if terminal reset fails."""
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except OSError:
        pass


def get_clean_error_message(exception: Exception) -> str:
    """Extract clean error message from exception."""
    if isinstance(
        exception,
        ConstructionError
        | SettingsError
        | ExecutionError
        | TranslationError
        | ConfigError
        | ParseError
        | BuildError
        | ExecError,
    ):
        return str(exception)

    error_msg = str(exception).strip()
    if not error_msg:
        return f"Unknown {type(exception).__name__}"

    return _clean_error_text(error_msg)


def _clean_error_text(error_msg: str) -> str:
    """Clean and format error message text."""
    cleaned = error_msg.replace("\n", " ").replace("\r", "")

    # Remove common prefixes that make errors verbose
    prefixes_to_remove = [
        "Error: ",
        "Exception: ",
        "RuntimeError: ",
        "ValueError: ",
        "TypeError: ",
        "OSError: ",
        "IOError: ",
    ]

    for prefix in prefixes_to_remove:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
            break

    return cleaned.strip()


def setup_logging(verbose: bool) -> None:
    """Setup logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # Suppress verbose logging from third-party libraries unless in debug mode
    if not verbose:
        _silence_noisy_libraries()


def _silence_noisy_libraries() -> None:
    """Silence verbose logging from third-party libraries."""
    noisy_loggers = ["urllib3", "requests", "httpx", "aiohttp", "botocore", "boto3"]

    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
