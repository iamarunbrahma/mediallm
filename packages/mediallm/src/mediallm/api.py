#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from .analysis.workspace_scanner import discover_media
from .core.command_builder import construct_operations
from .core.llm import LLM
from .core.llm import OllamaAdapter
from .core.task_router import dispatch_task
from .utils.exceptions import TranslationError

if TYPE_CHECKING:
    from .utils.data_models import CommandPlan


class MediaLLM:
    """Main API interface for MediaLLM package."""

    def __init__(
        self,
        workspace: dict[str, Any] | None = None,
        ollama_host: str = "http://localhost:11434",
        model_name: str = "llama3.1:latest",
        timeout: int = 60,
        working_dir: Path | str | None = None,
    ) -> None:
        """Initialize MediaLLM API."""
        self._working_dir = Path(working_dir) if working_dir else Path.cwd()
        self._timeout = timeout
        self._workspace: dict[str, Any] | None = None
        self._llm = self._initialize_llm(ollama_host, model_name)

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
        """Get the workspace, initializing if needed."""
        if self._workspace is None:
            self._workspace = self._scan_workspace()
        return self._workspace

    def _initialize_llm(self, ollama_host: str, model_name: str) -> LLM:
        """Initialize the LLM provider."""
        try:
            provider = OllamaAdapter(host=ollama_host, model_name=model_name)
            return LLM(provider)
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Ollama provider. Please ensure:\n"
                f"1. Ollama is running: ollama serve\n"
                f"2. Model is available: ollama pull {model_name}\n"
                f"Original error: {e}"
            ) from e

    def _scan_workspace(self) -> dict[str, Any]:
        """Scan workspace for media files."""
        return discover_media(cwd=self._working_dir, show_summary=False)

    def _validate_request(self, request: str) -> None:
        """Validate the input request."""
        if not request or not request.strip():
            raise ValueError("Request cannot be empty")

        if len(request) > 10000:  # Reasonable limit
            raise ValueError("Request too long (max 10000 characters)")

    def generate_command(
        self,
        request: str,
        return_raw: bool = False,
        assume_yes: bool = True,
    ) -> list[list[str]] | CommandPlan:
        """Generate FFmpeg commands from natural language request."""
        self._validate_request(request)

        try:
            # Parse natural language to intent
            intent = self._llm.parse_query(request, self.workspace, timeout=self._timeout)

            # Convert intent to command plan
            allowed_dirs = [self._working_dir]
            plan = dispatch_task(intent, allowed_dirs=allowed_dirs)

            if return_raw:
                return plan

            # Build executable commands
            return construct_operations(plan, assume_yes=assume_yes)

        except TranslationError:
            # Re-raise translation errors as-is (they have good error messages)
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to generate commands for request: '{request}'. " f"Error: {e}") from e

    def scan_workspace(self, directory: Path | str | None = None) -> dict[str, Any]:
        """Scan directory for media files and update workspace."""
        scan_dir = Path(directory) if directory else self._working_dir
        self._workspace = discover_media(cwd=scan_dir, show_summary=False)
        return self._workspace

    @property
    def available_files(self) -> dict[str, list[str]]:
        """Get dictionary of available media files by category."""
        return {
            "videos": self.workspace.get("videos", []),
            "audios": self.workspace.get("audios", []),
            "images": self.workspace.get("images", []),
            "subtitles": self.workspace.get("subtitle_files", []),
        }
