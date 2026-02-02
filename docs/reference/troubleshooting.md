# Troubleshooting

Common issues and solutions for MediaLLM.

## Installation Issues

### Command not found: mediallm

```bash
# Check if MediaLLM is installed
pip show mediallm

# If not installed
pip install mediallm

# Check PATH
echo $PATH
```

### ModuleNotFoundError: No module named 'mediallm'

```bash
# Reinstall MediaLLM
pip uninstall mediallm
pip install mediallm
```

## Ollama Issues

### Connection refused / Ollama not running

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if not running
ollama serve

# In another terminal, pull a model
ollama pull llama3.1:latest
```

### Model not found

```bash
# List available models
ollama list

# Pull required model
ollama pull llama3.1:latest
```

## FFmpeg Issues

### FFmpeg not found

```bash
# Check FFmpeg installation
ffmpeg -version

# Install FFmpeg
# macOS
brew install ffmpeg

# Linux  
sudo apt install ffmpeg
```

### Permission denied errors

```bash
# Check file permissions
ls -la video.mp4

# Fix permissions
chmod 644 video.mp4
```

## Runtime Issues

### "Cannot understand request" errors

This indicates the LLM couldn't parse your request:

- Be more specific: "convert video.mp4 to MP3" vs "convert video"
- Include format details: "convert to high quality MP4"
- Use `--dry-run` to test requests

### File not found errors

```bash
# Check current directory
ls -la

# Use absolute paths
mediallm "convert /full/path/to/video.mp4 to MP3"
```

### Commands fail during execution

```bash
# Preview commands first
mediallm --dry-run "your request"

# Check available disk space
df -h

# Check file isn't corrupted
ffmpeg -i video.mp4 -f null - 2>&1 | grep -i error
```

## Performance Issues

### Slow response times

- Use smaller models: `export MEDIALLM_MODEL="llama3.2:1b"`
- Increase timeout: `export MEDIALLM_TIMEOUT="120"`

### Large file processing

- Use `--dry-run` first to verify commands
- Process smaller segments for testing
- Ensure adequate disk space

## Known Limitations

Some operations may not work as expected depending on the LLM model:

### Operations with Limited Support

- **GIF creation**: May fail with "translation error" due to complex filter requirements
- **Batch operations**: "convert all X to Y" may produce malformed commands
- **Advanced filters**: Fade effects, volume adjustments, and crop/scale filters may not be applied
- **Format-specific conversions**: Some audio format conversions (e.g., MP3 to FLAC) may not output the expected format

### Workarounds

For advanced operations, try:
1. Be very specific: "convert video.mp4 to animated GIF output.gif"
2. Use simpler commands and chain them manually
3. Use `--dry-run` to preview and manually adjust commands
4. Consider using a more capable model like `llama3.1:8b` or larger

## Getting Help

If issues persist:

1. Check [GitHub Issues](https://github.com/iamarunbrahma/mediallm/issues)
2. Create a new issue with:
   - MediaLLM version: `mediallm --version`
   - Python version: `python --version`
   - Operating system
   - Complete error message
   - Command that failed