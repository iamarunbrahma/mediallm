#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from ..analysis.prompt_enhancer import refine_input
from ..constants.prompts import SYSTEM_PROMPT
from ..processing.media_file_handler import sanitize_user_input
from ..safety.data_protection import create_secure_logger
from ..utils.data_models import MediaIntent
from ..utils.exceptions import ParseError
from ..utils.exceptions import TranslationError
from .json_repair import JSONRepair

logger = create_secure_logger(__name__)


class QueryParser:
    """Handles parsing of natural language queries into structured FFmpeg intents."""

    def __init__(self, provider) -> None:
        """Initialize query parser with AI provider."""
        self._provider = provider
        self._json_repair = JSONRepair()

    def parse_query(self, user_query: str, workspace: dict[str, Any], timeout: int | None = None) -> MediaIntent:
        """Parse natural language query into MediaIntent with retry logic."""
        # Sanitize user input first to prevent injection attacks
        sanitized_query = sanitize_user_input(user_query)

        if not sanitized_query.strip():
            raise TranslationError(
                "Empty or invalid query provided. Please provide a clear description of what you want to do."
            )

        # Optimize the query for better model understanding using workspace
        optimized_request = refine_input(sanitized_query, workspace)

        # Log the optimization for debugging
        if optimized_request != sanitized_query:
            logger.debug(f"Optimized request: '{sanitized_query}' -> '{optimized_request}'")

        # Prepare user payload with query and workspace
        user_payload = json.dumps({"request": optimized_request, "workspace": workspace})
        effective_timeout = 60 if timeout is None else timeout

        logger.debug(f"Parsing query with timeout: {effective_timeout}s")

        return self._attempt_parsing(user_payload, optimized_request, workspace, effective_timeout)

    def _attempt_parsing(
        self,
        user_payload: str,
        optimized_request: str,
        workspace: dict[str, Any],
        timeout: int,
    ) -> MediaIntent:
        """Attempt to parse the query with error handling and retries."""
        # First attempt at parsing
        try:
            raw = self._provider.process_query(SYSTEM_PROMPT, user_payload, timeout=timeout)
            logger.debug(f"Received raw response: {len(raw) if raw else 0} chars")

            if not raw or raw.strip() == "":
                logger.warning("Empty response from model, using fallback")
                data = {}
            else:
                data = json.loads(raw)

            return self._process_response_data(data, optimized_request, workspace)

        except ValidationError as validation_err:
            return self._handle_validation_error(validation_err, data, optimized_request, workspace)
        except json.JSONDecodeError as json_err:
            return self._handle_json_error(json_err, user_payload, optimized_request, workspace, timeout)

    def _process_response_data(
        self, data: dict[str, Any], optimized_request: str, workspace: dict[str, Any]
    ) -> MediaIntent:
        """Process response data and handle error responses."""
        # Check if the response is an error JSON from the model
        if isinstance(data, dict) and "error" in data:
            error_type = data.get("error", "unknown_error")
            error_message = data.get("message", "Unknown error")

            if error_type == "missing_input":
                raise TranslationError(
                    f"Input file not found: {error_message}. Please ensure the file exists in the current directory and try again."
                )
            if error_type == "unsupported_action":
                raise TranslationError(
                    f"Unsupported operation: {error_message}. Please check the supported actions and try a different approach."
                )
            raise TranslationError(
                f"Model error: {error_message}. Please try rephrasing your request or check if the operation is supported."
            )

        intent = MediaIntent.model_validate(data)
        logger.debug(f"Successfully parsed task: {intent.action}")
        return intent

    def _handle_validation_error(
        self,
        validation_err: ValidationError,
        data: dict[str, Any],
        optimized_request: str,
        workspace: dict[str, Any],
    ) -> MediaIntent:
        """Handle validation errors by attempting to repair JSON."""
        logger.debug(f"Schema validation failed, attempting to repair: {validation_err}")
        try:
            repaired_data = self._json_repair.repair_json_for_schema(data, optimized_request, workspace)
            intent = MediaIntent.model_validate(repaired_data)
            logger.debug(f"Successfully repaired and parsed task: {intent.action}")
            return intent
        except ValidationError as repair_err:
            logger.error(f"Failed to repair JSON: {repair_err}")
            raise TranslationError(
                f"Failed to validate parsed task: {repair_err}. The local model returned JSON that doesn't match expected format. This could be due to: (1) unsupported operation - check supported actions, (2) ambiguous query - be more specific about what you want to do, (3) model issues - try a more capable model like llama3 or mistral."
            ) from repair_err
        except Exception as repair_exc:
            logger.error(f"Unexpected error during JSON repair: {repair_exc}")
            raise TranslationError(
                f"Failed to validate parsed task: {validation_err}. The local model returned JSON that doesn't match expected format. This could be due to: (1) unsupported operation - check supported actions, (2) ambiguous query - be more specific about what you want to do, (3) model issues - try a more capable model like llama3 or mistral."
            ) from validation_err

    def _handle_json_error(
        self,
        first_err: json.JSONDecodeError,
        user_payload: str,
        optimized_request: str,
        workspace: dict[str, Any],
        timeout: int,
    ) -> MediaIntent:
        """Handle JSON decode errors by attempting a retry with corrective instructions."""
        logger.debug(f"Primary parse failed: {type(first_err).__name__}: {first_err}")

        # One corrective pass with more specific instructions
        logger.debug("Attempting repair with corrective query")
        repair_query = (
            "The previous JSON output was invalid. Please generate ONLY valid JSON "
            "matching the MediaIntent schema. Do not include any explanations or markdown formatting."
        )

        try:
            raw2 = self._provider.process_query(
                SYSTEM_PROMPT,
                repair_query + "\n" + user_payload,
                timeout=timeout,
            )

            data2 = json.loads(raw2)
            return self._process_response_data(data2, optimized_request, workspace)

        except ValidationError as retry_validation_err:
            return self._handle_retry_validation_error(retry_validation_err, data2, optimized_request, workspace)
        except json.JSONDecodeError as json_err:
            logger.error(f"JSON parsing failed on retry: {json_err}")
            raise TranslationError(
                f"Failed to parse model response as JSON: {json_err}. The local model returned invalid JSON format. This could be due to: (1) model issues - try a different model like llama3, (2) timeout - try increasing --timeout, (3) complex query - try simplifying your request."
            ) from json_err
        except ParseError:
            # Re-raise ParseError from provider (already has good error message)
            raise
        except OSError as io_err:
            logger.error(f"Network/IO error during retry: {io_err}")
            raise TranslationError(
                f"Network error during model request: {io_err}. "
                "Please check your Ollama server connection and try again."
            ) from io_err

    def _handle_retry_validation_error(
        self,
        retry_validation_err: ValidationError,
        data2: dict[str, Any],
        optimized_request: str,
        workspace: dict[str, Any],
    ) -> MediaIntent:
        """Handle validation errors on retry attempt."""
        logger.debug(f"Retry validation failed, attempting to repair: {retry_validation_err}")
        try:
            repaired_data2 = self._json_repair.repair_json_for_schema(data2, optimized_request, workspace)
            intent2 = MediaIntent.model_validate(repaired_data2)
            logger.debug(f"Successfully repaired and parsed task on retry: {intent2.action}")
            return intent2
        except ValidationError as final_err:
            logger.error(f"Final repair attempt failed: {final_err}")
            raise TranslationError(
                f"Failed to validate parsed task: {final_err}. The local model returned JSON that doesn't match expected format. This could be due to: (1) unsupported operation - check supported actions, (2) ambiguous query - be more specific about what you want to do, (3) model issues - try a more capable model like llama3 or mistral."
            ) from final_err
