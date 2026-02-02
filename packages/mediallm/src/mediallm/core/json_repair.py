#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..safety.data_protection import create_secure_logger
from .action_inference import fix_action_validation_issues
from .action_inference import infer_action_from_query
from .action_inference import infer_format_and_codec
from .action_inference import infer_inputs_from_query

logger = create_secure_logger(__name__)


class JSONRepair:
    """Handles JSON validation and repair for LLM responses."""

    @staticmethod
    def extract_json_from_text(text: str) -> str:
        """Extract JSON object from text that may contain explanations.

        LLMs sometimes embed JSON within explanatory text or markdown code blocks.
        This method extracts the JSON portion from such responses.
        """
        if not text:
            return text

        text = text.strip()

        # If it already looks like valid JSON, return as-is
        if text.startswith("{") and text.endswith("}"):
            return text

        # Try to extract from markdown code blocks (```json ... ``` or ``` ... ```)
        markdown_patterns = [
            r"```json\s*([\s\S]*?)\s*```",
            r"```\s*([\s\S]*?)\s*```",
        ]
        for pattern in markdown_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                if extracted.startswith("{"):
                    logger.debug("Extracted JSON from markdown code block")
                    return extracted

        # Try to find JSON object between first { and last }
        first_brace = text.find("{")
        last_brace = text.rfind("}")

        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            extracted = text[first_brace:last_brace + 1]
            logger.debug("Extracted JSON from surrounding text")
            return extracted

        return text

    @staticmethod
    def sanitize_path_values(data: dict[str, Any], workspace: dict[str, Any]) -> dict[str, Any]:
        """Remove inline comments/descriptions from path values.

        LLMs sometimes generate paths with embedded explanations like:
        "video.mp4 - source file" or "output.mp3 (converted audio)"

        This method cleans these up to valid paths.
        """
        path_fields = ["output", "subtitle_path", "overlay_path"]

        for field in path_fields:
            value = data.get(field)
            if value and isinstance(value, str):
                cleaned = JSONRepair._clean_path_string(value, workspace)
                if cleaned != value:
                    logger.debug(f"Sanitized {field}: '{value}' -> '{cleaned}'")
                    data[field] = cleaned

        # Handle inputs list
        if "inputs" in data and isinstance(data["inputs"], list):
            cleaned_inputs = []
            for inp in data["inputs"]:
                if isinstance(inp, str):
                    cleaned = JSONRepair._clean_path_string(inp, workspace)
                    cleaned_inputs.append(cleaned)
                else:
                    cleaned_inputs.append(inp)
            data["inputs"] = cleaned_inputs

        return data

    @staticmethod
    def _clean_path_string(path_str: str, workspace: dict[str, Any]) -> str:
        """Clean a single path string by removing embedded text."""
        if not path_str:
            return path_str

        original = path_str

        # Remove common inline comment patterns
        # Pattern: "file.ext - description" or "file.ext (description)"
        patterns_to_remove = [
            r"\s*-\s+[^/\\]+$",           # " - description"
            r"\s*\([^)]+\)\s*$",          # " (description)"
            r"\s*#[^/\\]+$",              # " # comment"
            r"\s*//[^/\\]+$",             # " // comment"
            r"\s*:\s+[^/\\:]+$",          # " : description"
        ]

        for pattern in patterns_to_remove:
            path_str = re.sub(pattern, "", path_str)

        # If the entire string looks like a description (no file extension), try to extract filename
        if not re.search(r"\.\w{2,5}$", path_str):
            # Try to find a filename with extension in the original string
            ext_match = re.search(r"(\S+\.\w{2,5})", original)
            if ext_match:
                path_str = ext_match.group(1)

        # Try to match with workspace files if we have a partial match
        path_str_lower = path_str.lower().strip()
        workspace_lists = [
            workspace.get("videos", []),
            workspace.get("audios", []),
            workspace.get("images", []),
            workspace.get("subtitle_files", []),
        ]

        for file_list in workspace_lists:
            for ws_file in file_list:
                ws_file_str = str(ws_file)
                ws_filename = Path(ws_file_str).name.lower()
                # Check if the cleaned path matches a workspace file
                if path_str_lower == ws_filename or path_str_lower in ws_file_str.lower():
                    return ws_file_str

        return path_str.strip()

    @staticmethod
    def repair_json_for_schema(
        data: dict[str, Any] | None, user_query: str, workspace: dict[str, Any]
    ) -> dict[str, Any]:
        """Repair JSON data by inferring missing required fields."""
        if data is None:
            data = {}

        repaired = data.copy()

        # First, sanitize any path values that may have embedded text
        repaired = JSONRepair.sanitize_path_values(repaired, workspace)

        # Ensure required 'action' field
        if "action" not in repaired or not repaired["action"]:
            repaired["action"] = infer_action_from_query(user_query)
            logger.debug(f"Inferred missing action: {repaired['action']}")

        # Ensure list fields are properly initialized
        for field in ["inputs", "filters", "extra_flags"]:
            if field not in repaired or repaired[field] is None:
                repaired[field] = []
            elif not isinstance(repaired[field], list):
                # Convert single values to lists
                repaired[field] = [repaired[field]] if repaired[field] else []

        # Clean up empty strings in lists
        for field in ["filters", "extra_flags"]:
            if isinstance(repaired.get(field), list):
                repaired[field] = [item for item in repaired[field] if item and str(item).strip()]

        # If inputs is empty, try to infer from user query for most actions
        # Expanded list of actions that can benefit from input inference
        actions_needing_inputs = [
            "convert",
            "extract_audio",
            "compress",
            "format_convert",
            "trim",
            "segment",
            "thumbnail",
            "frames",
            "extract_frames",
            "burn_subtitles",
            "extract_subtitles",
            "remove_audio",
            "overlay",
        ]
        if not repaired.get("inputs") and repaired.get("action") in actions_needing_inputs:
            infer_inputs_from_query(repaired, user_query, workspace)

        # Always try to infer format and codec even if not explicitly needed for validation
        infer_format_and_codec(repaired, user_query)

        # Post-validation fixes for action-specific issues
        fix_action_validation_issues(repaired, user_query)

        return repaired

    @staticmethod
    def fix_common_issues(response: str) -> str:
        """Fix common issues in model responses before parsing."""
        # First, try to extract JSON from surrounding text
        response = JSONRepair.extract_json_from_text(response)

        # Fix null values for array fields that should be empty arrays
        response = re.sub(r'"filters":\s*null', '"filters": []', response)
        response = re.sub(r'"extra_flags":\s*null', '"extra_flags": []', response)
        response = re.sub(r'"inputs":\s*null', '"inputs": []', response)

        # Fix missing array brackets for single values
        # Match patterns like "filters": "value" and convert to "filters": ["value"]
        response = re.sub(r'"filters":\s*"([^"]+)"', r'"filters": ["\1"]', response)
        return re.sub(r'"extra_flags":\s*"([^"]+)"', r'"extra_flags": ["\1"]', response)
