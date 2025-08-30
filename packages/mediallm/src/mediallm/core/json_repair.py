#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import re
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
    def repair_json_for_schema(
        data: dict[str, Any] | None, user_query: str, workspace: dict[str, Any]
    ) -> dict[str, Any]:
        """Repair JSON data by inferring missing required fields."""
        if data is None:
            data = {}

        repaired = data.copy()

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

        # If inputs is empty and we have a convert-like action, try to infer from user query
        if not repaired.get("inputs") and repaired.get("action") in [
            "convert",
            "extract_audio",
            "compress",
            "format_convert",
        ]:
            infer_inputs_from_query(repaired, user_query, workspace)

        # Always try to infer format and codec even if not explicitly needed for validation
        infer_format_and_codec(repaired, user_query)

        # Post-validation fixes for action-specific issues
        fix_action_validation_issues(repaired, user_query)

        return repaired

    @staticmethod
    def fix_common_issues(response: str) -> str:
        """Fix common issues in model responses before parsing."""
        # Fix null values for array fields that should be empty arrays
        response = re.sub(r'"filters":\s*null', '"filters": []', response)
        response = re.sub(r'"extra_flags":\s*null', '"extra_flags": []', response)
        response = re.sub(r'"inputs":\s*null', '"inputs": []', response)

        # Fix missing array brackets for single values
        # Match patterns like "filters": "value" and convert to "filters": ["value"]
        response = re.sub(r'"filters":\s*"([^"]+)"', r'"filters": ["\1"]', response)
        return re.sub(r'"extra_flags":\s*"([^"]+)"', r'"extra_flags": ["\1"]', response)
