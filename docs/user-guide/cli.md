# CLI Usage

Complete reference for the MediaLLM command-line interface.

## Basic Syntax

```bash
mediallm [OPTIONS] "your request"
```

## Command Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview command without executing |
| `--version` | Show version information |
| `--help` | Show help message |

## Core Operations

### Video Processing
```bash
# Format conversion
mediallm "convert video.mov to MP4"

# Resize video
mediallm "resize video.mp4 to 720p"

# Compress video
mediallm "compress large-video.mp4"

# Extract clip
mediallm "trim video.mp4 from 0:30 to 2:00"
```

### Audio Operations
```bash
# Extract audio
mediallm "extract audio from video.mp4 as MP3"

# Convert audio format
mediallm "convert music.wav to MP3"

# Remove audio
mediallm "remove audio from video.mp4"
```

### Creative Operations
```bash
# Extract thumbnail
mediallm "extract frame from video.mp4 at 30 seconds"

# Create GIF
mediallm "create GIF from video.mp4 first 5 seconds"

# Create slideshow
mediallm "create slideshow from images in folder"
```

## Batch Processing

```bash
# Process all files of a type
mediallm "convert all MKV files to MP4"
mediallm "extract audio from all videos"
```

## Output Behavior

### File Naming
- **Conversions**: `input_converted.mp4`
- **Audio extractions**: `input_audio.mp3`  
- **Thumbnails**: `input_frame.jpg`

### Custom Output
```bash
mediallm "convert input.avi to MP4 and save as output.mp4"
```

## Tips

!!! tip "Be Specific"
    ```bash
    # Good
    mediallm "convert video.mp4 to high quality MP4"
    
    # Too vague
    mediallm "convert video"
    ```

!!! info "Preview First"
    ```bash
    mediallm --dry-run "compress large-video.mp4"
    ```

## Next Steps

- [Python API →](python-api.md) - Programmatic usage
- [MCP Server →](mcp-server.md) - AI agent integration