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