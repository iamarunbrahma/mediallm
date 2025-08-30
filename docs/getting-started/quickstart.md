# Quick Start

Get up and running with MediaLLM in under 5 minutes.

## Your First Command

Convert a video to audio:

```bash
mediallm "convert video.mp4 to MP3"
```

MediaLLM will analyze your request, generate the FFmpeg command, and execute it.

## Common Operations

### Video Processing
```bash
# Convert format
mediallm "convert movie.avi to MP4"

# Resize video  
mediallm "resize video.mp4 to 720p"

# Extract clip
mediallm "extract 30 seconds from video.mp4 starting at 2:15"
```

### Audio Operations
```bash
# Extract audio
mediallm "extract audio from video.mp4 as MP3"

# Convert audio format
mediallm "convert song.wav to AAC"
```

### Creative Operations
```bash
# Create GIF
mediallm "create 10-second GIF from video.mp4 starting at 30 seconds"

# Extract thumbnail
mediallm "extract frame at 2:15 from movie.mp4"
```

## Preview Mode

Always preview commands before execution:

```bash
mediallm --dry-run "compress large-video.mkv"
```

## Configuration

Set these environment variables to customize behavior:

```bash
# Use different Ollama model
export MEDIALLM_MODEL="llama3.2:latest"

# Change Ollama host
export MEDIALLM_OLLAMA_HOST="http://192.168.1.100:11434"  

# Always preview (don't execute)
export MEDIALLM_DRY_RUN="true"
```

Or create a `.env` file in your project:
```bash
MEDIALLM_MODEL=llama3.2:latest
MEDIALLM_OLLAMA_HOST=http://localhost:11434
```

## Next Steps

- [CLI Usage →](../user-guide/cli.md) - Complete command reference
- [Python API →](../user-guide/python-api.md) - Use in your scripts  
- [MCP Server →](../user-guide/mcp-server.md) - AI agent integration