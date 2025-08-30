#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Final
from typing import NamedTuple

# Import media extensions from constants
from ..constants.media_formats import MEDIA_EXTENSIONS as MEDIA_EXTS

# Initialize mimetypes for MIME type detection
mimetypes.init()

logger = logging.getLogger(__name__)


class ValidationConstants:
    """Constants for media file validation."""

    # MIME type categories for validation
    MIME_TYPE_CATEGORIES: Final[dict[str, str]] = {
        "video": "video/",
        "audio": "audio/",
        "image": "image/",
    }

    # Common MIME type mappings for problematic extensions
    MIME_OVERRIDES: Final[dict[str, str]] = {
        ".m4v": "video/mp4",
        ".m4a": "audio/mp4",
        ".webm": "video/webm",
        ".mkv": "video/x-matroska",
    }

    # Dangerous file patterns to reject
    DANGEROUS_PATTERNS: Final[list[str]] = [
        "..",  # Path traversal
        "://",  # URL schemes
        "<",
        ">",  # HTML/XML tags
    ]

    # File size limits (in bytes)
    MAX_FILE_SIZE: Final[int] = 10 * 1024 * 1024 * 1024  # 10GB


class ValidationResult(NamedTuple):
    """Result of media file validation."""

    is_valid: bool
    media_type: str | None  # "video", "audio", "image" or None
    error_message: str | None


class MediaFileValidator:
    """Comprehensive media file validator using multiple validation layers."""

    def __init__(self, enable_cache: bool = True, cache_size: int = 1000):
        """Initialize the media file validator."""
        logger.debug(f"Initializing MediaFileValidator with cache={enable_cache}, cache_size={cache_size}")
        self.supported_extensions = self._build_supported_extensions()
        self.extension_to_category = self._build_extension_mapping()
        logger.debug(f"Loaded {len(self.supported_extensions)} supported extensions")
        self._enable_cache = enable_cache
        self._cache_size = cache_size
        self._validation_cache: dict[str, ValidationResult] = {}

    @staticmethod
    def _build_supported_extensions() -> set[str]:
        """Build set of all supported extensions."""
        extensions = set()
        for category_exts in MEDIA_EXTS.values():
            extensions.update(category_exts)
        return extensions

    @staticmethod
    def _build_extension_mapping() -> dict[str, str]:
        """Build mapping from extension to media category."""
        mapping = {}
        for category, extensions in MEDIA_EXTS.items():
            for ext in extensions:
                mapping[ext] = category
        return mapping

    def validate_file(self, file_path: Path) -> ValidationResult:
        """Validate if a file is a supported media file."""
        # Check cache first
        if self._enable_cache:
            cache_key = self._get_cache_key(file_path)
            if cache_key in self._validation_cache:
                return self._validation_cache[cache_key]

        result = self._perform_validation(file_path)

        # Cache the result
        if self._enable_cache:
            self._cache_result(cache_key, result)

        return result

    def _perform_validation(self, file_path: Path) -> ValidationResult:
        """Perform the actual validation without caching."""
        # Basic file existence and type checks
        basic_validation = self._validate_file_basics(file_path)
        if not basic_validation.is_valid:
            return basic_validation

        # Extension validation
        file_extension = file_path.suffix.lower()
        extension_validation = self._validate_extension(file_path, file_extension)
        if not extension_validation.is_valid:
            return extension_validation

        # Security checks
        security_validation = self._validate_security(file_path)
        if not security_validation.is_valid:
            return security_validation

        # MIME type validation
        mime_validation = self._validate_mime_type(file_path, file_extension)
        if not mime_validation.is_valid:
            return mime_validation

        media_type = self.extension_to_category[file_extension]
        return ValidationResult(is_valid=True, media_type=media_type, error_message=None)

    def _get_cache_key(self, file_path: Path) -> str:
        """Generate cache key for file validation."""
        try:
            stat = file_path.stat()
            return f"{file_path}:{stat.st_size}:{stat.st_mtime}"
        except OSError:
            return str(file_path)

    def _cache_result(self, cache_key: str, result: ValidationResult) -> None:
        """Cache validation result with size limit."""
        if len(self._validation_cache) >= self._cache_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._validation_cache))
            del self._validation_cache[oldest_key]

        self._validation_cache[cache_key] = result

    def _validate_file_basics(self, file_path: Path) -> ValidationResult:
        """Validate basic file existence and type."""
        if not file_path.exists():
            return ValidationResult(
                is_valid=False,
                media_type=None,
                error_message=f"File not found: {file_path!s}",
            )

        if not file_path.is_file():
            return ValidationResult(
                is_valid=False,
                media_type=None,
                error_message=f"Not a file: {file_path.name}",
            )

        # Check file size
        try:
            file_size = file_path.stat().st_size
            if file_size > ValidationConstants.MAX_FILE_SIZE:
                size_gb = ValidationConstants.MAX_FILE_SIZE / (1024**3)
                return ValidationResult(
                    is_valid=False,
                    media_type=None,
                    error_message=f"File too large: {file_path.name} (max {size_gb:.1f}GB)",
                )
        except OSError:
            return ValidationResult(
                is_valid=False,
                media_type=None,
                error_message=f"Cannot access file: {file_path.name}",
            )

        return ValidationResult(is_valid=True, media_type=None, error_message=None)

    def _validate_extension(self, file_path: Path, file_extension: str) -> ValidationResult:
        """Validate file extension is supported."""
        if file_extension not in self.supported_extensions:
            supported_formats = self._get_supported_formats_message()
            return ValidationResult(
                is_valid=False,
                media_type=None,
                error_message=f"Unsupported file format: {file_path.name}. {supported_formats}",
            )
        return ValidationResult(is_valid=True, media_type=None, error_message=None)

    def _validate_security(self, file_path: Path) -> ValidationResult:
        """Validate file path for security issues."""
        file_str = str(file_path)
        for dangerous_pattern in ValidationConstants.DANGEROUS_PATTERNS:
            if dangerous_pattern in file_str:
                return ValidationResult(
                    is_valid=False,
                    media_type=None,
                    error_message=f"Potentially dangerous file path: {file_path.name}",
                )
        return ValidationResult(is_valid=True, media_type=None, error_message=None)

    def _validate_mime_type(self, file_path: Path, file_extension: str) -> ValidationResult:
        """Validate file using MIME type detection."""
        try:
            mime_type = self._detect_mime_type(file_path, file_extension)
            if mime_type is None:
                return ValidationResult(is_valid=True, media_type=None, error_message=None)

            return self._verify_mime_type_consistency(file_path, file_extension, mime_type)

        except Exception:
            # If MIME type detection fails, trust extension validation
            return ValidationResult(is_valid=True, media_type=None, error_message=None)

    def _detect_mime_type(self, file_path: Path, file_extension: str) -> str | None:
        """Detect MIME type for file."""
        # Check for override first
        if file_extension in ValidationConstants.MIME_OVERRIDES:
            return ValidationConstants.MIME_OVERRIDES[file_extension]

        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type

    def _verify_mime_type_consistency(self, file_path: Path, file_extension: str, mime_type: str) -> ValidationResult:
        """Verify MIME type matches expected category."""
        primary_mime = mime_type.split("/")[0]
        expected_category = self.extension_to_category[file_extension]

        # Check if primary MIME type matches expected category
        if primary_mime in ValidationConstants.MIME_TYPE_CATEGORIES:
            if primary_mime != expected_category:
                return ValidationResult(
                    is_valid=False,
                    media_type=None,
                    error_message=f"File type mismatch: {file_path.name} appears to be {primary_mime} but has {expected_category} extension",
                )

        return ValidationResult(is_valid=True, media_type=None, error_message=None)

    def _get_supported_formats_message(self) -> str:
        """Generate user-friendly message about supported formats.

        Returns:
            String describing all supported media formats
        """
        format_parts = []
        for category, extensions in MEDIA_EXTS.items():
            ext_list = ", ".join(sorted(extensions))
            format_parts.append(f"{category}: {ext_list}")

        return f"Supported formats: {'; '.join(format_parts)}"

    def is_media_file(self, file_path: Path) -> bool:
        """Quick check if a file is a supported media file.

        Args:
            file_path: Path to the file to check

        Returns:
            True if file is a valid media file, False otherwise
        """
        result = self.validate_file(file_path)
        return result.is_valid

    def get_media_type(self, file_path: Path) -> str | None:
        """Get the media type category of a file.

        Args:
            file_path: Path to the file

        Returns:
            Media type ("video", "audio", "image") or None if not a media file
        """
        result = self.validate_file(file_path)
        return result.media_type if result.is_valid else None


