# Examples

Real-world usage scenarios for MediaLLM across different use cases.

!!! note "About These Examples"
    The code examples below demonstrate MediaLLM's capabilities in various scenarios. While the core MediaLLM API usage is accurate, complex integration examples (Flask, Discord, file watchers) are illustrative and may require additional setup, error handling, and testing in your specific environment.

## Content Creation Workflows

### Social Media Content Pipeline

Creating content for multiple platforms from a single source video:

```bash
# Start with a raw video file
ls
# raw_interview.mp4

# Extract highlight clips
mediallm "extract 30 seconds from raw_interview.mp4 starting at 2:15"
mediallm "extract 15 seconds from raw_interview.mp4 starting at 5:30"

# Create platform-specific versions
mediallm "resize highlight1.mp4 to 1080x1080 square for Instagram"
mediallm "resize highlight2.mp4 to 9:16 portrait for TikTok"
mediallm "resize highlight1.mp4 to 1920x1080 for YouTube"

# Generate thumbnails
mediallm "extract thumbnail from highlight1.mp4 at 5 seconds"
mediallm "extract thumbnail from highlight2.mp4 at 3 seconds"

# Create audio versions for podcasts
mediallm "extract audio from raw_interview.mp4 as high quality MP3"
```

### YouTube Content Creation

Complete workflow from raw footage to published content:

```python
import mediallm
import subprocess
from pathlib import Path

# Initialize MediaLLM
ml = mediallm.MediaLLM()

# Scan for raw footage
workspace = ml.scan_workspace("./raw_footage")
print(f"Found {len(workspace['videos'])} raw video files")

# Process each video
for video in workspace['videos']:
 video_path = Path(video)
 base_name = video_path.stem
 
 # Extract audio for editing
 audio_cmd = ml.generate_command(
 f"extract audio from {video} as high quality WAV for editing"
 )
 
 # Create preview thumbnail
 thumb_cmd = ml.generate_command(
 f"extract thumbnail from {video} at 10 seconds as {base_name}_thumb.jpg"
 )
 
 # Generate compressed version for upload
 upload_cmd = ml.generate_command(
 f"compress {video} to high quality MP4 suitable for YouTube upload"
 )
 
 # Execute commands
 for cmd_list in [audio_cmd, thumb_cmd, upload_cmd]:
 for cmd in cmd_list:
 subprocess.run(cmd, check=True)
 
 print(f"Processed {video}")
```

## Media Archive Organization

### Converting Legacy Formats

Batch convert old video formats to modern standards:

```bash
# Convert all AVI files to MP4
mediallm "convert all AVI files to MP4 with high quality settings"

# Modernize audio files
mediallm "convert all WAV files to high quality AAC"

# Standardize image formats
mediallm "convert all BMP images to PNG format"

# Extract metadata before conversion
for file in *.avi; do
 mediallm "extract thumbnail from $file at 10 seconds as ${file%.avi}_preview.jpg"
done
```

### Family Video Archive

Organizing and preserving family memories:

```python
import subprocess
import mediallm
from pathlib import Path
import os

ml = mediallm.MediaLLM()

# Organize by year based on filename patterns
archive_dir = Path("family_archive")
archive_dir.mkdir(exist_ok=True)

# Scan for all videos
workspace = ml.scan_workspace()

for video in workspace['videos']:
 video_path = Path(video)
 
 # Extract year from filename (assuming YYYY format exists)
 year = None
 for part in video_path.stem.split('_'):
 if part.isdigit() and len(part) == 4 and part.startswith('20'):
 year = part
 break
 
 if year:
 year_dir = archive_dir / year
 year_dir.mkdir(exist_ok=True)
 
 # Convert to standardized format
 output_name = f"{year_dir}/{video_path.stem}_archived.mp4"
 
 commands = ml.generate_command(
 f"convert {video} to MP4 with good compression and save as {output_name}"
 )
 
 # Execute conversion
 for cmd in commands:
 subprocess.run(cmd, check=True)
 
 print(f"Success: Archived {video} to {year}")
```

## Educational Content

### Lecture Processing

Batch process recorded lectures for online distribution:

