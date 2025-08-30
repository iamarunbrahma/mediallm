#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Final

from prompt_toolkit import PromptSession
from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer
from prompt_toolkit.completion import Completion
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.filters import has_completions
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.shortcuts import clear
from prompt_toolkit.styles import Style


class PathUtils:
    """Utilities for path handling in completions."""

    _MAX_PATH_DISPLAY_LENGTH: Final[int] = 40

    @classmethod
    def abbreviate_path(cls, file_path: str) -> str:
        """Abbreviate long file paths for better display in completion menu."""
        if len(file_path) <= cls._MAX_PATH_DISPLAY_LENGTH:
            return file_path

        path_parts = Path(file_path).parts
        if len(path_parts) <= 2:
            return file_path

        first_part = path_parts[0]
        last_part = path_parts[-1]
        return f"{first_part}/.../{last_part}"


class FilteredPathCompleter(Completer):
    """Path completer that excludes hidden files."""

    def __init__(self) -> None:
        """Initialize the filtered path completer."""

    def get_completions(self, document, complete_event):
        """Get path completions excluding hidden files."""
        text = document.text_before_cursor
        path_info = self._parse_path_from_text(text)

        try:
            directory, basename = self._determine_directory_and_basename(path_info["path"])
            if not directory or not directory.exists():
                return

            yield from self._generate_completions(directory, basename, path_info["path"], path_info["prefix_length"])

        except (OSError, PermissionError, ValueError):
            pass

    def _parse_path_from_text(self, text: str) -> dict[str, any]:
        """Parse path information from input text."""
        words = text.split()
        path_to_complete = words[-1] if words else ""

        if path_to_complete.startswith("@"):
            return {
                "path": path_to_complete[1:],
                "prefix_length": len(words[-1]) if words else 0,
            }
        return {"path": path_to_complete, "prefix_length": len(path_to_complete)}

    def _determine_directory_and_basename(self, path_to_complete: str) -> tuple[Path | None, str]:
        """Determine directory to scan and basename to match."""
        if not path_to_complete:
            return Path.cwd(), ""

        path_obj = Path(path_to_complete)

        if path_obj.is_absolute():
            if path_obj.is_dir():
                return path_obj, ""
            return path_obj.parent, path_obj.name
        if path_to_complete.endswith("/"):
            return Path.cwd() / path_to_complete, ""
        if "/" in path_to_complete:
            return Path.cwd() / path_obj.parent, path_obj.name
        return Path.cwd(), path_to_complete

    def _generate_completions(self, directory: Path, basename: str, path_to_complete: str, prefix_length: int):
        """Generate completion objects for directory items."""
        for item in directory.iterdir():
            if self._should_skip_item(item, basename):
                continue

            completion_text = self._calculate_completion_text(item, basename, path_to_complete)
            display_text = item.name + ("/" if item.is_dir() else "")

            yield Completion(
                completion_text,
                start_position=-prefix_length if prefix_length > 0 else 0,
                display=display_text,
            )

    def _should_skip_item(self, item: Path, basename: str) -> bool:
        """Check if item should be skipped."""
        if item.name.startswith("."):
            return True

        return bool(basename and not item.name.lower().startswith(basename.lower()))

    def _calculate_completion_text(self, item: Path, basename: str, path_to_complete: str) -> str:
        """Calculate the completion text for an item."""
        if path_to_complete:
            completion_text = (
                item.name if path_to_complete.endswith("/") or not basename else item.name[len(basename) :]
            )
        else:
            completion_text = item.name

        if item.is_dir():
            completion_text += "/"

        return completion_text


