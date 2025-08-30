#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

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
        import ollama  # lazy import for testability

        logger.debug(f"Initializing Ollama provider with model: {model_name} at {host}")

        try:
            self.client = ollama.Client(host=host)
            self.model_name = model_name
            self.host = host

            self._test_connection()

        except Exception as e:
            sanitized_error = sanitize_error_message(str(e))
            logger.error(f"Failed to initialize Ollama client: {sanitized_error}")
            raise

    def _test_connection(self) -> None:
        """Test connection and ensure model is available."""
        logger.debug(f"Testing connection to Ollama at {self.host}")
        try:
            models = self.client.list()
            available_models = self._extract_available_models(models)
            logger.debug(f"Found {len(available_models)} available models: {available_models}")

            if self.model_name not in available_models:
                logger.warning(f"Model {self.model_name} not found locally. Attempting to download...")
                # Try to download the model using the spinner
                from ..utils.model_manager import ensure_model_available

                logger.debug(f"Initiating download for model {self.model_name}")
                if not ensure_model_available(self.model_name, use_spinner=True):
                    logger.error(f"Failed to download model {self.model_name}")
                    raise RuntimeError(
                        f"Model {self.model_name} is not available and could not be downloaded. "
                        f"Available models: {available_models}. "
                        f"You can manually download it with: ollama pull {self.model_name}"
                    )
            else:
                logger.debug(f"Model {self.model_name} is available locally")
        except Exception as test_e:
            # Only show warning if it's not a simple KeyError about 'name'
            error_msg = str(test_e)
            if "'name'" not in error_msg.lower():
                logger.warning(f"Could not verify model availability: {error_msg}")
            else:
                logger.debug(f"Model listing API format issue: {error_msg}")

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
                    # Try different possible keys in order of preference
                    model_name = m.get("model") or m.get("name") or str(m)
                    available_models.append(model_name)
                elif hasattr(m, "model"):
                    available_models.append(m.model)
                else:
                    available_models.append(str(m))

        logger.debug(f"Extracted {len(available_models)} model names")
        return available_models

    def process_query(self, system: str, user: str, timeout: int) -> str:
        """Process query with error handling and retries."""
        try:
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
            import ollama

            if isinstance(e, ollama.ResponseError):
                error_msg = str(e.error) if hasattr(e, "error") else str(e)
                logger.error(f"Ollama response error: {error_msg}")

                if "model not found" in error_msg.lower():
                    raise TranslationError(
                        f"Model '{self.model_name}' not found on Ollama server. Please install it with: ollama pull {self.model_name}"
                    ) from e
                if "connection refused" in error_msg.lower():
                    raise TranslationError(
                        f"Cannot connect to Ollama server at {self.host}. Please ensure Ollama is running with: ollama serve"
                    ) from e
                raise TranslationError(
                    f"Ollama error: {error_msg}. Try these troubleshooting steps: 1. Check if Ollama is running: ollama serve | 2. Verify the model is installed: ollama pull {self.model_name} | 3. List available models: ollama list"
                ) from e

        except ImportError:
            # Fallback for missing ollama package
            pass

        # Handle connection errors
        if "connection refused" in str(e).lower() or "connection failed" in str(e).lower():
            logger.error(f"Connection to Ollama server failed: {e}")
            raise TranslationError(
                f"Cannot connect to Ollama server at {self.host}. Please ensure Ollama is running with: ollama serve"
            ) from e

        # Handle timeout errors
        if "timeout" in str(e).lower():
            logger.error("Ollama request timed out")
            raise TranslationError(
                f'Ollama request timed out. Try: 1. Increase timeout: mediallm --timeout 120 "your command" | 2. Check if model is loaded: ollama ps | 3. Pull model if needed: ollama pull {self.model_name}'
            ) from e

        # Generic error handling for unknown exceptions
        sanitized_error = sanitize_error_message(str(e))
        logger.error(f"Unexpected error during Ollama request: {sanitized_error}")
        raise TranslationError(
            f"Failed to get response from Ollama: {sanitized_error}. Please check your Ollama installation and try again."
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
