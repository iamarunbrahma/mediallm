#!/usr/bin/env python3
"""
Test configuration and shared fixtures for MediaLLM tests.
Author: Arun Brahma
"""

import json
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Provide a Typer CliRunner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client for testing LLM interactions."""
    mock_client = Mock()

    # Mock list method to return available models
    mock_models_response = Mock()
    mock_models_response.models = [
        Mock(model="llama3.1:latest"),
        Mock(model="deepseek-r1:8b"),
        Mock(model="qwen:latest"),
    ]
    mock_client.list.return_value = mock_models_response

    # Mock chat method for LLM responses
    mock_client.chat.return_value = {
        "message": {
            "content": json.dumps(
                {
                    "action": "convert",
                    "inputs": ["test_video.mp4"],
                    "video_codec": "libx264",
                    "audio_codec": "aac",
                    "filters": [],
                }
            )
        }
    }

    return mock_client


@pytest.fixture
def mock_ollama_adapter(mock_ollama_client):
    """Mock OllamaAdapter with predefined responses."""
    mock_ollama = Mock()
    mock_ollama.Client.return_value = mock_ollama_client

    with patch.dict("sys.modules", {"ollama": mock_ollama}):
        from mediallm.core.llm import OllamaAdapter

        adapter = OllamaAdapter("http://localhost:11434", "llama3.1:latest")

        # Mock process_query method with predictable response
        adapter.process_query = Mock(
            return_value=json.dumps(
                {
                    "action": "convert",
                    "inputs": ["test_video.mp4"],
                    "video_codec": "libx264",
                    "audio_codec": "aac",
                    "filters": [],
                }
            )
        )

        yield adapter


@pytest.fixture
def mock_llm(mock_ollama_adapter):
    """Mock LLM instance with predictable responses."""
    from mediallm.core.llm import LLM

    llm = LLM(mock_ollama_adapter)

    # Mock parse_query method
    llm.parse_query = Mock(
        return_value={
            "action": "convert",
            "inputs": ["test_video.mp4"],
            "video_codec": "libx264",
            "audio_codec": "aac",
            "filters": [],
        }
    )

    return llm


@pytest.fixture
def sample_workspace():
    """Provide a sample workspace with mock media files."""
    return {
        "cwd": "/fake/workspace",
        "videos": ["test_video.mp4", "sample_movie.avi", "presentation.mkv"],
        "audios": ["song.mp3", "podcast.wav", "audio_clip.flac"],
        "images": ["photo.jpg", "screenshot.png", "diagram.webp"],
        "subtitle_files": ["movie_subtitles.srt", "episode_subs.vtt"],
        "info": [],
    }


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with sample media files for testing."""
    # Create media files
    video_dir = tmp_path / "videos"
    audio_dir = tmp_path / "audio"
    image_dir = tmp_path / "images"

    video_dir.mkdir()
    audio_dir.mkdir()
    image_dir.mkdir()

    # Create dummy files
    (video_dir / "test.mp4").write_text("fake video content")
    (video_dir / "sample.avi").write_text("fake avi content")
    (audio_dir / "song.mp3").write_text("fake audio content")
    (image_dir / "photo.jpg").write_text("fake image content")
    (tmp_path / "subtitle.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\nHello World")

    return tmp_path


@pytest.fixture
def mock_discover_media():
    """Mock the discover_media function to return predictable workspace."""
    with patch("mediallm.analysis.workspace_scanner.discover_media") as mock:
        mock.return_value = {
            "cwd": "/fake/workspace",
            "videos": ["test_video.mp4", "sample_movie.avi"],
            "audios": ["song.mp3", "podcast.wav"],
            "images": ["photo.jpg", "screenshot.png"],
            "subtitle_files": ["movie_subtitles.srt"],
            "info": [],
        }
        yield mock


@pytest.fixture
def mock_ffmpeg_commands():
    """Mock FFmpeg command construction."""
    return [
        ["ffmpeg", "-i", "input.mp4", "-c:v", "libx264", "-c:a", "aac", "output.mp4"],
        ["ffmpeg", "-i", "audio.wav", "-c:a", "mp3", "audio.mp3"],
    ]