class MediaCompleter(Completer):
    """Custom completer for mediallm commands and file paths."""

    def __init__(self, slash_commands: list[str], media_files: list[str] | None = None) -> None:
        """Initialize the completer."""
        self.slash_commands = slash_commands
        self.media_files = media_files or []
        self.word_completer = WordCompleter(slash_commands, ignore_case=True)
        self.path_completer = FilteredPathCompleter()

        # Common media operation keywords
        self.operation_keywords = [
            "convert",
            "resize",
            "compress",
            "extract",
            "merge",
            "trim",
            "speed",
            "audio",
            "video",
            "image",
            "mp4",
            "mp3",
            "avi",
            "mov",
            "jpg",
            "png",
            "to",
            "from",
            "and",
            "by",
            "seconds",
            "minutes",
            "quality",
            "bitrate",
        ]
        self.keyword_completer = WordCompleter(self.operation_keywords, ignore_case=True)

    def get_completions(self, document, complete_event):
        """Get completions for the current input."""
        text = document.text_before_cursor
        word_before_cursor = document.get_word_before_cursor()

        # Find the closest prefix symbol before cursor position
        len(text)

        # Look for the rightmost / or @ symbol that's relevant to cursor position
        slash_pos = text.rfind("/")
        at_pos = text.rfind("@")

        # Determine which completion type to use based on what's closest to cursor
        # and not separated by a space
        active_slash = False
        active_at = False

        if slash_pos != -1:
            # Check if there's a space between the / and cursor
            text_after_slash = text[slash_pos + 1 :]
            if " " not in text_after_slash:
                active_slash = True

        if at_pos != -1:
            # Check if there's a space between the @ and cursor
            text_after_at = text[at_pos + 1 :]
            if " " not in text_after_at:
                active_at = True

        # If both are active, use the one that's closer to cursor
        if active_slash and active_at:
            if slash_pos > at_pos:
                active_at = False
            else:
                active_slash = False

        # Handle slash command completions
        if active_slash:
            command_prefix = text[slash_pos + 1 :]

            # Get all matching slash commands
            matching_commands = []
            for command in self.slash_commands:
                # Remove the leading / from stored commands for comparison
                command_name = command.lstrip("/")
                # Show commands that match the prefix after / (or all commands if no prefix)
                if not command_prefix or command_name.lower().startswith(command_prefix.lower()):
                    matching_commands.append(command)

            # Sort commands alphabetically
            matching_commands.sort()

            for command in matching_commands:
                command_name = command.lstrip("/")  # Remove leading /
                if command_prefix:
                    # Provide full command with / and replace from the / position
                    completion_text = "/" + command_name
                    start_position = -(len(command_prefix) + 1)  # +1 to include the /
                else:
                    # If no prefix (just /), show the full command name
                    completion_text = command_name
                    start_position = 0

                yield Completion(completion_text, display=command, start_position=start_position)

        # Handle @ file completions
        elif active_at:
            at_pos = text.rfind("@")
            file_prefix = text[at_pos + 1 :]

            # Get files with smart prioritization and limited display
            try:
                current_dir = Path.cwd()
                matching_files = []

                # Maximum files to show for compact display (6 rows × 3 cols = 18)
                MAX_COMPLETIONS = 18

                for file_path in current_dir.rglob("*"):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(current_dir)
                        filename = str(relative_path)

                        # Skip hidden files and files in hidden directories
                        if any(part.startswith(".") for part in relative_path.parts):
                            continue

                        # Show files that match the prefix after @ (or all files if no prefix)
                        # Match on basename for easier file selection
                        basename = Path(filename).name
                        if not file_prefix or basename.lower().startswith(file_prefix.lower()):
                            # Calculate directory depth for prioritization
                            depth = len(relative_path.parts) - 1
                            matching_files.append((filename, depth))

                # Smart sorting: prioritize by directory depth, then alphabetically
                # Depth 0 = current directory files (highest priority)
                matching_files.sort(key=lambda x: (x[1], x[0].lower()))

                # Limit to MAX_COMPLETIONS for compact display
                total_matches = len(matching_files)
                files_to_show = matching_files[:MAX_COMPLETIONS]

                for filename, _ in files_to_show:
                    # Abbreviate very long paths for better display
                    display_name = PathUtils.abbreviate_path(filename) if len(filename) > 40 else filename

                    yield Completion(filename, display=display_name, start_position=-len(file_prefix))

                # Add indicator if more files are available
                if total_matches > MAX_COMPLETIONS:
                    remaining = total_matches - MAX_COMPLETIONS
                    yield Completion(
                        "",  # Empty completion text
                        display=f"... and {remaining} more files (type more to filter)",
                        start_position=-len(file_prefix),
                    )
            except (OSError, PermissionError):
                pass

        # If no specific prefix is active, provide fallback completions
        # If text contains file-like patterns, suggest path completions
        elif any(ext in text.lower() for ext in [".mp4", ".mp3", ".avi", ".mov", ".jpg", ".png", ".gif"]):
            yield from self.path_completer.get_completions(document, complete_event)

        # If text contains media files from context, suggest them
        elif self.media_files and word_before_cursor:
            for media_file in self.media_files:
                filename = Path(media_file).name
                if filename.lower().startswith(word_before_cursor.lower()):
                    yield Completion(filename[len(word_before_cursor) :], display=filename)

        # Otherwise suggest operation keywords
        elif word_before_cursor:
            for keyword in self.operation_keywords:
                if keyword.lower().startswith(word_before_cursor.lower()):
                    yield Completion(keyword[len(word_before_cursor) :], display=keyword)


