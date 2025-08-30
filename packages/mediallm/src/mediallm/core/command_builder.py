#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .file_type_detector import FileTypeDetector

if TYPE_CHECKING:
    from ..utils.data_models import CommandPlan

logger = logging.getLogger(__name__)


class CommandBuilder:
    """Builds executable FFmpeg commands from command plans."""

    # Pre-input flags that should come before -i
    _PRE_INPUT_FLAGS = {"-ss", "-t", "-to"}

    def __init__(self) -> None:
        """Initialize the command builder."""
        self._file_detector = FileTypeDetector()

    def construct_operations(self, execution_plan: CommandPlan, assume_yes: bool = False) -> list[list[str]]:
        """Build executable ffmpeg commands from a command execution_plan."""
        logger.debug(f"Building commands from plan with {len(execution_plan.entries)} entries")
        commands: list[list[str]] = []

        for i, entry in enumerate(execution_plan.entries):
            logger.debug(f"Processing entry {i+1}/{len(execution_plan.entries)}: {entry.input} -> {entry.output}")
            cmd = self._build_base_command(assume_yes)
            cmd.extend(self._build_input_section(entry))
            cmd.extend(self._build_processing_section(entry, execution_plan))
            cmd.append(str(entry.output))

            # Validate the command before adding it for security
            logger.debug(f"Validating generated command: {' '.join(cmd[:10])}...")
            if self._validate_command(cmd):
                commands.append(cmd)
                logger.debug(f"Command {i+1} validated successfully")
            else:
                logger.warning(f"Generated command failed validation: {' '.join(cmd[:5])}...")

        logger.debug(f"Successfully built {len(commands)} valid commands")
        return commands

    def _build_base_command(self, assume_yes: bool) -> list[str]:
        """Build the base FFmpeg command."""
        cmd = ["ffmpeg"]
        if assume_yes:
            cmd.append("-y")
            logger.debug("Added overwrite flag (-y) to command")
        return cmd

    def _build_input_section(self, entry) -> list[str]:
        """Build the input section of the command."""
        logger.debug(f"Building input section for {entry.input}")
        cmd_parts = []

        # Split args into pre/post by presence of pre-input flags
        pre_input_flags, _ = self._split_flags(entry.args)
        if pre_input_flags:
            logger.debug(f"Adding pre-input flags: {pre_input_flags}")

        # Add pre-input flags
        cmd_parts.extend(pre_input_flags)

        # Add main input
        cmd_parts.extend(["-i", str(entry.input)])

        # Add extra inputs (for overlay, etc.)
        if entry.extra_inputs:
            logger.debug(f"Adding {len(entry.extra_inputs)} extra inputs: {entry.extra_inputs}")
        for extra in entry.extra_inputs:
            cmd_parts.extend(["-i", str(extra)])

        return cmd_parts

    def _build_processing_section(self, entry, execution_plan: CommandPlan) -> list[str]:
        """Build the processing section of the command."""
        logger.debug(f"Building processing section for action: {execution_plan.summary[:50]}...")
        # Get post-input flags from args
        _, post_input_flags = self._split_flags(entry.args)
        if post_input_flags:
            logger.debug(f"Post-input flags: {post_input_flags}")

        # Apply action-specific defaults
        logger.debug("Applying action-specific defaults")
        cmd_parts = self._apply_action_defaults(entry, execution_plan)
        if cmd_parts:
            logger.debug(f"Applied defaults: {cmd_parts}")

        # Add post-input flags
        cmd_parts.extend(post_input_flags)

        return cmd_parts

    def _split_flags(self, args: list[str]) -> tuple[list[str], list[str]]:
        """Split arguments into pre-input and post-input flags."""
        pre_input_flags: list[str] = []
        post_input_flags: list[str] = []

        # Process arguments in pairs (flag, value)
        i = 0
        while i < len(args):
            flag = args[i]
            val = args[i + 1] if i + 1 < len(args) else None

            bucket = pre_input_flags if flag in self._PRE_INPUT_FLAGS else post_input_flags
            bucket.append(flag)

            if val is not None:
                bucket.append(val)
                i += 2
            else:
                i += 1

        return pre_input_flags, post_input_flags

    def _apply_action_defaults(self, entry, execution_plan: CommandPlan) -> list[str]:
        """Apply action-specific defaults based on summary heuristics."""
        cmd_parts = []
        summary = execution_plan.summary.lower()
        existing_args_str = " ".join(entry.args)
        logger.debug(f"Applying defaults for summary keywords: {summary}")

        # Handle compression defaults
        if "compress" in summary and "-c:v" not in existing_args_str:
            logger.debug("Adding compression video codec: libx265")
            cmd_parts.extend(["-c:v", "libx265"])

        # Handle convert defaults
        if "convert" in summary:
            cmd_parts.extend(self._apply_convert_defaults(entry, existing_args_str))

        # Handle compression CRF
        if "compress" in summary and "-crf" not in existing_args_str:
            logger.debug("Adding CRF value for compression: 28")
            cmd_parts.extend(["-crf", "28"])

        # Handle frame extraction defaults
        if "frames" in summary and "fps=" not in existing_args_str:
            cmd_parts.extend(["-vf", "fps=1/5"])

        # Handle overlay defaults
        if "overlay" in summary and "-filter_complex" not in entry.args:
            cmd_parts.extend(["-filter_complex", "overlay=W-w-10:10"])

        # Handle thumbnail defaults
        if "thumbnail" in summary and "-vframes" not in entry.args:
            cmd_parts.extend(["-vframes", "1"])

        # Handle trim/segment copy defaults
        if ("trim" in summary or "segment" in summary) and not any(
            token in existing_args_str for token in ["-c:v", "-c:a", "-filter", "-vf", "-af"]
        ):
            cmd_parts.extend(["-c", "copy"])

        return cmd_parts

    def _apply_convert_defaults(self, entry, existing_args_str: str) -> list[str]:
        """Apply convert action defaults based on input file type."""
        cmd_parts = []
        input_file_type = self._file_detector.get_file_type(entry.input)
        logger.debug(f"Applying convert defaults for file type: {input_file_type}")

        if input_file_type == "video":
            # Video files get video and audio codecs
            if "-c:v" not in existing_args_str:
                cmd_parts.extend(["-c:v", "libx264"])
            if "-c:a" not in existing_args_str:
                cmd_parts.extend(["-c:a", "aac"])
        elif input_file_type == "audio":
            # Audio files only get audio codec
            if "-c:a" not in existing_args_str:
                cmd_parts.extend(["-c:a", "aac"])
            # Don't add video codec for audio-only files
        elif input_file_type == "image":
            # Images might be converted to video (e.g., slideshows) or kept as images
            # If output suggests video format, add video codec
            output_ext = Path(str(entry.output)).suffix
            if output_ext.lower() in {".mp4", ".mov", ".avi", ".mkv"} and "-c:v" not in existing_args_str:
                cmd_parts.extend(["-c:v", "libx264"])

        return cmd_parts

    def _validate_command(self, cmd: list[str]) -> bool:
        """Validate the generated command for security."""
        from ..processing.media_file_handler import validate_ffmpeg_command

        result = validate_ffmpeg_command(cmd)
        logger.debug(f"Command validation result: {result}")
        return result


# Module-level function for backward compatibility
def construct_operations(execution_plan: CommandPlan, assume_yes: bool = False) -> list[list[str]]:
    """Build executable ffmpeg commands from a command execution_plan."""
    builder = CommandBuilder()
    return builder.construct_operations(execution_plan, assume_yes)
