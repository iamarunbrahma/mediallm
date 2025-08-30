#!/usr/bin/env python3
# Author: Arun Brahma

import argparse
import asyncio
import logging
import sys
from functools import partial
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
from fastmcp import FastMCP
from mediallm import MediaLLM
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Mount, Route

logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("mediallm-mcp")

# Global MediaLLM instance cache
_mediallm_instances: Dict[str, MediaLLM] = {}


def get_mediallm_instance(working_dir: Optional[str] = None) -> MediaLLM:
    """Get or create cached MediaLLM instance."""
    work_dir = Path(working_dir) if working_dir else Path.cwd()
    cache_key = str(work_dir)

    if cache_key not in _mediallm_instances:
        _mediallm_instances[cache_key] = MediaLLM(working_dir=work_dir)

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
) -> Any:
    """Generate FFmpeg commands from natural language request."""
    mediallm = get_mediallm_instance(workspace_dir)
    return await execute_sync(
        mediallm.generate_command,
        request=request,
        return_raw=return_raw,
        assume_yes=assume_yes,
    )


@mcp.tool()
async def scan_workspace(directory: Optional[str] = None) -> Dict[str, Any]:
    """Scan directory for media files."""
    mediallm = get_mediallm_instance(directory)
    return await execute_sync(mediallm.scan_workspace, directory=directory)


def create_starlette_app(transport, transport_type: str) -> Starlette:
    """Create Starlette app for HTTP/SSE transports."""
    if transport_type == "sse":

        async def handle_sse(request):
            """Handle SSE connections."""
            try:
                async with transport.connect_sse(
                    request.scope, request.receive, request._send
                ) as (read_stream, write_stream):
                    await mcp.server.run(
                        read_stream,
                        write_stream,
                        mcp.server.create_initialization_options(),
                    )
                return Response(status_code=200)
            except Exception as e:
                logger.error(f"SSE connection error: {e}")
                return Response(
                    content=f"SSE error: {str(e)}",
                    status_code=500,
                    headers={"content-type": "text/plain"},
                )

        routes = [
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Mount("/messages", app=transport.handle_post_message),
        ]

    elif transport_type == "http":

        async def handle_http(request):
            """Handle HTTP MCP requests."""
            session_id = request.headers.get("x-session-id")

            try:
                async with transport.get_session(session_id) as session:
                    await mcp.server.run(
                        session.read_stream,
                        session.write_stream,
                        mcp.server.create_initialization_options(),
                    )
            except Exception as e:
                logger.error(f"HTTP session error: {e}")
                return Response(
                    content=f"Session error: {str(e)}",
                    status_code=500,
                    headers={"content-type": "text/plain"},
                )

            return Response(status_code=200)

        async def health_check(_request):
            """Health check endpoint."""
            return Response(
                content="MediaLLM MCP Server is running",
                headers={"content-type": "text/plain"},
            )

        routes = [
            Route("/mcp", endpoint=handle_http, methods=["POST"]),
            Route("/health", endpoint=health_check, methods=["GET"]),
            Route("/", endpoint=health_check, methods=["GET"]),
        ]

    return Starlette(routes=routes)


def run_stdio():
    """Run server with STDIO transport."""
    # NO PRINT STATEMENTS - keep stdout clean for JSON-RPC
    mcp.run()


async def run_sse(host: str, port: int):
    """Run server with SSE transport."""
    from mcp.server.sse import SseServerTransport

    print("Starting SSE transport...")
    print(f"Connect to: http://{host}:{port}/sse")

    transport = SseServerTransport("/messages")
    app = create_starlette_app(transport, "sse")

    config = uvicorn.Config(
        app, host=host, port=port, log_level="info", access_log=False
    )
    uvicorn_server = uvicorn.Server(config)
    await uvicorn_server.serve()


async def run_http(host: str, port: int):
    """Run server with Streamable HTTP transport."""
    try:
        from mcp.server.http import StreamableHTTPSessionManager
    except ImportError as e:
        raise ImportError(f"StreamableHTTPSessionManager not available: {e}") from e

    print("Starting Streamable HTTP transport...")
    print(f"MCP endpoint: http://{host}:{port}/mcp")

    session_manager = StreamableHTTPSessionManager()
    app = create_starlette_app(session_manager, "http")

    config = uvicorn.Config(
        app, host=host, port=port, log_level="info", access_log=False
    )
    uvicorn_server = uvicorn.Server(config)
    await uvicorn_server.serve()


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


async def run_server(transport: str, host: str = "127.0.0.1", port: int = 3001):
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
            await run_http(host, port)
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
            asyncio.run(run_server(transport=transport, host=args.host, port=args.port))
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
