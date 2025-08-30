FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install application
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

# Environment
ENV PYTHONUNBUFFERED=1
ENV FFMPEG_PATH="/usr/bin/ffmpeg"

# Main command
ENTRYPOINT ["mediallm-mcp"]