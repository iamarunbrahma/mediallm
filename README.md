<pre>
                ███╗   ███╗███████╗██████╗ ██╗ █████╗ ██╗     ██╗     ███╗   ███╗
                ████╗ ████║██╔════╝██╔══██╗██║██╔══██╗██║     ██║     ████╗ ████║
                ██╔████╔██║█████╗  ██║  ██║██║███████║██║     ██║     ██╔████╔██║
                ██║╚██╔╝██║██╔══╝  ██║  ██║██║██╔══██║██║     ██║     ██║╚██╔╝██║
                ██║ ╚═╝ ██║███████╗██████╔╝██║██║  ██║███████╗███████╗██║ ╚═╝ ██║
                ╚═╝     ╚═╝╚══════╝╚═════╝ ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚═╝
</pre>

<div align="center">

**Natural language to FFmpeg, instantly and privately.**

*Privacy-First • Local LLM • FFmpeg made effortless*

[![PyPI - Version](https://img.shields.io/pypi/v/mediallm?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/mediallm/)
[![Python Version](https://img.shields.io/badge/python-3.10+-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![FFmpeg](https://img.shields.io/badge/requires-FFmpeg-red?style=flat-square&logo=ffmpeg)](https://ffmpeg.org)

<p align="center">
<a href="#installation">Installation</a> • 
<a href="#quick-start">Quick Start</a> • 
<a href="#usage">Usage</a> • 
<a href="#configuration">Configuration</a> • 
<a href="#contributing">Contributing</a>
</p>

</div>

---

## Overview

MediaLLM transforms media processing by bridging the gap between human language and FFmpeg complexity. This Python package enables you to manipulate videos, audio files, images, and subtitles using simple, conversational commands powered by local AI models.

Instead of memorizing complex FFmpeg syntax, simply describe what you want: "make this video square for Instagram," "extract the audio as high-quality MP3," or "create a 10-second GIF from the middle of this video." MediaLLM understands your intent and generates the precise commands needed, all while keeping your data completely private through local processing.

## Why MediaLLM?

Whether you're a developer automating video workflows, a content creator resizing clips for social media, or someone who just needs to convert files without diving into technical manuals, MediaLLM meets you where you are.

- **Skip the FFmpeg manual** - Say goodbye to cryptic command syntax and endless documentation searches
- **Actually free** - No monthly subscriptions, API costs, or usage caps to worry about
- **Works with everything** - Video, audio, images, subtitles - if FFmpeg can handle it, so can you
- **Plays nice with AI tools** - Built-in MCP server connects seamlessly with Claude and other AI agents  
- **Code when you want to** - Python API available for when you need programmatic control
- **Just works** - Simple CLI that gets out of your way and lets you focus on creating

## Installation

### Prerequisites

| Component | Version | macOS | Linux |
|-----------|---------|-------|-------|
| Python | 3.10+ | `brew install python` | `sudo apt install python3` |
| FFmpeg | Latest | `brew install ffmpeg` | `sudo apt install ffmpeg` |
| Ollama | Latest | `brew install ollama` | curl -fsSL https://ollama.com/install.sh | sh |

### Install MediaLLM

```bash
# Install from PyPI
pip install mediallm

# Alternative: using uv (faster)
uv add mediallm

# Development installation
git clone https://github.com/iamarunbrahma/mediallm.git
cd mediallm
pip install -e .
```

### Install MediaLLM MCP

```bash
# Install from PyPI
pip install mediallm-mcp

# Alternative: using uv (faster)
uv add mediallm-mcp
```

## Quick Start

```bash
# 1. Start Ollama and pull a model
ollama serve
ollama pull llama3.1:latest

# 2. Convert media with natural language
mediallm "convert video.mp4 to MP3 audio"
mediallm "resize video.mov to 720p with high quality"
mediallm "create 10-second GIF from video.mp4 starting at 1 minute"

# 3. Preview commands before execution
mediallm --dry-run "compress large-video.mkv to smaller size"
```

## Usage

### CLI Commands

```bash
# Video Operations
mediallm "convert video.mov to MP4 format"
mediallm "compress large-video.mp4 to 50% size"
mediallm "extract thumbnail at 30 seconds from video.mp4"
mediallm "make video.mp4 square format for Instagram"

# Audio Operations
mediallm "extract audio from movie.mp4 as high quality MP3"
mediallm "convert song.wav to AAC format"
mediallm "reduce audio volume by 50% in video.mp4"

# Creative Operations
mediallm "create animated GIF from first 5 seconds of video.mp4"
mediallm "extract frame at 2:15 from video.mp4"
mediallm "add fade in/out effects to video.mp4"

# Batch Operations
mediallm "convert all MKV files to MP4 format"
mediallm "extract audio from all videos in folder"
```

### Python API

```python
import mediallm

# Initialize MediaLLM
ml = mediallm.MediaLLM()

# Scan workspace for media files
files = ml.scan_workspace()
print(f"Found {len(files['videos'])} videos")

# Generate commands from natural language
request = "convert video.mp4 to high-quality MP3"
commands = ml.generate_command(request)

# Execute generated commands
for cmd in commands:
    print(f"Running: {' '.join(cmd)}")
    # subprocess.run(cmd) # Execute the command
```

### Configuration (Optional)

MediaLLM works out-of-the-box with sensible defaults. Customize only if needed:

**Common Adjustments:**
- `MEDIALLM_MODEL` - Switch between different Ollama models (default: llama3.1:latest)
- `MEDIALLM_OUTPUT_DIR` - Change where converted files are saved (default: current directory)

**Advanced Settings:**
- `MEDIALLM_OLLAMA_HOST` - Connect to Ollama on a different machine (default: http://localhost:11434)
- `MEDIALLM_TIMEOUT` - Increase for complex operations (default: 60s)
- `MEDIALLM_DRY_RUN` - Always preview commands without executing (default: false)

Set via environment variables or create a `.env` file in your project directory.

## Architecture

<div align="center">

```
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│  Natural Language │     │    Local LLM      │     │ FFmpeg Commands   │     │   Media Output    │
│ "convert vid.mp4" │ --> │     (Ollama)      │ --> │  ffmpeg -i ...    │ --> │   output.mp4      │
│                   │     │                   │     │                   │     │                   │
└───────────────────┘     └───────────────────┘     └───────────────────┘     └───────────────────┘
```
</div>

## MCP Server

MediaLLM includes an MCP (Model Context Protocol) server for integration with AI agents:

### Usage

```bash
# Default: STDIO transport (for Claude Desktop, etc.)
mediallm-mcp

# SSE transport (for web integrations)
mediallm-mcp --sse --port 3001

# HTTP transport (for custom integrations)  
mediallm-mcp --http --port 3001
```

### Running in Docker

```bash
# Build the Docker image
cd packages/mediallm-mcp
docker build -t mediallm-mcp .

# Run with volume mounting for media file access
docker run -it --rm \
  -v /path/to/your/media:/workspace \
  mediallm-mcp
```

### Claude Code

Works automatically when `mediallm-mcp` is installed in the active environment. Open the tools panel to discover available tools.

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mediallm-mcp": {
      "command": "mediallm-mcp"
    }
  }
}
```

### Cursor

[![Add to Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=mediallm-mcp&config=eyJjb21tYW5kIjogIm1lZGlhbGxtLW1jcCIsICJhcmdzIjogW119)

Or manually create `.cursor/mcp.json` in your project (or edit the global `~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "mediallm-mcp": {
      "command": "mediallm-mcp"
    }
  }
}
```

**Available Tools:**
- `generate_command` - Convert natural language to FFmpeg commands
- `scan_workspace` - Discover media files in directories


### Debugging

```bash
# Enable verbose logging
mediallm-mcp --debug

