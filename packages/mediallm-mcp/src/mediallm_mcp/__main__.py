#!/usr/bin/env python3
# Author: Arun Brahma

import argparse
import asyncio
import logging
import os
import sys
from functools import partial
from pathlib import Path
from typing import Any, Dict, Optional

from fastmcp import FastMCP
from mediallm import MediaLLM

logger = logging.getLogger(__name__)

mcp = FastMCP("mediallm-mcp")

_mediallm_instances: Dict[str, MediaLLM] = {}




def get_mediallm_instance(working_dir: Optional[str] = None) -> MediaLLM:
    """Get or create cached MediaLLM instance."""
    working_dir = Path(working_dir) if working_dir else Path.cwd()
    ollama_host = os.environ.get("MEDIALLM_OLLAMA_HOST", "http://localhost:11434")
    model_name = os.environ.get("MEDIALLM_MODEL", "llama3.1:latest")
    timeout = int(os.environ.get("MEDIALLM_TIMEOUT", "60"))

    cache_key = f"{working_dir}::{ollama_host}::{model_name}::{timeout}"

    if cache_key not in _mediallm_instances:
        _mediallm_instances[cache_key] = MediaLLM(
            working_dir=working_dir,
            ollama_host=ollama_host,
            model_name=model_name,
            timeout=timeout,
        )

    return _mediallm_instances[cache_key]


async def execute_sync(func, *args, **kwargs):
    """Execute synchronous function in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


@mcp.tool()
async def generate_command(
    request: str,
    return_raw: bool = False,
    assume_yes: bool = True,
    workspace_dir: Optional[str] = None,
    output_dir: Optional[str] = None
) -> Any:
    """Convert natural language to FFmpeg commands."""
    mediallm = get_mediallm_instance(workspace_dir)
    output_dir = os.environ.get("MEDIALLM_OUTPUT_DIR", "").strip()
    output_dir = Path(output_dir).expanduser() if output_dir else None
    

    return await execute_sync(
        mediallm.generate_command,
        request=request,
        return_raw=return_raw,
        assume_yes=assume_yes,
        output_dir=output_dir,
    )


@mcp.tool()
async def scan_workspace(directory: Optional[str] = None) -> Dict[str, Any]:
    """Discover media files under the given directory."""
    mediallm = get_mediallm_instance(directory)
    return await execute_sync(mediallm.scan_workspace, directory=directory)


# Removed legacy Starlette app builder; FastMCP manages HTTP/SSE.


def run_stdio():
    """Run server with STDIO transport."""
    mcp.run()


async def run_sse(host: str, port: int):
    """Run server with SSE transport."""
    print("Starting SSE transport...")
    print(f"Connect to: http://{host}:{port}/sse")
    # FastMCP manages the SSE server lifecycle
    mcp.run(transport="sse", host=host, port=port)


async def run_http(host: str, port: int, path: str):
    """Run server with Streamable HTTP transport."""
    print("Starting Streamable HTTP transport...")
    print(f"MCP endpoint: http://{host}:{port}{path}")
    # FastMCP manages the HTTP server lifecycle; expose MCP at /mcp
    mcp.run(transport="http", host=host, port=port, path=path)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MediaLLM MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # STDIO transport (default)
  %(prog)s --sse --port 3001        # SSE transport on port 3001
  %(prog)s --http --host 0.0.0.0    # HTTP transport on all interfaces
        """,
    )

    transport_group = parser.add_mutually_exclusive_group()
    transport_group.add_argument(
        "--http", action="store_true", help="Use Streamable HTTP transport"
    )
    transport_group.add_argument("--sse", action="store_true", help="Use SSE transport")

    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind to (default: %(default)s)"
    )
    parser.add_argument(
        "--port", type=int, default=3001, help="Port to bind to (default: %(default)s)"
    )
    parser.add_argument(
        "--path", default="/mcp", help="HTTP endpoint path (default: %(default)s)"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    return parser.parse_args()


def setup_logging(debug: bool, transport: str = "stdio") -> None:
    """Configure logging based on transport."""
    if transport == "stdio":
        # For STDIO: Only log to stderr, never stdout
        logging.basicConfig(
            stream=sys.stderr,
            level=logging.DEBUG if debug else logging.WARNING,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    else:
        # For HTTP/SSE: Can use normal logging
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


async def run_server(
    transport: str, host: str = "127.0.0.1", port: int = 3001, path: str = "/mcp"
):
    """Run server with specified transport."""
    # Only show banner for non-STDIO transports
    if transport != "stdio":
        print("MediaLLM MCP Server")
        print(f"Transport: {transport.upper()}")

    try:
        if transport == "stdio":
            run_stdio()  # Synchronous call for FastMCP
        elif transport == "sse":
            await run_sse(host, port)
        elif transport == "http":
            await run_http(host, port, path)
        else:
            raise ValueError(f"Unknown transport: {transport}")
    except Exception as e:
        logger.error(f"Transport {transport} failed: {e}")
        raise


def main() -> None:
    """Main entry point with improved error handling."""
    args = parse_args()

    # Determine transport
    transport = "stdio"  # Default
    if args.http:
        transport = "http"
    elif args.sse:
        transport = "sse"

    # Setup logging early with transport-aware configuration
    setup_logging(args.debug, transport)

    try:
        if transport == "stdio":
            # Direct synchronous call for FastMCP STDIO
            run_stdio()
        else:
            # Use asyncio for HTTP/SSE transports
            asyncio.run(
                run_server(
                    transport=transport,
                    host=args.host,
                    port=args.port,
                    path=args.path,
                )
            )
    except KeyboardInterrupt:
        if transport != "stdio":
            print("\n\nMediaLLM MCP Server stopped by user")
        exit(0)
    except Exception as e:
        error_msg = f"Server startup failed: {e}"
        if args.debug:
            logger.error(error_msg)
            logger.exception("Full traceback:")
        else:
            # For stdio, send error to stderr; for others, stdout is ok
            if transport == "stdio":
                print(error_msg, file=sys.stderr)
            else:
                print(error_msg)
        exit(1)


def cli_main() -> None:
    """CLI entry point."""
    main()


if __name__ == "__main__":
    cli_main()