@pytest.fixture
def mock_command_executor():
    """Mock command executor to avoid actual FFmpeg execution."""
    with patch("mediallm.processing.command_executor.run") as mock_run:
        mock_run.return_value = 0  # Success exit code
        with patch("mediallm.processing.command_executor.preview") as mock_preview:
            mock_preview.return_value = None
            with patch("mediallm.processing.command_executor.detect_overwrites") as mock_overwrites:
                mock_overwrites.return_value = False
                yield {
                    "run": mock_run,
                    "preview": mock_preview,
                    "detect_overwrites": mock_overwrites,
                }


@pytest.fixture
def mock_config():
    """Mock application configuration."""
    from mediallm.utils.config import AppConfig

    config = AppConfig()
    config.model_name = "llama3.1:latest"
    config.ollama_host = "http://localhost:11434"
    config.timeout_seconds = 60
    config.dry_run = False
    config.output_directory = None
    config.confirm_default = True

    return config


@pytest.fixture
def mock_media_intent():
    """Mock MediaIntent for testing."""
    from mediallm.utils.data_models import Action
    from mediallm.utils.data_models import MediaIntent

    return MediaIntent(
        action=Action.convert,
        inputs=["test_video.mp4"],
        video_codec="libx264",
        audio_codec="aac",
        filters=[],
    )


@pytest.fixture
def mock_command_plan():
    """Mock CommandPlan for testing."""
    from mediallm.utils.data_models import Action
    from mediallm.utils.data_models import CommandPlan
    from mediallm.utils.data_models import MediaTask

    task = MediaTask(
        action=Action.convert,
        inputs=[Path("test_video.mp4")],
        video_codec="libx264",
        audio_codec="aac",
        filters=[],
    )

    return CommandPlan(tasks=[task], summary="Convert test_video.mp4 to H.264/AAC format")


@pytest.fixture(autouse=True)
def mock_environment_validation():
    """Mock environment validation to avoid Python version checks in tests."""
    with patch("mediallm.main._validate_environment"):
        yield


@pytest.fixture
def sample_media_responses():
    """Provide sample LLM responses for different media operations."""
    return {
        "convert": {
            "action": "convert",
            "inputs": ["input.mp4"],
            "video_codec": "libx264",
            "audio_codec": "aac",
            "filters": [],
        },
        "resize": {
            "action": "resize",
            "inputs": ["image.jpg"],
            "width": 1920,
            "height": 1080,
            "filters": ["scale=1920:1080"],
        },
        "extract_audio": {
            "action": "extract",
            "inputs": ["video.mp4"],
            "output_format": "mp3",
            "audio_codec": "mp3",
            "filters": [],
        },
        "enhance": {
            "action": "enhance",
            "inputs": ["audio.mp3"],
            "filters": ["highpass=f=200", "lowpass=f=3000"],
            "audio_codec": "flac",
        },
    }


@pytest.fixture
def capture_logs(caplog):
    """Capture and provide access to log messages during tests."""
    return caplog


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests - fast, isolated, no external dependencies")
    config.addinivalue_line(
        "markers",
        "integration: Integration tests - use real file system, slower execution",
    )
    config.addinivalue_line("markers", "cli: CLI tests - test command-line interface functionality")
    config.addinivalue_line("markers", "slow: Slow running tests - performance or comprehensive tests")
    config.addinivalue_line("markers", "requires_ollama: Tests requiring Ollama server to be running")
    config.addinivalue_line("markers", "requires_ffmpeg: Tests requiring FFmpeg to be available")


# Mock constants for consistent testing
MOCK_VIDEO_FILES = ["test_video.mp4", "sample_movie.avi", "presentation.mkv"]
MOCK_AUDIO_FILES = ["song.mp3", "podcast.wav", "audio_clip.flac"]
MOCK_IMAGE_FILES = ["photo.jpg", "screenshot.png", "diagram.webp"]
MOCK_SUBTITLE_FILES = ["movie_subtitles.srt", "episode_subs.vtt"]
