#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import subprocess
import sys
import time
from typing import Final

from ..safety.data_protection import create_secure_logger
from .exceptions import ConfigError

# Create secure logger
logger = create_secure_logger(__name__)


class ModelManager:
    """Manages Ollama model operations and availability."""

    # Model configuration
    _PREFERRED_MODELS: Final[list[str]] = [
        "llama3.1:latest",
        "llama3:latest",
    ]

    # Timeout and monitoring constants
    _DEFAULT_PULL_TIMEOUT: Final[int] = 1800  # 30 minutes
    _VERSION_CHECK_TIMEOUT: Final[int] = 10
    _LIST_TIMEOUT: Final[int] = 30
    _PROCESS_WAIT_TIMEOUT: Final[int] = 5
    _NO_OUTPUT_TIMEOUT: Final[int] = 60
    _POLLING_INTERVAL: Final[float] = 0.5

    # Buffer settings
    _SUBPROCESS_BUFSIZE: Final[int] = 1

    @classmethod
    def check_ollama_available(cls) -> bool:
        """Check if Ollama CLI is available in the system."""
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=cls._VERSION_CHECK_TIMEOUT,
                check=False,
            )
            return result.returncode == 0
        except (
            subprocess.TimeoutExpired,
            FileNotFoundError,
            subprocess.SubprocessError,
        ):
            return False

    @classmethod
    def list_available_models(cls) -> list[str]:
        """Get list of locally available Ollama models."""
        if not cls.check_ollama_available():
            raise ConfigError("Ollama CLI not found. Please install Ollama first.")

        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=cls._LIST_TIMEOUT,
                check=False,
            )

            if result.returncode != 0:
                raise ConfigError(f"Failed to list models: {result.stderr}")

            models = cls._parse_model_list_output(result.stdout)
            logger.debug(f"Found {len(models)} locally available models: {models}")
            return models

        except subprocess.TimeoutExpired:
            raise ConfigError("Timeout while listing models")
        except (subprocess.SubprocessError, OSError) as e:
            raise ConfigError(f"Error listing models: {e}")

    @staticmethod
    def _parse_model_list_output(stdout: str) -> list[str]:
        """Parse ollama list output to extract model names."""
        models = []
        lines = stdout.strip().split("\n")

        # Skip header line (NAME, ID, SIZE, MODIFIED)
        for line in lines[1:]:
            if line.strip():
                model_name = line.split()[0]
                models.append(model_name)

        return models

    @classmethod
    def is_model_available(cls, model_name: str) -> bool:
        """Check if a specific model is available locally."""
        try:
            available_models = cls.list_available_models()
            return model_name in available_models
        except ConfigError:
            return False

    @classmethod
    def pull_model_with_progress(cls, model_name: str, timeout: int | None = None) -> bool:
        """Pull a model from Ollama registry with progress monitoring."""
        if not cls.check_ollama_available():
            raise ConfigError("Ollama CLI not found. Please install Ollama first.")

        if timeout is None:
            timeout = cls._DEFAULT_PULL_TIMEOUT

        logger.info(f"Pulling model {model_name}... This may take several minutes.")

        try:
            process = cls._start_pull_process(model_name)
            return cls._monitor_pull_progress(process, model_name, timeout)

        except subprocess.SubprocessError as e:
            raise ConfigError(f"Error pulling model {model_name}: {e}")
        except KeyboardInterrupt:
            logger.info("Model pull cancelled by user")
            if "process" in locals():
                process.terminate()
                process.wait(timeout=cls._PROCESS_WAIT_TIMEOUT)
            return False

    @classmethod
    def _start_pull_process(cls, model_name: str) -> subprocess.Popen:
        """Start the model pull subprocess."""
        return subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=cls._SUBPROCESS_BUFSIZE,
            universal_newlines=True,
        )

    @classmethod
    def _monitor_pull_progress(cls, process: subprocess.Popen, model_name: str, timeout: int) -> bool:
        """Monitor pull process progress and handle output."""
        start_time = time.time()
        last_output_time = start_time

        while True:
            if process.poll() is not None:
                break

            current_time = time.time()
            if current_time - start_time > timeout:
                process.terminate()
                process.wait(timeout=cls._PROCESS_WAIT_TIMEOUT)
                raise ConfigError(f"Model pull timed out after {timeout} seconds")

            # Read and display output
            try:
                line = process.stdout.readline()
                if line:
                    last_output_time = current_time
                    print(f"\r{line.strip()}", end="", flush=True)
                elif current_time - last_output_time > cls._NO_OUTPUT_TIMEOUT:
                    logger.warning("No progress output for 60 seconds...")
            except (OSError, ValueError):
                break

            time.sleep(cls._POLLING_INTERVAL)

        return cls._handle_pull_completion(process, model_name)

    @classmethod
    def _handle_pull_completion(cls, process: subprocess.Popen, model_name: str) -> bool:
        """Handle pull process completion and return result."""
        return_code = process.wait()

        if return_code == 0:
            print()  # New line after progress output
            logger.info(f"Successfully pulled model: {model_name}")
            return True
        remaining_output = cls._get_remaining_output(process)
        error_msg = f"Failed to pull model {model_name} (exit code {return_code})"
        if remaining_output.strip():
            error_msg += f": {remaining_output.strip()}"
        raise ConfigError(error_msg)

    @staticmethod
    def _get_remaining_output(process: subprocess.Popen) -> str:
        """Get any remaining output from the process."""
        try:
            return process.stdout.read() or ""
        except (OSError, ValueError):
            return ""

    @classmethod
    def pull_model_with_spinner(cls, model_name: str, timeout: int | None = None) -> bool:
        """Pull a model from Ollama registry using spinner for progress display."""
        if not cls.check_ollama_available():
            raise ConfigError("Ollama CLI not found. Please install Ollama first.")

        if timeout is None:
            timeout = cls._DEFAULT_PULL_TIMEOUT

        from rich.console import Console

        from ..interface.spinner import show_llm_spinner

        console = Console()
        logger.info(f"Downloading model {model_name}...")

        spinner = show_llm_spinner(console, f"Downloading {model_name}", allow_escape=True)

        try:
            process = cls._start_pull_process(model_name)
            return cls._monitor_spinner_pull(process, model_name, timeout, spinner, console)

        except subprocess.SubprocessError as e:
            spinner.stop()
            raise ConfigError(f"Error pulling model {model_name}: {e}")
        except KeyboardInterrupt:
            logger.info("Model pull cancelled by user")
            spinner.stop()
            if "process" in locals():
                process.terminate()
                process.wait(timeout=cls._PROCESS_WAIT_TIMEOUT)
            return False
        except Exception:
            spinner.stop()
            raise

    @classmethod
    def _monitor_spinner_pull(cls, process: subprocess.Popen, model_name: str, timeout: int, spinner, console) -> bool:
        """Monitor pull process with spinner display."""
        start_time = time.time()
        last_output_time = start_time

        while True:
            if process.poll() is not None:
                break

            if spinner.is_interrupted():
                process.terminate()
                process.wait(timeout=cls._PROCESS_WAIT_TIMEOUT)
                spinner.stop()
                logger.info("Model download cancelled by user")
                return False

            current_time = time.time()
            if current_time - start_time > timeout:
                process.terminate()
                process.wait(timeout=cls._PROCESS_WAIT_TIMEOUT)
                spinner.stop()
                raise ConfigError(f"Model pull timed out after {timeout} seconds")

            # Read output but don't display (spinner handles UI)
            try:
                line = process.stdout.readline()
                if line:
                    last_output_time = current_time
                    logger.debug(f"Pull progress: {line.strip()}")
                elif current_time - last_output_time > cls._NO_OUTPUT_TIMEOUT:
                    logger.warning("No progress output for 60 seconds...")
            except (OSError, ValueError):
                break

            time.sleep(cls._POLLING_INTERVAL)

        return_code = process.wait()
        spinner.stop()

        if return_code == 0:
            console.print(f"[green]✓[/green] Successfully downloaded model: [white]{model_name}[/white]")
            logger.info(f"Successfully pulled model: {model_name}")
            return True
        remaining_output = cls._get_remaining_output(process)
        error_msg = f"Failed to pull model {model_name} (exit code {return_code})"
        if remaining_output.strip():
            error_msg += f": {remaining_output.strip()}"
        raise ConfigError(error_msg)

    @classmethod
    def ensure_model_available(cls, model_name: str, use_spinner: bool = True) -> bool:
        """Ensure a specific model is available, downloading if necessary."""
        if cls.is_model_available(model_name):
            logger.info(f"Model {model_name} is already available")
            return True

        logger.info(f"Model {model_name} not found locally, downloading...")

        try:
            if use_spinner:
                return cls.pull_model_with_spinner(model_name)
            return cls.pull_model_with_progress(model_name)
        except ConfigError as e:
            logger.error(f"Failed to download model {model_name}: {e}")
            return False
        except KeyboardInterrupt:
            logger.info("Model download cancelled by user")
            return False

    @classmethod
    def ensure_preferred_model_available(cls) -> str:
        """Ensure a preferred model is available, pulling if necessary."""
        logger.info("Checking for preferred models...")

        # Check if any preferred model is already available
        available_preferred = cls._check_preferred_models_available()
        if available_preferred:
            return available_preferred

        # Try to pull preferred models
        pulled_model = cls._attempt_pull_preferred_models()
        if pulled_model:
            return pulled_model

        # Fallback to any available model
        return cls._get_fallback_model()

    @classmethod
    def _check_preferred_models_available(cls) -> str | None:
        """Check if any preferred model is already available."""
        for model_name in cls._PREFERRED_MODELS:
            if cls.is_model_available(model_name):
                logger.info(f"Using available model: {model_name}")
                return model_name
        return None

    @classmethod
    def _attempt_pull_preferred_models(cls) -> str | None:
        """Attempt to pull preferred models in order."""
        for model_name in cls._PREFERRED_MODELS:
            logger.info(f"Attempting to pull preferred model: {model_name}")
            try:
                if cls.pull_model_with_spinner(model_name):
                    logger.info(f"Successfully obtained model: {model_name}")
                    return model_name
            except ConfigError as e:
                logger.warning(f"Failed to pull {model_name}: {e}")
                continue
            except KeyboardInterrupt:
                logger.info("Model pull cancelled by user")
                sys.exit(1)
        return None

    @classmethod
    def _get_fallback_model(cls) -> str:
        """Get fallback model if no preferred models are available."""
        try:
            available_models = cls.list_available_models()
        except ConfigError:
            available_models = []

        if available_models:
            fallback_model = available_models[0]
            logger.warning(f"Could not obtain preferred models. Using fallback: {fallback_model}")
            return fallback_model
        raise ConfigError(
            "No models available and could not pull preferred models. "
            "Please ensure Ollama is running and try: ollama pull llama3:latest"
        )

    @classmethod
    def get_best_available_model(cls, requested_model: str | None = None) -> str:
        """Get the best available model, preferring requested then preferred models."""
        if requested_model:
            if cls.is_model_available(requested_model):
                return requested_model
            logger.warning(f"Requested model {requested_model} not available locally")

        return cls.ensure_preferred_model_available()


