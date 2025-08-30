# MediaLLM MCP Server

MCP server that provides AI-powered media processing capabilities for FFmpeg operations through natural language commands.
MediaLLM converts natural language requests into precise FFmpeg commands and scans workspaces for media files.

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
      "command": "mediallm-mcp"
    }
  }
}
```

Config file location:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

## Accessing from Claude Code

Add to `.mcp.json` in project root:

```json
{
  "mcpServers": {
    "mediallm-mcp": {
      "command": "mediallm-mcp"
    }
  }
}
```

## Accessing from Cursor

[![Add to Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=mediallm-mcp&config=eyJjb21tYW5kIjogIm1lZGlhbGxtLW1jcCIsICJhcmdzIjogW119)

Or manually add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "mediallm-mcp": {
      "command": "mediallm-mcp"
    }
  }
}
```

## Debugging

Use MCP inspector to test the connection:

```bash
npx @modelcontextprotocol/inspector mediallm-mcp
```