# Test alternate transports with debug
mediallm-mcp --sse --port 3001 --debug
mediallm-mcp --http --port 3001 --debug
```

If the server is not detected:
- Ensure the command is available: `mediallm-mcp --help`
- Restart the client (Claude Desktop, Claude Code, or Cursor)
- Verify Ollama is running if using local LLMs


## Contributing

Help make MediaLLM better for everyone! Whether you're fixing bugs, adding features, or improving documentation, your contributions matter.

**Get Started:**
- Fork the repo and create a feature branch
- Check out [CONTRIBUTING.md](CONTRIBUTING.md) for development setup
- Run `make help` to see available development commands
- Make your changes and add tests
- Submit a pull request

**Have Ideas or Issues?**
- **Found a bug?** [Open an issue](https://github.com/iamarunbrahma/mediallm/issues) with details to reproduce
- **Want a feature?** [Start a discussion](https://github.com/iamarunbrahma/mediallm/discussions) to share your ideas  

## License

MIT License - use it, modify it, share it. See [LICENSE](LICENSE) for the fine print.

---

<div align="center">

**Made by [Arun Brahma](https://github.com/iamarunbrahma)**

[⭐ Star on GitHub](https://github.com/iamarunbrahma/mediallm) • 
[🐛 Report Issues](https://github.com/iamarunbrahma/mediallm/issues)

</div>