```bash
# Directory with lecture recordings
cd /path/to/lectures

# Extract audio for podcast feed
mediallm "extract audio from all MP4 files as high quality MP3 for podcasts"

# Create quick preview clips (first 2 minutes)
for video in *.mp4; do
 mediallm "extract first 2 minutes from $video as ${video%.mp4}_preview.mp4"
done

# Generate closed captions (if subtitle files exist)
mediallm "burn subtitles from all SRT files into corresponding videos"

# Create mobile-friendly versions
mediallm "convert all lecture videos to 720p MP4 optimized for mobile viewing"
```

### Training Material Creation

Create training videos with consistent formatting:

```python
import mediallm

ml = mediallm.MediaLLM()

# Training video specifications
specs = {
 'intro_duration': 10,
 'outro_duration': 5,
 'resolution': '1280x720',
 'logo_overlay': 'company_logo.png'
}

# Process training modules
modules = ['module1.mp4', 'module2.mp4', 'module3.mp4']

for i, module in enumerate(modules, 1):
 # Add intro/outro
 intro_cmd = ml.generate_command(
 f"extract first {specs['intro_duration']} seconds from intro_template.mp4"
 )
 
 outro_cmd = ml.generate_command(
 f"extract last {specs['outro_duration']} seconds from outro_template.mp4"
 )
 
 # Resize to standard resolution
 resize_cmd = ml.generate_command(
 f"resize {module} to {specs['resolution']} with high quality"
 )
 
 # Add company logo overlay
 overlay_cmd = ml.generate_command(
 f"overlay {specs['logo_overlay']} on top-right of resized_{module}"
 )
 
 print(f"Processing Module {i}: {module}")
```

## Automation Scripts

### Watch Folder Processing

Automatically process new files as they appear:

```python
import time
import subprocess
import mediallm
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MediaProcessor(FileSystemEventHandler):
 def __init__(self):
 self.ml = mediallm.MediaLLM()
 
 def on_created(self, event):
 if event.is_directory:
 return
 
 file_path = Path(event.src_path)
 
 # Only process video files
 if file_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
 self.process_video(file_path)
 
 def process_video(self, video_path):
 print(f"New video detected: {video_path}")
 
 try:
 # Create web-optimized version
 web_cmd = self.ml.generate_command(
 f"convert {video_path} to MP4 optimized for web streaming"
 )
 
 # Extract thumbnail
 thumb_cmd = self.ml.generate_command(
 f"extract thumbnail from {video_path} at 10 seconds"
 )
 
 # Extract audio version
 audio_cmd = self.ml.generate_command(
 f"extract audio from {video_path} as MP3"
 )
 
 # Execute all commands
 for cmd_set in [web_cmd, thumb_cmd, audio_cmd]:
 for cmd in cmd_set:
 subprocess.run(cmd, check=True)
 
 print(f"Success: Successfully processed {video_path.name}")
 
 except Exception as e:
 print(f"Error: Error processing {video_path.name}: {e}")

# Set up file watcher
if __name__ == "__main__":
 watch_directory = "/path/to/watch/folder"
 event_handler = MediaProcessor()
 observer = Observer()
 observer.schedule(event_handler, watch_directory, recursive=True)
 observer.start()
 
 print(f"Watching {watch_directory} for new videos...")
 
 try:
 while True:
 time.sleep(1)
 except KeyboardInterrupt:
 observer.stop()
 observer.join()
```

### Batch Thumbnail Generator

Generate thumbnails for video libraries:

```bash
#!/bin/bash
# batch_thumbnails.sh

# Configuration
THUMB_SIZE="320x240"
THUMB_TIME="30" # seconds into video
OUTPUT_DIR="thumbnails"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Process all videos
for video in *.{mp4,avi,mov,mkv}; do
 [ -e "$video" ] || continue # Skip if no files match
 
 basename=$(basename "$video" | cut -d. -f1)
 thumbnail="$OUTPUT_DIR/${basename}_thumb.jpg"
 
 echo "Generating thumbnail for: $video"
 mediallm "extract frame from $video at $THUMB_TIME seconds and resize to $THUMB_SIZE as $thumbnail"
done

echo "Success: Thumbnail generation complete"
echo "Generated thumbnails in: $OUTPUT_DIR"
```

## Integration Examples

### Web Application Integration

