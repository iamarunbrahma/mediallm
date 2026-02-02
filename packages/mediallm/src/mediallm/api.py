#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import warnings
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import httpx

from .analysis.workspace_scanner import discover_media
from .core.command_builder import construct_operations
from .core.llm import LLM
from .core.llm import OllamaAdapter
from .core.task_router import dispatch_task
from .utils.exceptions import ConfigError
from .utils.exceptions import TranslationError
from .utils.exceptions import ValidationError

if TYPE_CHECKING:
    from .utils.data_models import CommandPlan


class MediaLLM:
    """Main API interface for MediaLLM package.

    This class provides the primary interface for converting natural language
    requests into FFmpeg commands using local LLMs via Ollama.

    Example:
        >>> mediallm = MediaLLM()
        >>> mediallm.scan_workspace("./videos")
        >>> plan = mediallm.generate_plan("compress video.mp4 to 50%")
        >>> commands = mediallm.generate_commands("compress video.mp4 to 50%")
    """

    def __init__(
        self,
        workspace: dict[str, Any] | None = None,
        ollama_host: str = "http://localhost:11434",
        model_name: str = "llama3.1:latest",
        timeout: int = 60,
        working_dir: Path | str | None = None,
    ) -> None:
        """Initialize MediaLLM API.

        Args:
            workspace: Pre-scanned workspace data. If None, workspace will be
                scanned lazily on first access.
            ollama_host: URL of the Ollama server.
            model_name: Name of the Ollama model to use.
            timeout: Timeout in seconds for LLM requests.
            working_dir: Working directory for media file operations.
        """
        self._working_dir = Path(working_dir) if working_dir else Path.cwd()
        self._timeout = timeout
        self._workspace: dict[str, Any] | None = None
        self._llm: LLM | None = None
        self._ollama_host = ollama_host
        self._model_name = model_name

        # Set up workspace (lazy initialization)
        if workspace is not None:
            self._workspace = workspace

    @property
    def working_dir(self) -> Path:
        """Get the working directory."""
        return self._working_dir

    @property
    def timeout(self) -> int:
        """Get the timeout value."""
        return self._timeout

    @property
    def workspace(self) -> dict[str, Any]:
        """Get the cached workspace data, scanning lazily if needed.

        Returns:
            Dictionary containing discovered media files.
        """
        return self._ensure_workspace()

    def get_workspace(self) -> dict[str, Any]:
        """Get the cached workspace data.

        Returns:
            Dictionary containing discovered media files.

        Raises:
            RuntimeError: If workspace has not been scanned yet.
        """
        if self._workspace is None:
            raise RuntimeError(
                "Workspace not scanned. Call scan_workspace() first, or pass "
                "a workspace dict to the constructor."
            )
        return self._workspace

    def scan_workspace(self, directory: Path | str | None = None) -> dict[str, Any]:
        """Scan directory for media files and update the cached workspace.

        Args:
            directory: Directory to scan. Defaults to working_dir.

        Returns:
            Dictionary containing discovered media files.
        """
        scan_dir = Path(directory) if directory else self._working_dir
        self._workspace = discover_media(cwd=scan_dir, show_summary=False)
        return self._workspace

    def _ensure_workspace(self) -> dict[str, Any]:
        """Ensure workspace is initialized, scanning if needed."""
        if self._workspace is None:
            self._workspace = discover_media(cwd=self._working_dir, show_summary=False)
        return self._workspace

    def _initialize_llm(self, ollama_host: str, model_name: str) -> LLM:
        """Initialize the LLM provider with specific error handling."""
        try:
            # Import ollama for specific exception handling
            import ollama as ollama_module

            provider = OllamaAdapter(host=ollama_host, model_name=model_name)
            return LLM(provider)

        except ollama_module.ResponseError as e:
            error_msg = str(e.error) if hasattr(e, "error") else str(e)
            raise ConfigError(
                f"Ollama model error: {error_msg}. "
                f"Please verify the model is installed: ollama pull {model_name}"
            ) from e
        except httpx.ConnectError as e:
            raise ConfigError(
                f"Cannot connect to Ollama at {ollama_host}. "
                "Please ensure Ollama is running: ollama serve"
            ) from e
        except httpx.TimeoutException as e:
            raise ConfigError(
                f"Ollama connection timed out at {ollama_host}. "
                "Please check your network connection and Ollama status."
            ) from e
        except ImportError as e:
            raise ConfigError(
                "Ollama package not installed. Please install it: pip install ollama"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Ollama provider: {e}. "
                "Please ensure Ollama is running: ollama serve"
            ) from e

    def _validate_request(self, request: str) -> None:
        """Validate the input request."""
        if not request or not request.strip():
            raise ValidationError("Request cannot be empty")

        if len(request) > 10000:  # Reasonable limit
            raise ValidationError("Request too long (max 10000 characters)")

    def _get_llm(self) -> LLM:
        """Get or create the LLM instance lazily."""
        if self._llm is None:
            self._llm = self._initialize_llm(self._ollama_host, self._model_name)
        return self._llm

    def generate_plan(
        self,
        request: str,
        output_dir: Path | str | None = None,
    ) -> CommandPlan:
        """Generate a command plan from natural language.

        This method parses the natural language request and returns a structured
        CommandPlan without building the final FFmpeg commands.

        Args:
            request: Natural language description of the media operation.
            output_dir: Optional directory for output files.

        Returns:
            CommandPlan containing the parsed operation details.

        Raises:
            ValidationError: If the request is invalid.
            TranslationError: If the request cannot be parsed.
            ConfigError: If there's an issue with the Ollama configuration.
        """
        self._validate_request(request)

        try:
            # Parse natural language to intent
            workspace = self._ensure_workspace()
            intent = self._get_llm().parse_query(request, workspace, timeout=self._timeout)

            # Convert intent to command plan
            allowed_dirs = [self._working_dir]
            return dispatch_task(
                intent,
                allowed_dirs=allowed_dirs,
                output_dir=Path(output_dir) if output_dir else None,
            )

        except TranslationError:
            raise
        except (ValidationError, ConfigError):
            raise
        except Exception as e:
            raise RuntimeError(
                f"Failed to generate plan for request: '{request[:100]}...'. Error: {e}"
            ) from e

    def generate_commands(
        self,
        request: str,
        assume_yes: bool = True,
        output_dir: Path | str | None = None,
    ) -> list[list[str]]:
        """Generate executable FFmpeg commands from natural language.

        This method parses the request and returns the final FFmpeg commands
        ready for execution.

        Args:
            request: Natural language description of the media operation.
            assume_yes: If True, add -y flag to overwrite existing files.
            output_dir: Optional directory for output files.

        Returns:
            List of FFmpeg commands, where each command is a list of arguments.

        Raises:
            ValidationError: If the request is invalid.
            TranslationError: If the request cannot be parsed.
            ConfigError: If there's an issue with the Ollama configuration.
        """
        plan = self.generate_plan(request, output_dir=output_dir)
        return construct_operations(plan, assume_yes=assume_yes)

    def generate_command(
        self,
        request: str,
        return_raw: bool = False,
        assume_yes: bool = True,
        output_dir: Path | str | None = None,
    ) -> list[list[str]] | CommandPlan:
        """Generate FFmpeg commands from natural language request.

        .. deprecated:: 0.0.4
            Use :meth:`generate_plan` or :meth:`generate_commands` instead.
            This method will be removed in v0.1.0.

        Args:
            request: Natural language description of the media operation.
            return_raw: If True, return CommandPlan instead of commands.
            assume_yes: If True, add -y flag to overwrite existing files.
            output_dir: Optional directory for output files.

        Returns:
            Either a list of FFmpeg commands or a CommandPlan depending on return_raw.
        """
        warnings.warn(
            "generate_command() is deprecated. Use generate_plan() or generate_commands() instead. "
            "This method will be removed in v0.1.0.",
            DeprecationWarning,
            stacklevel=2,
        )

        if return_raw:
            return self.generate_plan(request, output_dir=output_dir)
        return self.generate_commands(request, assume_yes=assume_yes, output_dir=output_dir)

    @property
    def available_files(self) -> dict[str, list[str]]:
        """Get dictionary of available media files by category.

        Note: This property calls scan_workspace() internally if workspace
        hasn't been scanned yet.

        Returns:
            Dictionary with keys 'videos', 'audios', 'images', 'subtitles'.
        """
        workspace = self._ensure_workspace()
        return {
            "videos": workspace.get("videos", []),
            "audios": workspace.get("audios", []),
            "images": workspace.get("images", []),
            "subtitles": workspace.get("subtitle_files", []),
        }