# Backward compatibility wrapper functions
def check_ollama_available() -> bool:
    """Check if Ollama CLI is available in the system."""
    return ModelManager.check_ollama_available()


def list_available_models() -> list[str]:
    """Get list of locally available Ollama models."""
    return ModelManager.list_available_models()


def is_model_available(model_name: str) -> bool:
    """Check if a specific model is available locally."""
    return ModelManager.is_model_available(model_name)


def pull_model_with_progress(model_name: str, timeout: int = 1800) -> bool:
    """Pull a model from Ollama registry with progress monitoring."""
    return ModelManager.pull_model_with_progress(model_name, timeout)


def pull_model_with_spinner(model_name: str, timeout: int = 1800) -> bool:
    """Pull a model from Ollama registry using spinner for progress display."""
    return ModelManager.pull_model_with_spinner(model_name, timeout)


def ensure_model_available(model_name: str, use_spinner: bool = True) -> bool:
    """Ensure a specific model is available, downloading if necessary."""
    return ModelManager.ensure_model_available(model_name, use_spinner)


def ensure_preferred_model_available() -> str:
    """Ensure a preferred model is available, pulling if necessary."""
    return ModelManager.ensure_preferred_model_available()


def get_best_available_model(requested_model: str | None = None) -> str:
    """Get the best available model, preferring llama3:latest."""
    return ModelManager.get_best_available_model(requested_model)


# Export the preferred models for external use
PREFERRED_MODELS = ModelManager._PREFERRED_MODELS
