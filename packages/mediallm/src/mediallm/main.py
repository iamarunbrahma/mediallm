#!/usr/bin/env python3
# Author: Arun Brahma

import sys

try:
    from mediallm.interface.terminal_interface import app as terminal_app
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
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if __debug__:  # Show traceback in debug mode
            import traceback

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
    for module_name, description in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing_modules.append(f"{module_name} ({description})")

    if missing_modules:
        print("Error: Missing required dependencies:", file=sys.stderr)
        for module in missing_modules:
            print(f"  - {module}", file=sys.stderr)
        print("\nPlease install missing dependencies and try again.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
