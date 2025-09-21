#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import importlib
import time
from typing import TYPE_CHECKING
from typing import Any

from ..safety.data_protection import create_secure_logger
from ..safety.data_protection import sanitize_error_message
from ..utils.exceptions import TranslationError
from .query_parser import QueryParser

if TYPE_CHECKING:
    from ..utils.data_models import MediaIntent

logger = create_secure_logger(__name__)


class AIProvider:
    """Abstract base class for local model providers."""

    def process_query(self, system: str, user: str, timeout: int) -> str:
        """Process query request with the local model."""
        raise NotImplementedError


class OllamaAdapter(AIProvider):
    """Ollama local model provider implementation."""

    def __init__(self, host: str, model_name: str) -> None:
        """Initialize Ollama provider with host and model."""
        self.host = host
        self.model_name = model_name
        self.client = None  # Will be created immediately below

        # Initialize client eagerly so initialization failures surface early
        self._ensure_client_initialized()

    def _ensure_client_initialized(self) -> None:
        """Create an Ollama client instance lazily when first needed."""
        if self.client is not None:
            return

        try:
            logger.debug(f"Creating Ollama client for host: {self.host}")
            ollama_module = importlib.import_module("ollama")
            self.client = ollama_module.Client(host=self.host)
        except Exception as e:
            sanitized_error = sanitize_error_message(str(e))
            logger.error(f"Failed to create Ollama client: {sanitized_error}")
            raise

    def _ensure_model_available_via_client(self) -> None:
        """Ensure the requested model exists; pull when missing."""
        try:
            models = self.client.list()
            available_models = self._extract_available_models(models)
            if self.model_name in available_models:
                logger.debug(f"Model {self.model_name} already present on host {self.host}")
                return

            logger.info(f"Model {self.model_name} not found. Attempting remote pull via Ollama API...")

            pull_result = self.client.pull(self.model_name)
            try:
                for _ in pull_result:  # type: ignore[assignment]
                    pass
            except TypeError:
                pass

            # Wait until the model appears in list/show to avoid race conditions
            self._wait_for_model_availability(timeout_seconds=600.0, poll_interval_seconds=2.0)

            logger.info(f"Successfully ensured model availability: {self.model_name}")

        except Exception as e:
            # Convert to a helpful TranslationError for the higher layers
            sanitized_error = sanitize_error_message(str(e))
            logger.error(f"Failed ensuring model availability via client: {sanitized_error}")
            raise TranslationError(
                f"Failed to ensure model '{self.model_name}' on {self.host}: {sanitized_error}. "
                f"Verify that your Ollama server is reachable and has permissions to pull models."
            ) from e

    def _extract_available_models(self, models: Any) -> list[str]:
        """Extract available model names from models response."""
        logger.debug("Extracting model names from Ollama response")
        available_models = []

        # Handle both dictionary and object responses from different ollama library versions
        if hasattr(models, "models"):
            # Newer API returns a response object with models attribute
            model_list = models.models
            for m in model_list or []:
                if hasattr(m, "model"):
                    available_models.append(m.model)
                elif isinstance(m, dict) and "model" in m:
                    available_models.append(m["model"])
                elif isinstance(m, dict) and "name" in m:
                    available_models.append(m["name"])
        else:
            # Older API returns a dictionary with 'models' key
            model_list = models.get("models", [])
            for m in model_list:
                if isinstance(m, dict):
                    # Try different possible keys
                    model_name = m.get("model") or m.get("name") or str(m)
                    available_models.append(model_name)
                elif hasattr(m, "model"):
                    available_models.append(m.model)
                else:
                    available_models.append(str(m))

        logger.debug(f"Extracted {len(available_models)} model names")
        return available_models

    def _wait_for_model_availability(self, timeout_seconds: float = 300.0, poll_interval_seconds: float = 0.5) -> None:
        """Wait for the model to be available using exponential backoff and two-step checks."""
        start = time.monotonic()
        delay = max(0.1, poll_interval_seconds)
        max_delay = 4.0
        last_error: str | None = None

        while True:
            elapsed = time.monotonic() - start
            if elapsed >= timeout_seconds:
                break

            try:
                # Step 1: precise readiness via show()
                if hasattr(self.client, "show"):
                    try:
                        details = self.client.show(self.model_name)  # type: ignore[attr-defined]
                        if details:
                            logger.debug("Model is available (show)")
                            return
                    except Exception as inner:
                        last_error = str(inner)

                # Step 2: fallback to list()
                try:
                    models = self.client.list()
                    names = self._extract_available_models(models)
                    if self.model_name in names:
                        logger.debug("Model is available (list)")
                        return
                except Exception as e_inner:
                    last_error = str(e_inner)

            except Exception as e_outer:
                last_error = str(e_outer)

            time.sleep(delay)
            delay = min(max_delay, delay * 2)

        sanitized = sanitize_error_message(last_error or "timeout waiting for model availability")
        raise TranslationError(
            f"Model '{self.model_name}' did not become available on {self.host} "
            f"within {int(timeout_seconds)}s: {sanitized}. "
            f"If this persists, try pulling manually: ollama pull {self.model_name}"
        )

    def process_query(self, system: str, user: str, timeout: int) -> str:
        """Process query with error handling and retries."""
        try:
            # Initialize client lazily
            self._ensure_client_initialized()

            # Ensure the requested model exists (pull if missing)
            self._ensure_model_available_via_client()

            logger.debug(f"Making Ollama request with model: {self.model_name}, timeout: {timeout}s")

            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]

            logger.debug(f"Sending chat request to model {self.model_name}")
            response = self.client.chat(
                model=self.model_name,
                messages=messages,
                stream=False,
                format="json",  # Force JSON output format
                options={
                    "timeout": timeout,
                    "temperature": 0.1,  # Low temperature for consistent JSON output
                    "top_p": 0.9,
                },
            )
            logger.debug("Received response from Ollama")

            content = response.get("message", {}).get("content", "{}")
            logger.debug(f"Received response length: {len(content)} characters")
            return content

        except Exception as e:
            logger.debug(f"Error during Ollama request: {type(e).__name__}")
            return self._handle_error(e)

    def _handle_error(self, e: Exception) -> str:
        """Handle various types of errors from Ollama."""
        logger.debug(f"Handling Ollama error: {type(e).__name__}: {str(e)[:100]}...")
        # Import specific exception types for better handling
        try:
            ollama_module = importlib.import_module("ollama")
            if isinstance(e, ollama_module.ResponseError):
                error_msg = str(e.error) if hasattr(e, "error") else str(e)
                logger.error(f"Ollama response error: {error_msg}")

                if "model not found" in error_msg.lower():
                    raise TranslationError(
                        f"Model '{self.model_name}' not found on Ollama server. "
                        f"Please install it with: ollama pull {self.model_name}"
                    ) from e
                if "connection refused" in error_msg.lower():
                    raise TranslationError(
                        f"Cannot connect to Ollama server at {self.host}. "
                        f"Please ensure Ollama is running with: ollama serve"
                    ) from e
                raise TranslationError(
                    f"Ollama error: {error_msg}. Try these troubleshooting steps: "
                    "1. Check if Ollama is running: ollama serve | "
                    f"2. Verify the model is installed: ollama pull {self.model_name} | "
                    "3. List available models: ollama list"
                ) from e

        except ImportError:
            # Fallback for missing ollama package
            pass

        # Handle connection errors
        if "connection refused" in str(e).lower() or "connection failed" in str(e).lower():
            logger.error(f"Connection to Ollama server failed: {e}")
            raise TranslationError(
                f"Cannot connect to Ollama server at {self.host}. "
                f"Please ensure Ollama is running with: ollama serve"
            ) from e

        # Handle timeout errors
        if "timeout" in str(e).lower():
            logger.error("Ollama request timed out")
            raise TranslationError(
                "Ollama request timed out. Try: "
                "1. Increase timeout: mediallm --timeout 120 'your command' | "
                "2. Check if model is loaded: ollama ps | "
                f"3. Pull model if needed: ollama pull {self.model_name}"
            ) from e

        # Generic error handling for unknown exceptions
        sanitized_error = sanitize_error_message(str(e))
        logger.error(f"Unexpected error during Ollama request: {sanitized_error}")
        raise TranslationError(
            f"Failed to get response from Ollama: {sanitized_error}. "
            "Please check your Ollama installation and try again."
        ) from e


class LLM:
    """High-level model interface for parsing natural language into ffmpeg tasks."""

    def __init__(self, provider: AIProvider) -> None:
        """Initialize model interface with a provider."""
        logger.debug(f"Initializing LLM with provider: {type(provider).__name__}")
        self._provider = provider
        self._query_parser = QueryParser(provider)

    def parse_query(self, user_query: str, workspace: dict[str, Any], timeout: int | None = None) -> MediaIntent:
        """Parse natural language query into MediaIntent with retry logic."""
        logger.debug(f"Starting query parsing for: '{user_query[:50]}{'...' if len(user_query) > 50 else ''}'")
        result = self._query_parser.parse_query(user_query, workspace, timeout)
        logger.debug(f"Query parsing completed, action: {result.action.value if result.action else 'unknown'}")
        return result
