# MCP Server

MediaLLM MCP Server integrates MediaLLM with AI agents using the Model Context Protocol.

## Installation

```bash
pip install mediallm-mcp
```

## Basic Usage

```bash
# STDIO transport (default)
mediallm-mcp

# HTTP transport
mediallm-mcp --http --port 3001

# SSE transport  
mediallm-mcp --sse --port 3002
```

## AI Client Integration

### Claude Desktop

Add to your `claude_desktop_config.json`:

=== "macOS"
    ```json
    // ~/Library/Application Support/Claude/claude_desktop_config.json
    {
      "mcpServers": {
        "mediallm-mcp": {
          "command": "mediallm-mcp"
        }
      }
    }
    ```

=== "Windows"
    ```json
    // %APPDATA%\Claude\claude_desktop_config.json
    {
      "mcpServers": {
        "mediallm-mcp": {
          "command": "mediallm-mcp"
        }
      }
    }
    ```

### Claude Code

Add to `.mcp.json` in your project root:

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

Create `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "mediallm-mcp": {
      "command": "mediallm-mcp"
    }
  }
}
```

## Available Tools

The MCP server exposes these tools to AI agents:

### generate_command

Generate FFmpeg commands from natural language.

**Parameters:**
- `request` (string): Natural language description
- `return_raw` (boolean): Return raw plan vs executable commands
- `assume_yes` (boolean): Skip confirmation prompts
- `workspace_dir` (string): Working directory path

### scan_workspace

Scan directory for media files.

**Parameters:**
- `directory` (string): Directory path to scan

## Example Usage in AI Agents

Once configured, AI agents can use MediaLLM tools:

```
User: Convert video.mp4 to audio format

AI Agent: I'll help you convert that video to audio format.

[Agent calls generate_command tool with request: "convert video.mp4 to MP3"]

The command to extract audio is:
ffmpeg -i video.mp4 -q:a 0 -map a video.mp3
```

## Transport Modes

| Transport | Use Case |
|-----------|----------|
| STDIO | Claude Desktop, Claude Code |
| HTTP | Web integrations, REST APIs |
| SSE | Real-time web applications |

## Docker Usage

The MCP server includes a Dockerfile for containerized deployments:

```bash
# Build image
cd packages/mediallm-mcp
docker build -t mediallm-mcp .

# Run container
docker run -v /path/to/media:/workspace mediallm-mcp
```

## Next Steps

- [Python API →](python-api.md) - Direct API usage
- [CLI Usage →](cli.md) - Command-line interface