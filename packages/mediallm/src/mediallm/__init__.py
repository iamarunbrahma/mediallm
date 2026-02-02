#!/usr/bin/env python3
# Author: Arun Brahma
"""MediaLLM - Natural language to FFmpeg, instantly and privately.

This package provides the core API for converting natural language
requests into FFmpeg commands using local LLMs via Ollama.

Example:
    >>> from mediallm import MediaLLM
    >>> mediallm = MediaLLM()
    >>> mediallm.scan_workspace("./videos")
    >>> commands = mediallm.generate_commands("compress video.mp4 to 50%")

"""

from .analysis.workspace_scanner import discover_media
from .api import MediaLLM
from .utils.data_models import Action
from .utils.data_models import CommandEntry
from .utils.data_models import CommandPlan
from .utils.data_models import MediaIntent
from .utils.exceptions import ConfigError
from .utils.exceptions import ConstructionError
from .utils.exceptions import ExecError
from .utils.exceptions import ExecutionError
from .utils.exceptions import MediaLLMError
from .utils.exceptions import ParseError
from .utils.exceptions import SecurityError
from .utils.exceptions import TranslationError
from .utils.exceptions import ValidationError
from .utils.version import __version__

__all__ = [
    "Action",
    "CommandEntry",
    "CommandPlan",
    "ConfigError",
    "ConstructionError",
    "ExecError",
    "ExecutionError",
    "MediaIntent",
    "MediaLLM",
    "MediaLLMError",
    "ParseError",
    "SecurityError",
    "TranslationError",
    "ValidationError",
    "__version__",
    "discover_media",
]
