# syntax=docker/dockerfile:1
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1
ENV FFMPEG_PATH="/usr/bin/ffmpeg"


EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os, urllib.request, sys; port=os.environ.get('PORT','8080'); sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=2).getcode()==200 else 1)"

ENV MCP_PATH="/mcp"
ENTRYPOINT ["sh", "-lc", "exec mediallm-mcp --http --host 0.0.0.0 --port ${PORT:-8080} --path ${MCP_PATH}"]