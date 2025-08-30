#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import logging
from pathlib import Path

from ..processing.media_file_handler import expand_globs
from ..utils.data_models import Action
from ..utils.data_models import CommandEntry
from ..utils.data_models import CommandPlan
from ..utils.data_models import MediaIntent
from ..utils.exceptions import ConstructionError
from .file_type_detector import FileTypeDetector
from .filter_validator import FilterValidator
from .output_generator import OutputGenerator

logger = logging.getLogger(__name__)


class TaskDispatcher:
    """Dispatches FFmpeg intents to command plans."""

    def __init__(self) -> None:
        """Initialize the task dispatcher."""
        self._file_detector = FileTypeDetector()
        self._filter_validator = FilterValidator()
        self._output_generator = OutputGenerator()

    def dispatch_task(
        self,
        task: MediaIntent,
        allowed_dirs: list[Path] | None = None,
        output_dir: Path | None = None,
    ) -> CommandPlan:
        """Dispatch MediaIntent to CommandPlan with security validation."""
        logger.debug(
            f"Dispatching task: {task.action.value if task.action else 'unknown'} with {len(task.inputs)} inputs"
        )
        validated_inputs = self._validate_and_prepare_inputs(task, allowed_dirs)
        entries = self._process_task_entries(task, validated_inputs, output_dir)
        summary = self._build_summary(task, entries)
        logger.debug(f"Task dispatch completed: {summary}")
        return CommandPlan(summary=summary, entries=entries)

    def _validate_and_prepare_inputs(self, task: MediaIntent, allowed_dirs: list[Path] | None) -> list[Path]:
        """Validate and prepare input files for processing."""
        logger.debug(f"Validating {len(task.inputs)} input files")
        # Expand any glob patterns provided with security validation
        derived_inputs: list[Path] = list(task.inputs)
        if task.glob:
            logger.debug(f"Expanding glob pattern: {task.glob}")
            # Use secure glob expansion with allowed directories
            if allowed_dirs is None:
                allowed_dirs = [Path.cwd()]  # Default to current directory
            globbed = expand_globs([task.glob], allowed_dirs)
            logger.debug(f"Glob expansion found {len(globbed)} additional files")
            derived_inputs.extend(globbed)

        # Validate all input paths for security
        from ..processing.media_file_handler import is_safe_path
        from ..utils.media_validator import validate_media_file

        validated_inputs = []
        media_validation_errors = []

        logger.debug(f"Security validating {len(derived_inputs)} derived inputs")
        for input_path in derived_inputs:
            if not is_safe_path(input_path, allowed_dirs):
                logger.warning(f"Unsafe path rejected: {input_path}")
                continue

            # Validate that the file is a supported media file
            validation_result = validate_media_file(input_path)
            if validation_result.is_valid:
                validated_inputs.append(input_path)
                logger.debug(f"File validated: {input_path}")
            else:
                logger.debug(f"File validation failed: {input_path} - {validation_result.error_message}")
                media_validation_errors.append(f"{input_path}: {validation_result.error_message}")

        self._handle_validation_errors(media_validation_errors)

        if not validated_inputs:
            logger.debug("No valid input files found after validation")
            raise ConstructionError(
                "No safe input files found. Please ensure: (1) input files exist in the current directory, (2) file paths are correct and safe, (3) no path traversal attempts (e.g., ../), and (4) glob patterns match existing files. Try 'ls' to check available files."
            )

        logger.debug(f"Successfully validated {len(validated_inputs)} input files")
        return validated_inputs

    def _handle_validation_errors(self, errors: list[str]) -> None:
        """Handle media validation errors."""
        if not errors:
            return

        # Separate file not found errors from non-media file errors
        file_not_found_errors = []
        non_media_errors = []

        for error in errors:
            if "File not found:" in error:
                file_not_found_errors.append(error)
            else:
                non_media_errors.append(error)

        # Handle file not found errors separately
        if file_not_found_errors:
            if len(file_not_found_errors) == 1:
                # Extract just the error message part (after the filename:)
                error_parts = file_not_found_errors[0].split(": ", 1)
                if len(error_parts) > 1:
                    raise ConstructionError(error_parts[1])  # "File not found: filename"
                raise ConstructionError(file_not_found_errors[0])
            raise ConstructionError(
                "Multiple files not found:\n"
                + "\n".join([error.split(": ", 1)[1] if ": " in error else error for error in file_not_found_errors])
            )

        # Handle non-media file errors
        if non_media_errors:
            error_message = "FFmpeg commands can't be generated for non-media files:\n" + "\n".join(non_media_errors)
            raise ConstructionError(error_message)

    def _process_task_entries(
        self, task: MediaIntent, validated_inputs: list[Path], output_dir: Path | None
    ) -> list[CommandEntry]:
        """Process task entries for each input file."""
        logger.debug(f"Processing {len(validated_inputs)} task entries")
        entries: list[CommandEntry] = []

        for i, inp in enumerate(validated_inputs):
            logger.debug(f"Processing entry {i+1}/{len(validated_inputs)}: {inp}")
            output = self._output_generator.derive_output_name(inp, task, output_dir)
            logger.debug(f"Generated output path: {output}")
            args = self._build_action_args(task, inp)
            logger.debug(f"Built args: {args}")

            # Handle overlay as special case (has extra inputs)
            if task.action == Action.overlay and task.overlay_path:
                if task.overlay_xy:
                    args.extend(["-filter_complex", f"overlay={task.overlay_xy}"])
                entries.append(
                    CommandEntry(
                        input=inp,
                        output=output,
                        args=args,
                        extra_inputs=[task.overlay_path],
                    )
                )
                continue

            entries.append(CommandEntry(input=inp, output=output, args=args))

        logger.debug(f"Successfully processed {len(entries)} command entries")
        return entries

    def _build_action_args(self, task: MediaIntent, input_path: Path) -> list[str]:
        """Build FFmpeg arguments for specific action."""
        logger.debug(f"Building args for action: {task.action.value if task.action else 'unknown'}")
        args: list[str] = []

        if task.action == Action.convert:
            args.extend(self._build_convert_args(task))
        elif task.action == Action.extract_audio:
            args.extend(["-q:a", "0", "-map", "a"])
        elif task.action == Action.remove_audio:
            args.extend(["-an"])
            if task.video_codec:
                args.extend(["-c:v", task.video_codec])
        elif task.action == Action.trim:
            args.extend(self._build_trim_args(task))
        elif task.action == Action.segment:
            args.extend(self._build_trim_args(task))  # Same as trim
        elif task.action == Action.thumbnail:
            args.extend(self._build_thumbnail_args(task))
        elif task.action == Action.frames:
            args.extend(self._build_frames_args(task))
        elif task.action == Action.compress:
            args.extend(self._build_compress_args(task))
        elif task.action == Action.format_convert:
            args.extend(self._build_format_convert_args(task))
        elif task.action == Action.extract_frames:
            args.extend(self._build_extract_frames_args(task))
        elif task.action == Action.burn_subtitles:
            args.extend(self._build_burn_subtitles_args(task))
        elif task.action == Action.extract_subtitles:
            args.extend(["-map", "0:s:0", "-c:s", "srt"])
        elif task.action == Action.slideshow:
            args.extend(self._build_slideshow_args(task))
        else:
            raise ConstructionError(
                f"Unsupported action: {task.action}. "
                f"Supported actions are: convert, extract_audio, remove_audio, "
                f"trim, segment, thumbnail, frames, compress, overlay, format_convert, extract_frames, "
                f"burn_subtitles, extract_subtitles, slideshow. "
                f"Please rephrase your request using supported operations."
            )

        return args

    def _build_convert_args(self, task: MediaIntent) -> list[str]:
        """Build arguments for convert action."""
        args = []

        # Collect all filters to combine into a single -vf flag
        all_filters = []

        if task.scale:
            # Validate and fix scale filter to ensure even dimensions
            fixed_scale = self._filter_validator.validate_and_fix_scale_filter(f"scale={task.scale}")
            if fixed_scale:
                all_filters.append(fixed_scale)

        if task.filters:
            # Validate all filters in the filters list
            validated_filters = self._filter_validator.validate_and_fix_filter_chain(task.filters)
            all_filters.extend(validated_filters)

        # Combine filters
        filter_str = self._filter_validator.combine_filters(all_filters)
        if filter_str:
            args.extend(["-vf", filter_str])

        if task.video_codec:
            args.extend(["-c:v", task.video_codec])
        if task.audio_codec:
            args.extend(["-c:a", task.audio_codec])

        return args

    def _build_trim_args(self, task: MediaIntent) -> list[str]:
        """Build arguments for trim/segment actions."""
        args = []

        if task.start:
            args.extend(["-ss", task.start])
        # If end is provided, prefer -to; otherwise use duration if present
        if task.end:
            args.extend(["-to", task.end])
        elif task.duration is not None:
            args.extend(["-t", str(task.duration)])

        return args

    def _build_thumbnail_args(self, task: MediaIntent) -> list[str]:
        """Build arguments for thumbnail action."""
        args = []

        if task.start:
            args.extend(["-ss", task.start])
        args.extend(["-vframes", "1"])

        return args

    def _build_frames_args(self, task: MediaIntent) -> list[str]:
        """Build arguments for frames action."""
        args = []

        if task.fps:
            args.extend(["-vf", f"fps={task.fps}"])

        return args

    def _build_compress_args(self, task: MediaIntent) -> list[str]:
        """Build arguments for compress action."""
        args = []

        if task.crf is not None:
            args.extend(["-crf", str(task.crf)])
        if task.video_codec:
            args.extend(["-c:v", task.video_codec])
        if task.audio_codec:
            args.extend(["-c:a", task.audio_codec])

        return args

    def _build_format_convert_args(self, task: MediaIntent) -> list[str]:
        """Build arguments for format_convert action."""
        args = []

        if task.format:
            args.extend(["-f", task.format])
        if task.video_codec:
            args.extend(["-c:v", task.video_codec])
        if task.audio_codec:
            args.extend(["-c:a", task.audio_codec])

        return args

    def _build_extract_frames_args(self, task: MediaIntent) -> list[str]:
        """Build arguments for extract_frames action."""
        args = []

        if task.fps:
            args.extend(["-vf", f"fps={task.fps}"])
        else:
            # Default to 1 frame per 5 seconds
            args.extend(["-vf", "fps=1/5"])
        # Add frame_pts for better frame naming
        args.extend(["-frame_pts", "1"])

        return args

    def _build_burn_subtitles_args(self, task: MediaIntent) -> list[str]:
        """Build arguments for burn_subtitles action."""
        args = []

        if task.subtitle_path:
            if task.filters:
                # Add subtitles filter to existing filters
                task.filters.append(f"subtitles={task.subtitle_path}")
            else:
                task.filters = [f"subtitles={task.subtitle_path}"]
        if task.video_codec:
            args.extend(["-c:v", task.video_codec])
        if task.audio_codec:
            args.extend(["-c:a", task.audio_codec])

        return args

    def _build_slideshow_args(self, task: MediaIntent) -> list[str]:
        """Build arguments for slideshow action."""
        args = []

        if task.video_codec:
            args.extend(["-c:v", task.video_codec])
        if task.audio_codec:
            args.extend(["-c:a", task.audio_codec])
        # Set framerate for slideshow
        args.extend(["-r", "30"])  # Output framerate
        if task.duration:
            # Duration per image
            args.extend(
                [
                    "-t",
                    str(task.duration * len(task.inputs) if task.inputs else task.duration),
                ]
            )

        return args

    def _build_summary(self, task: MediaIntent, entries: list[CommandEntry]) -> str:
        """Build human-readable summary of the command plan."""
        logger.debug(
            f"Building summary for {task.action.value if task.action else 'unknown'} action with {len(entries)} entries"
        )
        if task.action == Action.convert:
            return f"Convert {len(entries)} file(s) to mp4 h264+aac with optional scale {task.scale or '-'}"
        if task.action == Action.extract_audio:
            return f"Extract audio from {len(entries)} file(s) to mp3"
        if task.action == Action.trim:
            end_or_duration = f"end={task.end}" if task.end else f"duration={task.duration or '-'}"
            return f"Trim {len(entries)} file(s) start={task.start or '0'} {end_or_duration}"
        if task.action == Action.thumbnail:
            return f"Thumbnail from {len(entries)} file(s) at {task.start or '00:00:10'}"
        if task.action == Action.overlay:
            return f"Overlay {task.overlay_path} on {len(entries)} file(s)"
        if task.action == Action.compress:
            return f"Compress {len(entries)} file(s) with libx265 CRF {task.crf or 28}"
        if task.action == Action.frames:
            return f"Extract frames from {len(entries)} file(s) with fps {task.fps or '1/5'}"
        if task.action == Action.format_convert:
            format_info = f"format={task.format}" if task.format else "default format"
            video_info = f"video={task.video_codec}" if task.video_codec else "default video"
            audio_info = f"audio={task.audio_codec}" if task.audio_codec else "default audio"
            return f"Convert {len(entries)} file(s) to {format_info} with {video_info} and {audio_info}"
        if task.action == Action.extract_frames:
            fps_info = f"fps={task.fps}" if task.fps else "fps=1/5"
            return f"Extract frames from {len(entries)} file(s) with {fps_info}"
        if task.action == Action.burn_subtitles:
            subtitle_info = f"subtitles={task.subtitle_path.name}" if task.subtitle_path else "no subtitle file"
            return f"Burn {subtitle_info} into {len(entries)} video file(s)"
        if task.action == Action.extract_subtitles:
            return f"Extract subtitles from {len(entries)} video file(s) to SRT format"
        if task.action == Action.slideshow:
            duration_info = f"duration={task.duration}s per image" if task.duration else "default timing"
            return f"Create slideshow from {len(entries)} image(s) with {duration_info}"
        return f"Action {task.action} on {len(entries)} file(s)"


# Module-level function for backward compatibility
def dispatch_task(
    task: MediaIntent,
    allowed_dirs: list[Path] | None = None,
    output_dir: Path | None = None,
) -> CommandPlan:
    """Dispatch MediaIntent to CommandPlan with security validation."""
    dispatcher = TaskDispatcher()
    return dispatcher.dispatch_task(task, allowed_dirs, output_dir)
