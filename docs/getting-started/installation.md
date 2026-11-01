# Installation

## Prerequisites

You need three components:

- **Python 3.10+** - Core runtime
- **FFmpeg** - Media processing  
- **Ollama** - Local LLM provider

### Quick Setup

=== "macOS"
    ```bash
    brew install ffmpeg ollama
    ```

=== "Linux"
    ```bash
    sudo apt install ffmpeg
    curl -fsSL https://ollama.com/install.sh | sh
    ```

=== "Windows"
    Use WSL with Ubuntu and follow Linux instructions.

## Install MediaLLM

```bash
pip install mediallm
```

### Install this checkout with Python 3.10–3.15

From the repository root, install the CLI with uv:

```bash
uv tool install --python 3.14 ./packages/mediallm
mediallm --help
```

Select any Python version from 3.10 through 3.15 using `--python`.
Python 3.14 and 3.15 require the updated Pydantic dependency in this checkout.
Older releases pinned to Pydantic 2.11.0 can fail while building
`pydantic-core` with a PyO3 Python-version compatibility error. Install the
local package above to use this fix until it is included in a PyPI release.

For MCP server integration:
```bash
pip install mediallm-mcp
```

## Setup Ollama

```bash
# Start Ollama
ollama serve

# In another terminal, pull a model
ollama pull llama3.1:latest
```

## Verify Installation

```bash
# Test basic functionality
mediallm --version
mediallm --dry-run "convert test.mp4 to mp3"
```

## Next Steps

- [Quick Start →](quickstart.md)
- [CLI Usage →](../user-guide/cli.md)
- [Python API →](../user-guide/python-api.md)
