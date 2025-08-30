#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

import contextlib
import random
import signal
import sys
import threading
import time
from typing import TYPE_CHECKING
from typing import Any
from typing import Final

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.widgets import TextArea
from rich.console import Console
from rich.live import Live
from rich.text import Text

if TYPE_CHECKING:
    from collections.abc import Callable


class LLMSpinner:
    """ASCII spinner with processing words for LLM waiting periods with interrupt handling."""

    # Class constants
    _SPINNER_CHARS: Final[list[str]] = [
        "⠋",
        "⠙",
        "⠹",
        "⠸",
        "⠼",
        "⠴",
        "⠦",
        "⠧",
        "⠇",
        "⠏",
    ]
    _PROCESSING_WORDS: Final[list[str]] = [
        "Cooking",
        "Brewing",
        "Mixing",
        "Blending",
        "Crafting",
        "Forging",
        "Dissolving",
        "Melting",
        "Crystallizing",
        "Distilling",
        "Fermenting",
        "Simmering",
        "Marinating",
        "Seasoning",
        "Grilling",
        "Roasting",
        "Baking",
        "Steaming",
        "Churning",
        "Whipping",
        "Kneading",
        "Assembling",
        "Building",
        "Constructing",
        "Weaving",
        "Spinning",
        "Polishing",
        "Refining",
        "Processing",
        "Transforming",
        "Converting",
        "Generating",
        "Computing",
        "Calculating",
        "Analyzing",
        "Parsing",
        "Compiling",
        "Rendering",
        "Encoding",
        "Decoding",
        "Optimizing",
    ]
    _WORD_CHANGE_INTERVAL: Final[int] = 20
    _REFRESH_RATE: Final[int] = 10
    _ANIMATION_DELAY: Final[float] = 0.1
    _TERMINAL_RESET_DELAY: Final[float] = 0.1

    def __init__(
        self,
        console: Console | None = None,
        allow_escape: bool = True,
        interrupt_callback: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the spinner with console and interrupt handling."""
        self.console = console or Console()
        self.allow_escape = allow_escape
        self.interrupt_callback = interrupt_callback

        # Spinner state
        self.is_spinning = False
        self.current_word_index = 0
        self.current_char_index = 0

        # Threading components
        self.spinner_thread: threading.Thread | None = None
        self.kb_thread: threading.Thread | None = None
        self.live: Live | None = None

        # Interrupt handling
        self.interrupted = False
        self.interrupt_reason = ""
        self.kb_app: Application | None = None
        self.original_sigint_handler = None
        self._app_running = False
        self._stop_event = threading.Event()
        self._thread_lock = threading.Lock()

    def start(self, message: str = "your request") -> None:
        """Start the spinning animation."""
        if self.is_spinning:
            return

        self._initialize_spinner_state()
        self._setup_interrupt_handlers()
        self._create_live_display(message)
        self._start_animation_thread(message)

    def stop(self) -> None:
        """Stop the spinning animation and clear the display."""
        if not self.is_spinning:
            return

        self.is_spinning = False
        self._stop_event.set()
        self._cleanup_interrupt_handlers()
        self._stop_live_display()
        self._stop_animation_thread()

    def is_interrupted(self) -> bool:
        """Check if the spinner was interrupted by user."""
        return self.interrupted

    def get_interrupt_reason(self) -> str:
        """Get the reason for interruption."""
        return self.interrupt_reason

    def wait_for_completion_or_interrupt(self, timeout: float | None = None) -> bool:
        """Wait for spinner to complete or be interrupted."""
        if not self.is_spinning:
            return True

        start_time = time.time()
        while self.is_spinning and not self.interrupted:
            if timeout and (time.time() - start_time) > timeout:
                break
            time.sleep(self._ANIMATION_DELAY)

        return not self.interrupted

    def _initialize_spinner_state(self) -> None:
        """Initialize spinner state for new animation."""
        self.is_spinning = True
        self.interrupted = False
        self.interrupt_reason = ""
        self.current_word_index = random.randint(0, len(self._PROCESSING_WORDS) - 1)
        self.current_char_index = 0
        self._stop_event.clear()
        self._app_running = False

    def _setup_interrupt_handlers(self) -> None:
        """Setup signal and escape key handlers."""
        self._setup_signal_handler()
        self._setup_escape_detection()

    def _cleanup_interrupt_handlers(self) -> None:
        """Cleanup interrupt handlers."""
        self._cleanup_escape_detection()
        self._restore_signal_handler()

    def _create_live_display(self, message: str) -> None:
        """Create and start the live display."""
        self.live = Live(
            self._get_spinner_text(message),
            console=self.console,
            refresh_per_second=self._REFRESH_RATE,
            transient=True,
        )
        self.live.start()

    def _start_animation_thread(self, message: str) -> None:
        """Start the animation thread."""
        self.spinner_thread = threading.Thread(target=self._animate, args=(message,), daemon=True)
        self.spinner_thread.start()

    def _stop_live_display(self) -> None:
        """Stop the live display."""
        if self.live:
            self.live.stop()
            self.live = None

    def _stop_animation_thread(self) -> None:
        """Stop the animation thread."""
        if self.spinner_thread and self.spinner_thread.is_alive():
            self.spinner_thread.join(timeout=0.5)
        self.spinner_thread = None

    def _setup_signal_handler(self) -> None:
        """Setup signal handler for Ctrl+C interrupts."""

        def sigint_handler(signum, frame):
            self.interrupted = True
            self.interrupt_reason = "Ctrl+C"
            if self.interrupt_callback:
                with contextlib.suppress(Exception):
                    self.interrupt_callback()
            self.stop()

        try:
            self.original_sigint_handler = signal.signal(signal.SIGINT, sigint_handler)
        except (ValueError, OSError):
            # Signal handling might not work in some contexts (e.g., threads)
            pass

    def _restore_signal_handler(self) -> None:
        """Restore the original signal handler."""
        if self.original_sigint_handler is not None:
            try:
                signal.signal(signal.SIGINT, self.original_sigint_handler)
                self.original_sigint_handler = None
            except (ValueError, OSError):
                pass

    def _setup_escape_detection(self) -> None:
        """Setup escape key detection using prompt-toolkit."""
        if not self.allow_escape:
            return

        try:
            # Create key bindings
            kb = KeyBindings()

            @kb.add("escape")
            def _(event):
                """Handle escape key press."""
                self.interrupted = True
                self.interrupt_reason = "Escape"
                if self.interrupt_callback:
                    with contextlib.suppress(Exception):
                        self.interrupt_callback()
                event.app.exit()

            @kb.add("c-c")
            def _(event):
                """Handle Ctrl+C in prompt-toolkit context."""
                self.interrupted = True
                self.interrupt_reason = "Ctrl+C"
                if self.interrupt_callback:
                    with contextlib.suppress(Exception):
                        self.interrupt_callback()
                event.app.exit()

            # Create a minimal application for key detection
            text_area = TextArea(read_only=True, height=0)

            self.kb_app = Application(
                layout=Layout(Window(content=text_area.control)),
                key_bindings=kb,
                full_screen=False,
                mouse_support=False,
            )

            # Run the application in a separate thread
            def run_kb_app():
                try:
                    with self._thread_lock:
                        if self.kb_app and not self.interrupted and not self._stop_event.is_set():
                            self._app_running = True

                    if self._app_running:
                        self.kb_app.run()
                except Exception:
                    # Ignore exceptions during keyboard detection
                    pass
                finally:
                    with self._thread_lock:
                        self._app_running = False

            self.kb_thread = threading.Thread(target=run_kb_app, daemon=True)
            self.kb_thread.start()

        except Exception:
            # If escape detection fails, continue without it
            self.allow_escape = False

    def _cleanup_escape_detection(self) -> None:
        """Cleanup escape key detection."""
        # Signal the thread to stop
        self._stop_event.set()

        if self.kb_app:
            try:
                # Only try to exit if the app is actually running
                with self._thread_lock:
                    if self._app_running:
                        try:
                            self.kb_app.exit()
                        except Exception as e:
                            # Ignore "Application is not running" and similar errors
                            error_msg = str(e).lower()
                            if "application is not running" not in error_msg:
                                # Log unexpected errors but don't fail
                                import logging

                                logging.getLogger(__name__).debug(f"Error exiting keyboard app: {e}")
            except Exception:
                # Ignore all errors during cleanup
                pass
            self.kb_app = None

        if self.kb_thread and self.kb_thread.is_alive():
            with contextlib.suppress(Exception):
                self.kb_thread.join(timeout=0.1)
            self.kb_thread = None

    def _get_spinner_text(self, message: str) -> Text:
        """Generate the current spinner text."""
        text = Text()

        # Add spinner character
        spinner_char = self._SPINNER_CHARS[self.current_char_index]
        text.append(spinner_char, style="dim")
        text.append(" ")

        # Add message with optional processing word
        if message.startswith("Downloading"):
            text.append(message, style="dim")
        else:
            processing_word = self._PROCESSING_WORDS[self.current_word_index]
            text.append(processing_word, style="dim")
            text.append(" ")
            text.append(message, style="dim")

        text.append("...", style="dim")

        # Add interrupt hint if enabled
        if self.allow_escape:
            text.append(" ")
            text.append("(esc to interrupt)", style="dim italic")

        return text

    def _animate(self, message: str) -> None:
        """Animation loop that runs in a separate thread."""
        word_change_counter = 0

        while self.is_spinning and not self.interrupted:
            self._update_spinner_character()
            word_change_counter = self._update_processing_word(word_change_counter)
            self._update_display(message)
            time.sleep(self._ANIMATION_DELAY)

        if self.interrupted:
            self.stop()

    def _update_spinner_character(self) -> None:
        """Update the spinner character index."""
        self.current_char_index = (self.current_char_index + 1) % len(self._SPINNER_CHARS)

    def _update_processing_word(self, counter: int) -> int:
        """Update processing word periodically."""
        counter += 1
        if counter >= self._WORD_CHANGE_INTERVAL:
            self.current_word_index = random.randint(0, len(self._PROCESSING_WORDS) - 1)
            return 0
        return counter

    def _update_display(self, message: str) -> None:
        """Update the live display with current text."""
        if self.live:
            self.live.update(self._get_spinner_text(message))

    def _reset_terminal_state(self) -> None:
        """Reset terminal state to prevent corruption after spinner operations."""
        reset_sequence = "\r\033[K\033[0m\033[?25h\033[?1000l\033[?47l"

        try:
            if hasattr(self.console, "file") and self.console.file:
                self.console.file.write(reset_sequence)
                self.console.file.flush()
            else:
                sys.stdout.write(reset_sequence)
                sys.stdout.flush()
        except (AttributeError, OSError):
            self._fallback_terminal_reset()

    def _fallback_terminal_reset(self) -> None:
        """Fallback terminal reset method."""
        try:
            sys.stdout.write("\033[0m\033[?25h")
            sys.stdout.flush()
            sys.stderr.flush()
        except OSError:
            self._final_fallback_reset()

    def _final_fallback_reset(self) -> None:
        """Final fallback - just flush streams."""
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except OSError:
            pass

    def __enter__(self) -> LLMSpinner:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit with proper cleanup and interrupt propagation."""
        try:
            self.stop()
        finally:
            self._reset_terminal_state()

        if self.interrupted:
            interrupt_msg = f"Operation interrupted by {self.interrupt_reason}"
            if self.interrupt_reason == "Escape":
                interrupt_msg += " key"
            raise KeyboardInterrupt(interrupt_msg)


def show_llm_spinner(
    console: Console | None = None,
    message: str = "your request",
    allow_escape: bool = True,
    interrupt_callback: Callable[[], None] | None = None,
) -> LLMSpinner:
    """Create and start an LLM spinner.

    Args:
        console: Rich console instance for output
        message: Message to display with spinner
        allow_escape: Whether to enable escape key detection
        interrupt_callback: Optional callback to run on interrupt

    Returns:
        Started LLMSpinner instance
    """
    spinner = LLMSpinner(console, allow_escape, interrupt_callback)
    spinner.start(message)
    return spinner
