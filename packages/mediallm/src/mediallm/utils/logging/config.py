#!/usr/bin/env python3
# Author: Arun Brahma

import json
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Any
from typing import Final

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme
from rich.traceback import install as install_rich_traceback

from .context import get_context


class LoggingConstants:
    """Constants for logging configuration."""

    DEFAULT_LOG_LEVEL: Final[str] = "INFO"
    LOG_FILE_MAX_BYTES: Final[int] = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: Final[int] = 5
    DEFAULT_ENCODING: Final[str] = "utf-8"

    NOISY_LIBRARIES: Final[list[str]] = [
        "urllib3",
        "botocore",
        "boto3",
        "requests",
        "httpx",
        "aiohttp",
        "asyncio",
        "charset_normalizer",
        "certifi",
    ]


# Create a custom theme for better visual consistency
custom_theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "red",
        "critical": "red bold",
        "debug": "dim",
        "success": "green",
        "progress": "blue",
    }
)

# Initialize console with custom theme
console = Console(theme=custom_theme)


def _determine_log_level(level: str | int | None) -> int:
    """Determine logging level from parameter or environment."""
    if level is None:
        level = os.getenv("LOG_LEVEL", LoggingConstants.DEFAULT_LOG_LEVEL)

    if isinstance(level, str):
        return getattr(logging, level.upper(), logging.INFO)
    return level


def _setup_console_handler(root_logger: logging.Logger, rich_console: Console, level: int, show_locals: bool) -> None:
    """Setup Rich console handler."""
    rich_handler = RichHandler(
        console=rich_console,
        show_time=False,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=show_locals,
        show_level=False,
        level=level,
        log_time_format="[%X]",
    )
    rich_handler.setLevel(level)

    rich_formatter = logging.Formatter(fmt="%(message)s", datefmt="[%X]")
    rich_handler.setFormatter(rich_formatter)
    root_logger.addHandler(rich_handler)


def _setup_file_handler(root_logger: logging.Logger, log_file: str | Path, json_output: bool, level: int) -> None:
    """Setup file logging handler."""
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=LoggingConstants.LOG_FILE_MAX_BYTES,
        backupCount=LoggingConstants.LOG_BACKUP_COUNT,
        encoding=LoggingConstants.DEFAULT_ENCODING,
    )
    file_handler.setLevel(level)

    if json_output:
        file_handler.setFormatter(JsonFormatter())
    else:
        file_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)

    root_logger.addHandler(file_handler)


def setup_logging(
    level: str | int | None = None,
    json_output: bool = False,
    log_file: str | Path | None = None,
    show_locals: bool = True,
    console_instance: Console | None = None,
) -> None:
    """Setup Rich-based logging configuration."""
    level = _determine_log_level(level)
    install_rich_traceback(show_locals=show_locals)

    rich_console = console_instance or console
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    _setup_console_handler(root_logger, rich_console, level, show_locals)

    if log_file:
        _setup_file_handler(root_logger, log_file, json_output, level)

    _silence_noisy_libraries()

    # Create Rich console handler with enhanced formatting
    rich_handler = RichHandler(
        console=rich_console,
        show_time=False,  # Don't show time for cleaner output
        show_path=False,  # Don't show file paths and line numbers
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=show_locals,
        show_level=False,  # Don't show INFO/WARNING/etc. prefixes
        level=level,
        log_time_format="[%X]",
    )
    rich_handler.setLevel(level)

    # Set root logger level
    root_logger.setLevel(level)

    # Create formatter for Rich handler
    rich_formatter = logging.Formatter(
        fmt="%(message)s",
        datefmt="[%X]",
    )
    rich_handler.setFormatter(rich_formatter)

    # Add Rich handler to root logger
    root_logger.addHandler(rich_handler)

    # Setup file logging if log_file is specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        if json_output:
            # JSON file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setFormatter(JsonFormatter())
        else:
            # Plain text file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setFormatter(
                logging.Formatter(
                    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )

        file_handler.setLevel(level)
        root_logger.addHandler(file_handler)

    # Capture warnings in logs
    logging.captureWarnings(True)

    # Silence noisy libraries
    _silence_noisy_libraries()

    # Log setup completion with enhanced formatting
    logger = logging.getLogger(__name__)
    # Removed startup logging message for cleaner CLI experience
    logger.debug(
        "mediallm logging initialized",
        extra={
            "level": logging.getLevelName(level),
            "log_file": str(log_file) if log_file else "console only",
            "rich_tracebacks": True,
            "show_locals": show_locals,
        },
    )


def _silence_noisy_libraries() -> None:
    """Silence noisy third-party libraries to WARNING level."""
    for lib in LoggingConstants.NOISY_LIBRARIES:
        logging.getLogger(lib).setLevel(logging.WARNING)


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Get context data
        context_data = get_context()

        # Prepare log entry
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add context data if available
        if context_data:
            log_entry["context"] = context_data

        # Add exception info if present
        if record.exc_info and record.exc_info != (None, None, None):
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in log_entry and not key.startswith("_"):
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False, default=str)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_startup_info() -> None:
    """Log startup information with Rich formatting."""
    logger = get_logger(__name__)

    # Only log startup info in debug mode to keep CLI clean
    logger.debug(
        "Starting mediallm",
        extra={
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": sys.platform,
            "working_directory": str(Path.cwd()),
        },
    )

    # Only log configuration status in debug mode
    api_key_configured = bool(os.getenv("OPENAI_API_KEY"))
    logger.debug(
        "Configuration status",
        extra={
            "api_key_configured": api_key_configured,
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "model": os.getenv("AICLIP_MODEL", "gpt-5"),
        },
    )


def log_operation_start(operation: str, **kwargs: Any) -> None:
    """Log the start of an operation with Rich formatting.

    Args:
        operation: Name of the operation
        **kwargs: Additional context information
    """
    logger = get_logger(__name__)
    logger.info(f"Starting operation: {operation}", extra=kwargs)


def log_operation_success(operation: str, **kwargs: Any) -> None:
    """Log successful completion of an operation with Rich formatting.

    Args:
        operation: Name of the operation
        **kwargs: Additional context information
    """
    logger = get_logger(__name__)
    logger.info(f"Operation completed: {operation}", extra=kwargs)


def log_operation_error(operation: str, error: Exception, **kwargs: Any) -> None:
    """Log an operation error with Rich formatting.

    Args:
        operation: Name of the operation
        error: The error that occurred
        **kwargs: Additional context information
    """
    logger = get_logger(__name__)
    logger.error(
        f"Operation failed: {operation}",
        extra={
            "error_type": type(error).__name__,
            "error_message": str(error),
            **kwargs,
        },
        exc_info=True,
    )
