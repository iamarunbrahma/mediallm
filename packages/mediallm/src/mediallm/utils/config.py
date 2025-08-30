#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import os
import shutil
from typing import Final

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic import Field
from pydantic import ValidationError
from pydantic import field_validator

from ..safety.data_protection import create_secure_logger
from .exceptions import ConfigError

# Create secure logger
logger = create_secure_logger(__name__)


class ConfigDefaults:
    """Configuration default values and constants."""

    DEFAULT_HOST: Final[str] = "http://localhost:11434"
    DEFAULT_MODEL: Final[str] = "llama3.1:latest"
    DEFAULT_TIMEOUT: Final[int] = 60
    DEFAULT_MAX_FILE_SIZE: Final[int] = 500 * 1024 * 1024  # 500MB
    DEFAULT_RATE_LIMIT: Final[int] = 60
    DEFAULT_OUTPUT_DIR: Final[str] = "outputs"

    MIN_TIMEOUT: Final[int] = 1
    MAX_TIMEOUT: Final[int] = 300
    MIN_RATE_LIMIT: Final[int] = 1
    MAX_RATE_LIMIT: Final[int] = 1000

    TRUTHY_VALUES: Final[set[str]] = {"1", "true", "yes"}


class AppConfig(BaseModel):
    """Runtime configuration loaded from environment variables."""

    ollama_host: str = Field(default_factory=lambda: os.getenv("MEDIALLM_OLLAMA_HOST", ConfigDefaults.DEFAULT_HOST))
    model_name: str = Field(default_factory=lambda: os.getenv("MEDIALLM_MODEL", ConfigDefaults.DEFAULT_MODEL))
    dry_run: bool = Field(
        default_factory=lambda: os.getenv("MEDIALLM_DRY_RUN", "false").lower() in ConfigDefaults.TRUTHY_VALUES
    )
    confirm_default: bool = Field(default=True)
    timeout_seconds: int = Field(
        default=ConfigDefaults.DEFAULT_TIMEOUT,
        ge=ConfigDefaults.MIN_TIMEOUT,
        le=ConfigDefaults.MAX_TIMEOUT,
    )
    max_file_size: int = Field(default=ConfigDefaults.DEFAULT_MAX_FILE_SIZE)
    allowed_directories: list[str] = Field(default_factory=lambda: [os.getcwd()])
    rate_limit_requests: int = Field(
        default=ConfigDefaults.DEFAULT_RATE_LIMIT,
        ge=ConfigDefaults.MIN_RATE_LIMIT,
        le=ConfigDefaults.MAX_RATE_LIMIT,
    )
    output_directory: str = Field(default=ConfigDefaults.DEFAULT_OUTPUT_DIR)

    @field_validator("ollama_host")
    @classmethod
    def validate_ollama_host(cls, v: str) -> str:
        """Validate Ollama host URL format."""
        if not v or not isinstance(v, str):
            raise ValueError("Ollama host URL is required")

        # Basic URL validation
        if not (v.startswith(("http://", "https://"))):
            raise ValueError("Ollama host must start with http:// or https://")

        return v.rstrip("/")  # Remove trailing slash

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model name format - accepts any valid Ollama model name."""
        if not v or not isinstance(v, str):
            raise ValueError("Model name is required")

        # Allow any model name that follows Ollama's naming convention
        # Format: name[:tag] where tag is optional
        # Just check for basic validity - actual availability will be checked at runtime
        if not v.strip():
            raise ValueError("Model name cannot be empty")

        # Log which model is being used
        logger.debug(f"Using model: {v}")

        return v

    @field_validator("allowed_directories", mode="before")
    @classmethod
    def validate_directories(cls, v: list[str] | str) -> list[str]:
        """Validate and normalize allowed directories."""
        if isinstance(v, str):
            v = [v]

        validated_dirs = []
        for dir_path in v:
            try:
                abs_path = os.path.abspath(dir_path)
                if os.path.exists(abs_path) and os.path.isdir(abs_path):
                    validated_dirs.append(abs_path)
                else:
                    logger.warning(f"Directory does not exist or is not accessible: {dir_path}")
            except (OSError, ValueError) as e:
                logger.warning(f"Invalid directory path {dir_path}: {e}")

        if not validated_dirs:
            # Fallback to current directory if no valid directories
            validated_dirs = [os.getcwd()]

        return validated_dirs

    @field_validator("output_directory")
    @classmethod
    def validate_output_directory(cls, v: str) -> str:
        """Validate and normalize output directory path without creating it."""
        if not v or not isinstance(v, str):
            raise ValueError("Output directory is required")

        try:
            abs_path = os.path.abspath(v)
            # Only validate that the path is valid, don't create it
            # If path exists, ensure it's a directory
            if os.path.exists(abs_path) and not os.path.isdir(abs_path):
                raise ValueError(f"Output directory path exists but is not a directory: {v}")

            return abs_path
        except (OSError, ValueError) as e:
            logger.warning(f"Invalid output directory path {v}: {e}")
            # Fallback to "outputs" in current directory (but don't create it)
            return os.path.abspath("outputs")

    def validate_ffmpeg_available(self) -> None:
        """Validate that ffmpeg is available in PATH."""
        if shutil.which("ffmpeg") is None:
            raise ConfigError(
                "ffmpeg not found in PATH. Please install it: macOS: brew install ffmpeg | Ubuntu/Debian: sudo apt install ffmpeg | Windows: choco install ffmpeg"
            )

    def validate_ollama_connection(self) -> None:
        """Validate that Ollama server is accessible."""
        try:
            import ollama

            # Test connection by creating a client and listing models
            client = ollama.Client(host=self.ollama_host)
            models = client.list()

            available_models = [m["name"] for m in models.get("models", [])]
            logger.debug(f"Available Ollama models: {available_models}")

            # Don't fail if no models are available - we can download them
            if not available_models:
                logger.debug(
                    f"No models found on Ollama server at {self.ollama_host}. "
                    f"Model {self.model_name} will be downloaded when needed."
                )
            elif self.model_name not in available_models:
                logger.debug(
                    f"Model '{self.model_name}' not found on server. "
                    f"It will be downloaded automatically when needed."
                )

        except ImportError as e:
            raise ConfigError("Ollama package not installed. Please install with: uv add ollama") from e
        except Exception as e:
            error_msg = str(e).lower()
            if "connection refused" in error_msg or "connection failed" in error_msg:
                raise ConfigError(
                    f"Cannot connect to Ollama server at {self.ollama_host}. "
                    "Please ensure Ollama is running with: ollama serve"
                ) from e
            raise ConfigError(
                f"Failed to validate Ollama connection: {e}. "
                "Try these troubleshooting steps:\n"
                "1. Start Ollama: ollama serve\n"
                "2. Check installation: curl -fsSL https://ollama.com/install.sh | sh\n"
                "3. Verify server status: curl http://localhost:11434/api/version"
            ) from e

    def ensure_model_available_after_override(self, original_model_name: str) -> None:
        """Ensure model is available after CLI override, with fallback if needed.

        This method should be called after CLI arguments have overridden the model_name.
        It handles user-specified models by attempting to download them first.

        Args:
            original_model_name: The original model name before CLI override
        """
        # Only process if model was actually changed (user specified via CLI)
        if self.model_name == original_model_name:
            return

        try:
            from .model_manager import ensure_model_available
            from .model_manager import get_best_available_model

            # User explicitly specified this model via CLI - try to ensure it's available
            logger.debug(f"Attempting to ensure CLI-specified model {self.model_name} is available...")

            try:
                # Try to download the exact model requested
                if ensure_model_available(self.model_name, use_spinner=True):
                    logger.debug(f"Successfully ensured model {self.model_name} is available")
                else:
                    # Download failed or model doesn't exist
                    logger.error(f"Failed to download model {self.model_name}")
                    logger.debug("Falling back to best available model...")

                    # Fall back to best available model
                    best_model = get_best_available_model()
                    if best_model != self.model_name:
                        logger.warning(
                            f"CLI-specified model '{self.model_name}' could not be obtained. "
                            f"Using '{best_model}' instead."
                        )
                        self.model_name = best_model
            except Exception as e:
                # Handle any errors during download attempt
                logger.error(f"Error while trying to download CLI-specified model {self.model_name}: {e}")
                logger.debug("Falling back to best available model...")

                # Fall back to best available model
                best_model = get_best_available_model()
                if best_model != self.model_name:
                    logger.warning(
                        f"CLI-specified model '{self.model_name}' is not available. " f"Using '{best_model}' instead."
                    )
                    self.model_name = best_model

        except Exception as e:
            logger.warning(f"Could not ensure CLI-specified model availability: {e}")
            # Continue with CLI-specified model name


class ConfigLoader:
    """Handles configuration loading and validation."""

    _ENV_VAR_PREFIX: Final[str] = "MEDIALLM_"
    _CONFIG_ERROR_MESSAGE: Final[str] = (
        "Please check your environment variables and .env file format. "
        "Optional: MEDIALLM_OLLAMA_HOST, MEDIALLM_MODEL, MEDIALLM_DRY_RUN, "
        "MEDIALLM_ALLOWED_DIRS, MEDIALLM_TIMEOUT, MEDIALLM_MAX_FILE_SIZE, MEDIALLM_RATE_LIMIT."
    )

    @classmethod
    def load_config(cls) -> AppConfig:
        """Load configuration from environment variables and validate environment."""
        load_dotenv(override=False)

        try:
            config = cls._create_config_instance()
            logger.debug(f"Configuration loaded successfully with Ollama host: {config.ollama_host}")
        except (ValidationError, ValueError) as exc:
            raise ConfigError(f"Configuration validation failed: {exc}. {cls._CONFIG_ERROR_MESSAGE}") from exc

        config.validate_ffmpeg_available()
        cls._ensure_model_availability(config)
        cls._log_configuration_summary(config)

        return config

    @classmethod
    def _create_config_instance(cls) -> AppConfig:
        """Create AppConfig instance with environment values."""
        allowed_dirs = cls._parse_allowed_directories()

        return AppConfig(
            allowed_directories=allowed_dirs,
            timeout_seconds=int(os.getenv(f"{cls._ENV_VAR_PREFIX}TIMEOUT", str(ConfigDefaults.DEFAULT_TIMEOUT))),
            max_file_size=int(
                os.getenv(
                    f"{cls._ENV_VAR_PREFIX}MAX_FILE_SIZE",
                    str(ConfigDefaults.DEFAULT_MAX_FILE_SIZE),
                )
            ),
            rate_limit_requests=int(
                os.getenv(
                    f"{cls._ENV_VAR_PREFIX}RATE_LIMIT",
                    str(ConfigDefaults.DEFAULT_RATE_LIMIT),
                )
            ),
            output_directory=os.getenv(f"{cls._ENV_VAR_PREFIX}OUTPUT_DIR", ConfigDefaults.DEFAULT_OUTPUT_DIR),
        )

    @classmethod
    def _parse_allowed_directories(cls) -> list[str]:
        """Parse allowed directories from environment variable."""
        allowed_dirs_str = os.getenv(f"{cls._ENV_VAR_PREFIX}ALLOWED_DIRS", "")
        allowed_dirs = [d.strip() for d in allowed_dirs_str.split(",") if d.strip()] if allowed_dirs_str else []
        return allowed_dirs or [os.getcwd()]

    @classmethod
    def _ensure_model_availability(cls, config: AppConfig) -> None:
        """Ensure preferred model is available."""
        try:
            from .model_manager import ensure_model_available
            from .model_manager import get_best_available_model

            user_specified_model = os.getenv(f"{cls._ENV_VAR_PREFIX}MODEL") is not None

            if user_specified_model:
                cls._handle_user_specified_model(config, ensure_model_available, get_best_available_model)
            else:
                cls._handle_default_model(config, get_best_available_model)

        except Exception as e:
            logger.warning(f"Could not ensure model availability: {e}")

    @classmethod
    def _handle_user_specified_model(cls, config: AppConfig, ensure_model_available, get_best_available_model) -> None:
        """Handle user-specified model availability."""
        logger.debug(f"Attempting to ensure model {config.model_name} is available...")

        try:
            if ensure_model_available(config.model_name, use_spinner=True):
                logger.debug(f"Successfully ensured model {config.model_name} is available")
            else:
                cls._fallback_to_best_available(config, get_best_available_model, "could not be obtained")
        except Exception as e:
            logger.error(f"Error while trying to download model {config.model_name}: {e}")
            cls._fallback_to_best_available(config, get_best_available_model, "is not available")

    @classmethod
    def _handle_default_model(cls, config: AppConfig, get_best_available_model) -> None:
        """Handle default model selection."""
        best_model = get_best_available_model(config.model_name)
        if best_model != config.model_name:
            logger.debug(f"Using model {best_model}")
            config.model_name = best_model

    @classmethod
    def _fallback_to_best_available(cls, config: AppConfig, get_best_available_model, reason: str) -> None:
        """Fallback to best available model."""
        logger.debug("Falling back to best available model...")
        best_model = get_best_available_model()

        if best_model != config.model_name:
            logger.warning(f"Model '{config.model_name}' {reason}. Using '{best_model}' instead.")
            config.model_name = best_model

    @staticmethod
    def _log_configuration_summary(config: AppConfig) -> None:
        """Log configuration summary."""
        logger.debug(
            f"mediallm configuration: model={config.model_name}, host={config.ollama_host}, "
            f"dry_run={config.dry_run}, timeout={config.timeout_seconds}s, "
            f"allowed_dirs={len(config.allowed_directories)} directories"
        )


def load_config() -> AppConfig:
    """Load configuration from environment variables and validate environment."""
    return ConfigLoader.load_config()
