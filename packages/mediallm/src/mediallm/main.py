#!/usr/bin/env python3
# Author: Arun Brahma

import sys
import traceback

try:
    from mediallm.interface.terminal_interface import app as terminal_app
    from mediallm.utils.exceptions import ConfigError
    from mediallm.utils.exceptions import ConstructionError
    from mediallm.utils.exceptions import ExecError
    from mediallm.utils.exceptions import MediaLLMError
    from mediallm.utils.exceptions import SecurityError
    from mediallm.utils.exceptions import TranslationError
    from mediallm.utils.exceptions import ValidationError
except ImportError as e:
    print(f"Error: Failed to import MediaLLM components: {e}", file=sys.stderr)
    print("Please ensure MediaLLM is properly installed.", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    """Entry point for the mediallm CLI with error handling."""
    try:
        # Basic environment validation
        _validate_environment()

        # Initialize and run the terminal application
        terminal_app()

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)  # Standard exit code for Ctrl+C

    except SecurityError as e:
        print(f"Security error: {e.message}", file=sys.stderr)
        sys.exit(2)

    except ValidationError as e:
        print(f"Validation error: {e.message}", file=sys.stderr)
        sys.exit(3)

    except ConfigError as e:
        print(f"Configuration error: {e.message}", file=sys.stderr)
        print("Please check your Ollama installation and configuration.", file=sys.stderr)
        sys.exit(4)

    except TranslationError as e:
        print(f"Translation error: {e.message}", file=sys.stderr)
        print("Try rephrasing your request or using a different model.", file=sys.stderr)
        sys.exit(5)

    except ConstructionError as e:
        print(f"Command construction error: {e.message}", file=sys.stderr)
        sys.exit(6)

    except ExecError as e:
        print(f"Execution error: {e.message}", file=sys.stderr)
        sys.exit(7)

    except MediaLLMError as e:
        # Catch-all for any other MediaLLM-specific errors
        print(f"Error: {e.message}", file=sys.stderr)
        sys.exit(1)

    except OSError as e:
        print(f"System error: {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if __debug__:  # Show traceback in debug mode
            traceback.print_exc()
        sys.exit(1)


def _validate_environment() -> None:
    """Validate basic environment requirements."""
    # Check Python version

    # Check for required modules
    _check_required_modules()


def _check_required_modules() -> None:
    """Check if required modules are available."""
    required_modules = [
        ("rich", "Rich console library"),
        ("typer", "Typer CLI framework"),
        ("pydantic", "Pydantic data validation"),
    ]

    missing_modules = []

    def _try_import(name: str, desc: str) -> None:
        try:
            __import__(name)
        except ImportError:
            missing_modules.append(f"{name} ({desc})")

    for module_name, description in required_modules:
        _try_import(module_name, description)

    if missing_modules:
        print("Error: Missing required dependencies:", file=sys.stderr)
        for module in missing_modules:
            print(f"  - {module}", file=sys.stderr)
        print("\nPlease install missing dependencies and try again.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