# Global validator instance for easy access
_validator_instance = MediaFileValidator()


def validate_media_file(file_path: Path | str) -> ValidationResult:
    """Validate if a file is a supported media file.

    Convenience function that uses the global validator instance.

    Args:
        file_path: Path to the file to validate (str or Path)

    Returns:
        ValidationResult with validation status and details
    """
    path_obj = Path(file_path) if isinstance(file_path, str) else file_path
    return _validator_instance.validate_file(path_obj)


def is_media_file(file_path: Path | str) -> bool:
    """Quick check if a file is a supported media file.

    Convenience function that uses the global validator instance.

    Args:
        file_path: Path to the file to check (str or Path)

    Returns:
        True if file is a valid media file, False otherwise
    """
    path_obj = Path(file_path) if isinstance(file_path, str) else file_path
    return _validator_instance.is_media_file(path_obj)


def get_media_type(file_path: Path | str) -> str | None:
    """Get the media type category of a file.

    Convenience function that uses the global validator instance.

    Args:
        file_path: Path to the file (str or Path)

    Returns:
        Media type ("video", "audio", "image") or None if not a media file
    """
    path_obj = Path(file_path) if isinstance(file_path, str) else file_path
    return _validator_instance.get_media_type(path_obj)


def validate_multiple_files(
    file_paths: list[Path | str],
) -> dict[str, ValidationResult]:
    """Validate multiple files and return results.

    Args:
        file_paths: List of file paths to validate

    Returns:
        Dictionary mapping file paths to ValidationResults
    """
    results = {}
    for file_path in file_paths:
        path_obj = Path(file_path) if isinstance(file_path, str) else file_path
        results[str(path_obj)] = validate_media_file(path_obj)

    return results