Using MediaLLM in a Flask web application:

```python
from flask import Flask, request, jsonify, send_file
import subprocess
import mediallm
import tempfile
import os
from pathlib import Path

app = Flask(__name__)
ml = mediallm.MediaLLM()

@app.route('/api/convert', methods=['POST'])
def convert_media():
 try:
 # Get uploaded file and conversion request
 file = request.files['media_file']
 conversion_request = request.json.get('request', '')
 
 # Save uploaded file
 with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
 file.save(temp_file.name)
 input_path = temp_file.name
 
 # Generate conversion commands
 commands = ml.generate_command(f"{conversion_request} {input_path}")
 
 # Execute conversion (simplified - add proper error handling)
 for cmd in commands:
 subprocess.run(cmd, check=True)
 
 # Return success response
 return jsonify({'status': 'success', 'message': 'Conversion completed'})
 
 except Exception as e:
 return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/preview', methods=['POST'])
def preview_command():
 try:
 request_text = request.json.get('request', '')
 
 # Generate command without executing
 commands = ml.generate_command(request_text, assume_yes=True)
 
 # Return commands as preview
 return jsonify({
 'commands': [' '.join(cmd) for cmd in commands],
 'status': 'preview'
 })
 
 except Exception as e:
 return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
 app.run(debug=True)
```

### Discord Bot Integration

Create a Discord bot that processes media using MediaLLM:

```python
import discord
from discord.ext import commands
import subprocess
import mediallm
import aiofiles
import tempfile
from pathlib import Path

bot = commands.Bot(command_prefix='!')
ml = mediallm.MediaLLM()

@bot.command()
async def convert(ctx, *, request_text):
 """Convert attached media file based on natural language request."""
 
 if not ctx.message.attachments:
 await ctx.send("Please attach a media file to convert.")
 return
 
 attachment = ctx.message.attachments[0]
 
 # Check if it's a media file
 if not any(attachment.filename.lower().endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.mp3', '.wav']):
 await ctx.send("Please attach a valid media file (video or audio).")
 return
 
 try:
 await ctx.send(f"Processing: {request_text}")
 
 # Download attachment
 with tempfile.NamedTemporaryFile(delete=False, suffix=Path(attachment.filename).suffix) as temp_file:
 await attachment.save(temp_file.name)
 
 # Generate and execute commands
 commands = ml.generate_command(f"{request_text} {temp_file.name}")
 
 for cmd in commands:
 subprocess.run(cmd, check=True)
 
 await ctx.send("Success: Conversion completed! Check your server for the output file.")
 
 except Exception as e:
 await ctx.send(f"Error processing file: {str(e)}")

@bot.command()
async def preview(ctx, *, request_text):
 """Preview the FFmpeg command that would be generated."""
 
 try:
 commands = ml.generate_command(request_text, assume_yes=True)
 
 preview_text = "**Generated Commands:**\n"
 for cmd in commands:
 preview_text += f"```bash\n{' '.join(cmd)}\n```"
 
 await ctx.send(preview_text)
 
 except Exception as e:
 await ctx.send(f"Error generating preview: {str(e)}")

bot.run('YOUR_BOT_TOKEN')
```

## Performance Optimization

### Parallel Processing

Process multiple files concurrently:

```python
import mediallm
import concurrent.futures
import subprocess
from pathlib import Path

def process_video(video_path, request_template):
 """Process a single video file."""
 ml = mediallm.MediaLLM()
 
 try:
 request = request_template.format(video=video_path)
 commands = ml.generate_command(request)
 
 for cmd in commands:
 subprocess.run(cmd, check=True)
 
 return f"Success: {video_path}"
 
 except Exception as e:
 return f"Error: {video_path}: {e}"

# Process multiple videos in parallel
video_files = list(Path('.').glob('*.mp4'))
request_template = "convert {video} to 720p MP4 with good compression"

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
 futures = [
 executor.submit(process_video, video, request_template)
 for video in video_files
 ]
 
 for future in concurrent.futures.as_completed(futures):
 result = future.result()
 print(result)
```

## Next Steps

- **[Python API](../user-guide/python-api.md)** - Complete API reference
- **[Troubleshooting](../reference/troubleshooting.md)** - Common issues and solutions