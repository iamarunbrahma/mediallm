#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from ..constants.media_formats import ALL_EXTENSIONS
from ..utils.media_validator import validate_media_file
from ..utils.path_utils import PathUtils


class FileConstants:
    """Constants for file utilities."""

    # Use centralized media extensions with dot prefix
    MEDIA_EXTENSIONS: Final[set[str]] = {f".{ext}" for ext in ALL_EXTENSIONS}

    OUTPUT_INDICATORS: Final[list[str]] = [
        "to",
        "into",
        "as",
        "output",
        "save",
        "export",
        "create",
        "generate",
    ]

    MAX_WORDS_BETWEEN_TO: Final[int] = 2
    AT_PATTERN: Final[str] = r"@([^\s]+)"


def parse_file_references(user_input: str) -> tuple[str, list[str]]:
    """Parse @ file references from user input with media file validation."""
    matches = re.findall(FileConstants.AT_PATTERN, user_input)

    referenced_files = []
    processed_input = user_input
    missing_files = []
    media_validation_errors = []

    for filename in matches:
        file_path = PathUtils.resolve_file_path(filename)

        if not file_path:
            missing_files.append(filename)
            continue

        validation_result = validate_media_file(file_path)

        if validation_result.is_valid:
            processed_input = processed_input.replace(f"@{filename}", filename)
            referenced_files.append(str(file_path.absolute()))
        else:
            media_validation_errors.append(f"@{filename}: {validation_result.error_message}")

    _handle_file_errors(missing_files, media_validation_errors)

    return processed_input, referenced_files


def _handle_file_errors(missing_files: list[str], media_validation_errors: list[str]) -> None:
    """Handle and format file errors."""
    if missing_files:
        if len(missing_files) == 1:
            raise ValueError(f"File not found: {missing_files[0]}")
        raise ValueError(f"Files not found: {', '.join(missing_files)}")

    if media_validation_errors:
        error_message = "FFmpeg commands can't be generated for non-media files: " + "; ".join(media_validation_errors)
        raise ValueError(error_message)


def extract_potential_filenames(user_input: str) -> list[str]:
    """Extract potential INPUT filenames from user input text."""
    pattern = r"\b[\w\./\-_]+\.(?:" + "|".join(ext[1:] for ext in FileConstants.MEDIA_EXTENSIONS) + r")\b"
    potential_files = re.findall(pattern, user_input, re.IGNORECASE)

    input_files = _filter_output_files(user_input, potential_files)

    return _remove_duplicates(input_files)


def _filter_output_files(user_input: str, potential_files: list[str]) -> list[str]:
    """Filter out files that are likely outputs based on context."""
    input_files = []
    input_lower = user_input.lower()

    for filename in potential_files:
        if not _is_likely_output_file(input_lower, filename):
            input_files.append(filename)

    return input_files


def _is_likely_output_file(input_lower: str, filename: str) -> bool:
    """Check if filename is likely an output file based on context."""
    filename_lower = filename.lower()
    pos = input_lower.find(filename_lower)

    if pos == -1:
        return False

    # Check words before filename for output indicators
    words_before = input_lower[:pos].strip().split()
    if words_before:
        last_word = words_before[-1].rstrip(".,!?")
        if last_word in FileConstants.OUTPUT_INDICATORS:
            return True

    # Check for "to" pattern
    return _check_to_pattern(input_lower, pos)


def _check_to_pattern(input_lower: str, filename_pos: int) -> bool:
    """Check if filename appears after 'to' indicating output."""
    to_pos = input_lower.find("to")
    if to_pos < filename_pos and to_pos != -1:
        between_text = input_lower[to_pos + 2 : filename_pos].strip()
        words_between = between_text.split()
        if len(words_between) <= FileConstants.MAX_WORDS_BETWEEN_TO:
            return True
    return False


def _remove_duplicates(files: list[str]) -> list[str]:
    """Remove duplicates while preserving order."""
    seen = set()
    unique_files = []

    for filename in files:
        if filename.lower() not in seen:
            seen.add(filename.lower())
            unique_files.append(filename)

    return unique_files


def validate_mentioned_files(user_input: str) -> tuple[list[str], list[str]]:
    """Validate that files mentioned in user input actually exist."""
    potential_files = extract_potential_filenames(user_input)
    existing_files = []
    missing_files = []

    for filename in potential_files:
        file_path = _find_existing_file(filename)

        if file_path:
            existing_files.append(filename)
        else:
            missing_files.append(filename)

    return existing_files, missing_files


def _find_existing_file(filename: str) -> Path | None:
    """Find existing file using multiple resolution strategies."""
    # Strategy 1: Path as given (for relative/absolute paths)
    test_path = Path(filename)
    if test_path.exists() and test_path.is_file():
        return test_path

    # Strategy 2: Assume current directory (for bare filenames)
    test_path = Path.cwd() / filename
    if test_path.exists() and test_path.is_file():
        return test_path

    return None


def filter_context_for_referenced_files(context: dict, referenced_files: list[str]) -> dict:
    """Filter workspace context to prioritize explicitly referenced files."""
    filtered_context = context.copy()

    for file_type in ["videos", "audios", "images", "subtitle_files"]:
        if file_type in context:
            filtered_context[file_type] = _prioritize_referenced_files(context[file_type], referenced_files)

    return filtered_context


def _prioritize_referenced_files(file_list: list[str], referenced_files: list[str]) -> list[str]:
    """Prioritize referenced files in the file list."""
    working_list = file_list.copy()
    prioritized_list = []

    # Add referenced files first
    for ref_file in referenced_files:
        ref_path = Path(ref_file)
        for file_path in working_list:
            if Path(file_path).resolve() == ref_path.resolve():
                prioritized_list.append(file_path)
                working_list.remove(file_path)
                break

    # Add remaining files
    prioritized_list.extend(working_list)
    return prioritized_list


def validate_non_media_files_in_input(user_input: str) -> None:
    """Validate that no non-media files are referenced in the user input."""
    # Use centralized media extensions
    all_media_exts = FileConstants.MEDIA_EXTENSIONS

    # Find potential file patterns in input
    file_pattern = r"\b[\w\./\-_]+\.[\w]+\b"
    potential_files = re.findall(file_pattern, user_input, re.IGNORECASE)

    non_media_files = []
    for filename in potential_files:
        file_ext = Path(filename).suffix.lower()
        if file_ext and file_ext not in all_media_exts:
            # Check if file exists to avoid false positives
            if Path(filename).exists() or Path.cwd() / filename:
                non_media_files.append(filename)

    if non_media_files:
        raise ValueError(
            f"Non-media files detected in input: {', '.join(non_media_files)}. "
            f"MediaLLM only processes media files (video, audio, image, subtitle)."
        )