def create_input_box(
    placeholder: str = "Type your command (e.g., convert video.mp4 to .mp3) or /help for commands",
    slash_commands: list[str] | None = None,
    media_files: list[str] | None = None,
    session: PromptSession | None = None,
) -> tuple[str, PromptSession]:
    """Create a simple input prompt with completion support."""

    # TTY detection and terminal capability handling
    is_tty = sys.stdin.isatty() and sys.stdout.isatty()

    # Disable CPR (Cursor Position Requests) for non-TTY or limited terminals
    # This prevents "WARNING: your terminal doesn't support cursor position requests (CPR)"
    if not is_tty or os.getenv("TERM") in ("dumb", "unknown"):
        os.environ["PROMPT_TOOLKIT_NO_CPR"] = "1"

    # Create or reuse prompt session for persistent history
    if session is None:
        from prompt_toolkit.history import InMemoryHistory

        history = InMemoryHistory()
        session = PromptSession(history=history)

    # Setup completer
    slash_commands = slash_commands or []
    completer = MediaCompleter(slash_commands, media_files)

    # Key bindings
    kb = KeyBindings()

    @kb.add("c-j", eager=True)  # Ctrl+J for multiline
    def _(event):
        """Insert newline on Ctrl+J."""
        event.current_buffer.insert_text("\n")

    @kb.add("c-l", eager=True)  # Ctrl+L to clear screen
    def _(event):
        """Clear screen on Ctrl+L."""
        clear()

    @kb.add("@")  # Trigger completion when @ is typed
    def _(event):
        """Insert @ and trigger completion."""
        event.current_buffer.insert_text("@")
        event.current_buffer.start_completion()

    @kb.add("/")  # Trigger completion when / is typed
    def _(event):
        """Insert / and trigger completion."""
        event.current_buffer.insert_text("/")
        event.current_buffer.start_completion()

    @kb.add(Keys.Any)  # Handle any printable character
    def _(event):
        """Handle any character and maintain completion if after @ or /."""
        # Get the key that was pressed
        key = event.key_sequence[0].key

        # Only handle printable characters (not control keys)
        if len(key) == 1 and key.isprintable() and key not in ["@", "/"]:
            buffer = event.current_buffer
            buffer.insert_text(key)

            text_before_cursor = buffer.document.text_before_cursor

            # Check if we're typing after @ symbol
            if "@" in text_before_cursor:
                at_pos = text_before_cursor.rfind("@")
                # Trigger completion if there's no space between @ and cursor
                text_after_at = text_before_cursor[at_pos + 1 :]
                if " " not in text_after_at:
                    buffer.start_completion()

            # Check if we're typing after / symbol (check independently, not elif)
            if "/" in text_before_cursor:
                slash_pos = text_before_cursor.rfind("/")
                # Trigger completion if there's no space between / and cursor
                text_after_slash = text_before_cursor[slash_pos + 1 :]
                if " " not in text_after_slash:
                    buffer.start_completion()

    # Override Tab key to accept completion instead of navigate
    @kb.add("tab", eager=True)
    def _(event):
        """Accept the current completion with Tab."""
        buffer = event.current_buffer
        if buffer.complete_state:
            if buffer.complete_state.current_completion:
                # Accept the current completion and close the dropdown
                buffer.apply_completion(buffer.complete_state.current_completion)
            else:
                # No completion selected yet, select first one
                buffer.complete_next()
        else:
            # If no completion active, do nothing (don't insert tab)
            pass

    # Use arrow keys for completion navigation (with history fallback)
    @kb.add("down", filter=has_completions)
    def _(event):
        """Navigate down in completion menu."""
        event.current_buffer.complete_next()

    @kb.add("up", filter=has_completions)
    def _(event):
        """Navigate up in completion menu."""
        event.current_buffer.complete_previous()

    # Style definition
    style = Style.from_dict(
        {
            "prompt": "#00aa00 bold",  # Green prompt
            "input": "#ffffff",  # White input text
            "placeholder": "#888888 italic",  # Gray placeholder
            "completion-menu": "noinherit",  # No inherited styles
            "completion-menu.completion": "noinherit fg:#888888",  # Gray text, no background
            "completion-menu.completion.current": "noinherit fg:#ffffff bold",  # White bold selection, no background
            "completion-menu.meta": "noinherit fg:#666666",  # Dark gray meta text
            "completion-menu.border": "",  # No border
            "scrollbar": "",  # No scrollbar
            "scrollbar.background": "",  # No scrollbar background
            "scrollbar.button": "",  # No scrollbar button
        }
    )

    result = ""

    try:
        # Configure prompt parameters based on terminal capabilities
        prompt_kwargs = {
            "multiline": False,  # Enter submits, Ctrl+J for newline
            "key_bindings": kb,
            "style": style,
            "wrap_lines": True,
            "mouse_support": False,  # Always disabled for compatibility
            "enable_history_search": True,
        }

        # Adjust settings for limited terminal environments
        if is_tty:
            # Full TTY capabilities
            prompt_kwargs.update(
                {
                    "placeholder": HTML(f"<placeholder>{placeholder}</placeholder>"),
                    "complete_style": CompleteStyle.MULTI_COLUMN,
                    "completer": completer,
                    "complete_while_typing": True,
                }
            )
        else:
            # Limited terminal - disable advanced features that may cause issues
            prompt_kwargs.update(
                {
                    "placeholder": None,  # Skip placeholder for non-TTY
                    "complete_style": CompleteStyle.COLUMN,  # Simpler completion style
                    "completer": None,  # Disable completion for non-TTY
                    "complete_while_typing": False,
                    "enable_history_search": False,  # Disable for non-TTY
                }
            )

        # Get input with configured features
        result = session.prompt(HTML("<prompt>mediallm> </prompt>"), **prompt_kwargs)

        return (result.strip() if result else "", session)

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        raise KeyboardInterrupt()  # Re-raise to let caller handle

    except EOFError:
        # Handle Ctrl+D gracefully
        raise EOFError()  # Re-raise to let caller handle

    except Exception as e:
        # Handle prompt-toolkit internal errors that cause session corruption
        # This includes "Application is not running" and similar state errors
        error_msg = str(e).lower()
        if any(
            phrase in error_msg
            for phrase in [
                "application is not running",
                "application.exit() failed",
                "event loop",
            ]
        ):
            # Session is corrupted, return None to force a fresh session
            return ("", None)
        # Other exceptions should be re-raised
        raise


def get_enhanced_prompt(
    placeholder: str = "Type your command (e.g., convert video.mp4 to .mp3)",
    slash_commands: list[str] | None = None,
    media_files: list[str] | None = None,
    session: PromptSession | None = None,
) -> tuple[str, PromptSession]:
    """Wrapper function for backward compatibility."""
    return create_input_box(placeholder, slash_commands, media_files, session)


def get_multiline_prompt(
    placeholder: str = "Type your command (e.g., convert video.mp4 to .mp3)",
) -> str:
    """Backward compatibility wrapper for the original function signature."""
    try:
        result, _ = create_input_box(placeholder)
        return result
    except KeyboardInterrupt:
        return ""


def get_simple_prompt(prompt_text: str = "mediallm> ") -> str:
    """Get a simple single-line prompt with basic styling."""
    from prompt_toolkit.formatted_text import HTML

    try:
        return prompt(
            HTML(f"<prompt>{prompt_text}</prompt>"),
            style=Style.from_dict({"prompt": "#00aa00 bold"}),
        ).strip()
    except KeyboardInterrupt:
        return ""
