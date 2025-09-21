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

ENTRYPOINT ["sh", "-lc", "exec mediallm-mcp --http --host 0.0.0.0 --port ${PORT:-8080} --path /mcp"]