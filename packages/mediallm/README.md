<pre>
                                ███╗   ███╗███████╗██████╗ ██╗ █████╗ ██╗     ██╗     ███╗   ███╗
                                ████╗ ████║██╔════╝██╔══██╗██║██╔══██╗██║     ██║     ████╗ ████║
                                ██╔████╔██║█████╗  ██║  ██║██║███████║██║     ██║     ██╔████╔██║
                                ██║╚██╔╝██║██╔══╝  ██║  ██║██║██╔══██║██║     ██║     ██║╚██╔╝██║
                                ██║ ╚═╝ ██║███████╗██████╔╝██║██║  ██║███████╗███████╗██║ ╚═╝ ██║
                                ╚═╝     ╚═╝╚══════╝╚═════╝ ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚═╝
</pre>

<div align="center">

**Natural language to FFmpeg, instantly and privately**

[![PyPI version](https://img.shields.io/pypi/v/mediallm)](https://pypi.org/project/mediallm/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## Quick Start

**Install MediaLLM:**
```bash
pip install mediallm
```

**Setup prerequisites:**
```bash
# Install Ollama (local LLM)
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
ollama pull llama3.1:latest

# Install FFmpeg
brew install ffmpeg  # macOS
# sudo apt install ffmpeg  # Linux
```

---

## CLI Usage

```bash
# Convert video to audio
mediallm "convert video.mp4 to MP3 audio"

# Resize and compress
mediallm "compress large_video.mp4 to 720p"

# Create GIF from video
mediallm "create 10-second GIF from video.mp4 starting at 1 minute"

# Preview command (dry-run)
mediallm --dry-run "extract audio from movie.avi"
```

---

## Python API Usage

### Basic Usage
```python
import mediallm

# Initialize MediaLLM
ml = mediallm.MediaLLM()

# Generate FFmpeg commands from natural language
commands = ml.generate_command("convert video.mp4 to high-quality MP3")
print("Generated commands:", commands)

# Scan workspace for media files
workspace = ml.scan_workspace()
print(f"Found {len(workspace.get('videos', []))} videos")
```

### Advanced Usage
```python
import mediallm

# Scan directory for media files
workspace = mediallm.discover_media()
print(f"Found {len(workspace.get('videos', []))} videos")

# Initialize with custom settings
ml = mediallm.MediaLLM(
    workspace=workspace,
    model_name="llama3.1:latest", 
    ollama_host="http://localhost:11434",
    timeout=120
)

# Generate commands from natural language
commands = ml.generate_command("compress large_video.mp4 to 720p")
print("Commands:", commands)
```

### Using Data Models
```python
import mediallm
from pathlib import Path

# Create MediaIntent objects directly
intent = mediallm.MediaIntent(
    action=mediallm.Action.convert,
    inputs=[Path("input.mp4")],
    video_codec="libx264",
    audio_codec="aac"
)

# Available actions
for action in mediallm.Action:
    print(f"- {action.value}")
```

---

## Configuration

Create a `.env` file or set environment variables:

```bash
MEDIALLM_MODEL=llama3.1:latest
MEDIALLM_OLLAMA_HOST=http://localhost:11434
MEDIALLM_OUTPUT_DIR=./outputs
MEDIALLM_DRY_RUN=false
```

---

## Contributing

We welcome contributions! See our [contributing guide](../../CONTRIBUTING.md) for:
- Development setup
- Testing guidelines  
- Code style requirements
- How to submit pull requests

---


<div align="center">

[Report Bug](https://github.com/iamarunbrahma/mediallm/issues) • [Request Feature](https://github.com/iamarunbrahma/mediallm/issues) • [Discussions](https://github.com/iamarunbrahma/mediallm/discussions)

</div>