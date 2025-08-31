# MediaLLM MCP Server

MCP server that provides AI-powered media processing capabilities for FFmpeg operations through natural language commands.
MediaLLM converts natural language requests into precise FFmpeg commands and scans workspaces for media files.

**[Full Documentation](https://mediallm.arunbrahma.com/)**

## Installation

```bash
# Using pip
pip install mediallm-mcp

# Using uv (recommended)
uv add mediallm-mcp
```

## Usage

```bash
# STDIO (default)
mediallm-mcp

# Streamable HTTP
mediallm-mcp --http --port 3001

# SSE
mediallm-mcp --sse --port 3001
```

## Running in Docker

```bash
# Build image
cd packages/mediallm-mcp
docker build -t mediallm-mcp .

# Run with media directory mounted
docker run -it --rm \
  -v /path/to/media:/workspace \
  mediallm-mcp
```

## Accessing from Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mediallm-mcp": {
      "command": "uvx",
      "args": ["mediallm-mcp"],
      "env": {}
    }
  }
}
```

**Config file location:**
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

## Accessing from Claude Code

Add to `.mcp.json` in project root:

```json
{
  "mcpServers": {
    "mediallm-mcp": {
      "command": "uvx",
      "args": ["mediallm-mcp"],
      "env": {}
    }
  }
}
```

## Accessing from Cursor

[![Add to Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=mediallm-mcp&config=eyJjb21tYW5kIjogInV2eCIsICJhcmdzIjogWyJtZWRpYWxsbS1tY3AiXX0%3D)

Or manually add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "mediallm-mcp": {
      "command": "uvx",
      "args": ["mediallm-mcp"],
      "env": {}
    }
  }
}
```

## Environment Variables (Optional) for MCP configuration

- `MEDIALLM_WORKSPACE` - Specify media directory (default: current working directory)
- `MEDIALLM_MODEL` - Override LLM model (default: llama3.1:latest)
- `MEDIALLM_OLLAMA_HOST` - Ollama server URL (default: http://localhost:11434)
- `MEDIALLM_OUTPUT_DIR` - Output directory (default: current working directory)

## Debugging

Use MCP inspector to test the connection:

```bash
npx @modelcontextprotocol/inspector mediallm-mcp
```