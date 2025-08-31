# Python API

Use MediaLLM programmatically in your Python applications.

## Quick Start

```python
import mediallm

# Initialize MediaLLM
ml = mediallm.MediaLLM()

# Generate commands from natural language
commands = ml.generate_command("convert video.mp4 to MP3")
print("Generated commands:", commands)

# Scan for media files
workspace = ml.scan_workspace()
print(f"Found {len(workspace.get('videos', []))} videos")
```

## MediaLLM Class

### Initialization

```python
ml = mediallm.MediaLLM(
    workspace=None,                        # Pre-scanned workspace
    ollama_host="http://localhost:11434",  # Ollama server URL
    model_name="llama3.1:latest",          # LLM model to use
    timeout=60,                            # Request timeout
    working_dir=None                       # Working directory
)
```

### Core Methods

#### generate_command()

Convert natural language to executable FFmpeg commands.

```python
# Basic usage - returns executable commands
commands = ml.generate_command("convert video.mp4 to MP3")
for cmd in commands:
    print(" ".join(cmd))  # Print the command

# Get raw plan object instead
plan = ml.generate_command("extract audio", return_raw=True)
print(plan.action)  # Action enum
print(plan.inputs)  # Input file paths
```

**Parameters:**

- `request` (str): Natural language description
- `return_raw` (bool): Return CommandPlan object vs executable commands
- `assume_yes` (bool): Skip confirmation prompts

#### scan_workspace()

Discover media files in a directory.

```python
# Scan current directory
workspace = ml.scan_workspace()

# Scan specific directory
workspace = ml.scan_workspace("/path/to/media")
```

**Returns:**

```python
{
    "cwd": "/path/to/directory",
    "videos": ["video1.mp4", "video2.avi"],
    "audios": ["audio1.mp3", "audio2.wav"],
    "images": ["image1.jpg", "image2.png"],
    "subtitle_files": ["subs.srt"]
}
```

### Properties

#### available_files

Get categorized media files:

```python
files = ml.available_files
print(files["videos"])     # List of video files
print(files["audios"])     # List of audio files  
print(files["images"])     # List of image files
print(files["subtitles"])  # List of subtitle files
```

#### workspace

Access current workspace data:

```python
workspace = ml.workspace  # Auto-scans if not initialized
```

## Complete Example

```python
import mediallm
import subprocess
from pathlib import Path

def process_media_batch():
    # Initialize with custom settings
    ml = mediallm.MediaLLM(
        model_name="llama3.2:latest",
        timeout=120
    )
    
    # Scan for media files
    workspace = ml.scan_workspace("./input_media")
    
    # Process each video
    for video_path in workspace["videos"]:
        video = Path(video_path).name
        
        try:
            # Generate commands for audio extraction
            commands = ml.generate_command(
                f"extract audio from {video} as high quality MP3"
            )
            
            # Execute commands
            for cmd in commands:
                result = subprocess.run(cmd, check=True, capture_output=True)
                print(f"Processed {video}: {result.returncode}")
                
        except Exception as e:
            print(f"Error processing {video}: {e}")

if __name__ == "__main__":
    process_media_batch()
```

## Error Handling

```python
from mediallm.utils.exceptions import TranslationError

try:
    commands = ml.generate_command("invalid request that makes no sense")
except TranslationError as e:
    print(f"Could not understand request: {e}")
except RuntimeError as e:
    print(f"System error: {e}")
```

## Next Steps

- [CLI Usage →](cli.md) - Command-line interface
- [MCP Server →](mcp-server.md) - AI agent integration