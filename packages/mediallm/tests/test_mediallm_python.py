#!/usr/bin/env python3
"""
Comprehensive unit tests for MediaLLM Python wrapper.
Author: Arun Brahma
"""

from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from mediallm import MediaLLM
from mediallm import discover_media
from mediallm.utils.data_models import Action
from mediallm.utils.data_models import CommandEntry
from mediallm.utils.data_models import CommandPlan
from mediallm.utils.data_models import MediaIntent
from mediallm.utils.exceptions import TranslationError


class TestMediaLLMInitialization:
    """Test MediaLLM class initialization and configuration."""

    def test_initialization_default_params(self, mock_discover_media):
        """Test MediaLLM initialization with default parameters."""
        mock_ollama = Mock()
        mock_client = Mock()
        mock_ollama.Client.return_value = mock_client

        # Mock the models list response
        mock_models_response = Mock()
        mock_models_response.models = [Mock(model="llama3.1:latest")]
        mock_client.list.return_value = mock_models_response

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            mediallm = MediaLLM()

            assert mediallm.working_dir == Path.cwd()
            assert mediallm.timeout == 60
            assert mediallm._workspace is None  # Lazy initialization
            mock_ollama.Client.assert_called_once_with(host="http://localhost:11434")

    def test_initialization_custom_params(self, sample_workspace):
        """Test MediaLLM initialization with custom parameters."""
        mock_ollama = Mock()
        mock_client = Mock()
        mock_ollama.Client.return_value = mock_client

        # Mock the models list response
        mock_models_response = Mock()
        mock_models_response.models = [Mock(model="qwen:latest")]
        mock_client.list.return_value = mock_models_response

        custom_working_dir = "/tmp/test_workspace"
        custom_host = "http://localhost:11435"
        custom_model = "qwen:latest"
        custom_timeout = 120

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            mediallm = MediaLLM(
                workspace=sample_workspace,
                ollama_host=custom_host,
                model_name=custom_model,
                timeout=custom_timeout,
                working_dir=custom_working_dir,
            )

            assert mediallm.working_dir == Path(custom_working_dir)
            assert mediallm.timeout == custom_timeout
            assert mediallm._workspace == sample_workspace  # Pre-set workspace
            mock_ollama.Client.assert_called_once_with(host=custom_host)

    def test_initialization_ollama_failure(self):
        """Test MediaLLM initialization failure when Ollama is not available."""
        mock_ollama = Mock()
        mock_ollama.Client.side_effect = Exception("Connection refused")

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            with pytest.raises(RuntimeError) as exc_info:
                MediaLLM()

            assert "Failed to initialize Ollama provider" in str(exc_info.value)
            assert "ollama serve" in str(exc_info.value)

    def test_workspace_lazy_initialization(self, mock_discover_media, sample_workspace):
        """Test workspace is lazily initialized when first accessed."""
        mock_discover_media.return_value = sample_workspace

        mock_ollama = Mock()
        mock_client = Mock()
        mock_ollama.Client.return_value = mock_client

        # Mock the models list response
        mock_models_response = Mock()
        mock_models_response.models = [Mock(model="llama3.1:latest")]
        mock_client.list.return_value = mock_models_response

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            with patch("mediallm.api.discover_media", return_value=sample_workspace) as patched_discover:
                mediallm = MediaLLM()

                # Workspace should not be initialized yet
                assert mediallm._workspace is None

                # Accessing workspace should trigger initialization
                workspace = mediallm.workspace
                assert workspace == sample_workspace
                patched_discover.assert_called_once()

    def test_properties_access(self):
        """Test property access for working_dir and timeout."""
        mock_ollama = Mock()
        mock_client = Mock()
        mock_ollama.Client.return_value = mock_client

        # Mock the models list response
        mock_models_response = Mock()
        mock_models_response.models = [Mock(model="llama3.1:latest")]
        mock_client.list.return_value = mock_models_response

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            working_dir = "/custom/path"
            timeout = 90
            mediallm = MediaLLM(working_dir=working_dir, timeout=timeout)

            assert mediallm.working_dir == Path(working_dir)
            assert mediallm.timeout == timeout


class TestMediaLLMCommandGeneration:
    """Test MediaLLM command generation functionality."""

    def test_generate_command_success(self, mock_discover_media, mock_ollama_adapter, sample_workspace):
        """Test successful command generation from natural language."""
        mock_discover_media.return_value = sample_workspace

        mock_ollama = Mock()
        mock_ollama.Client.return_value = mock_ollama_adapter.client

        # Create mock intent and plan
        mock_intent = MediaIntent(
            action=Action.convert,
            inputs=[Path("input.mp4")],
            video_codec="libx264",
            audio_codec="aac",
        )

        mock_plan = CommandPlan(
            summary="Convert video to MP3",
            entries=[
                CommandEntry(
                    input=Path("input.mp4"),
                    output=Path("output.mp3"),
                    args=["-c:a", "mp3"],
                )
            ],
        )

        expected_commands = [
            [
                "ffmpeg",
                "-y",
                "-i",
                "input.mp4",
                "-c:v",
                "libx264",
                "-c:a",
                "mp3",
                "output.mp3",
            ]
        ]

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            with patch("mediallm.api.discover_media", return_value=sample_workspace):
                with patch("mediallm.core.llm.OllamaAdapter", return_value=mock_ollama_adapter):
                    with patch("mediallm.core.llm.LLM") as mock_llm_class:
                        mock_llm = Mock()
                        mock_llm_class.return_value = mock_llm
                        mock_llm.parse_query.return_value = mock_intent

                        with patch("mediallm.api.dispatch_task", return_value=mock_plan) as mock_dispatch:
                            with patch(
                                "mediallm.api.construct_operations",
                                return_value=expected_commands,
                            ) as mock_construct:
                                mediallm = MediaLLM()
                                result = mediallm.generate_command("convert video to audio")

                                assert result == expected_commands
                                mock_dispatch.assert_called_once()
                                mock_construct.assert_called_once()

    def test_generate_command_return_raw(self, mock_discover_media, mock_ollama_adapter, sample_workspace):
        """Test generate_command with return_raw=True."""
        mock_discover_media.return_value = sample_workspace

        mock_ollama = Mock()
        mock_ollama.Client.return_value = mock_ollama_adapter.client

        mock_intent = MediaIntent(
            action=Action.convert,
            inputs=[Path("input.mp4")],
            video_codec="libx264",
            audio_codec="aac",
        )

        mock_plan = CommandPlan(
            summary="Convert video to MP3",
            entries=[
                CommandEntry(
                    input=Path("input.mp4"),
                    output=Path("output.mp3"),
                    args=["-c:a", "mp3"],
                )
            ],
        )

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            with patch("mediallm.api.discover_media", return_value=sample_workspace):
                with patch("mediallm.core.llm.OllamaAdapter", return_value=mock_ollama_adapter):
                    with patch("mediallm.core.llm.LLM") as mock_llm_class:
                        mock_llm = Mock()
                        mock_llm_class.return_value = mock_llm
                        mock_llm.parse_query.return_value = mock_intent

                        with patch("mediallm.api.dispatch_task", return_value=mock_plan) as mock_dispatch:
                            mediallm = MediaLLM()
                            result = mediallm.generate_command("convert video to audio", return_raw=True)

                            assert result == mock_plan
                            mock_dispatch.assert_called_once()

    def test_generate_command_empty_request(self):
        """Test generate_command with empty request."""
        with patch("mediallm.core.llm.OllamaAdapter"):
            mediallm = MediaLLM()

            with pytest.raises(ValueError, match="Request cannot be empty"):
                mediallm.generate_command("")

    def test_generate_command_too_long(self):
        """Test generate_command with request that's too long."""
        with patch("mediallm.core.llm.OllamaAdapter"):
            mediallm = MediaLLM()
            long_request = "a" * 10001  # Exceeds 10000 character limit

            with pytest.raises(ValueError, match="Request too long"):
                mediallm.generate_command(long_request)

    def test_generate_command_translation_error(self, mock_discover_media, mock_ollama_adapter, sample_workspace):
        """Test generate_command handles TranslationError."""
        mock_discover_media.return_value = sample_workspace

        mock_ollama = Mock()
        mock_ollama.Client.return_value = mock_ollama_adapter.client

        with (
            patch.dict("sys.modules", {"ollama": mock_ollama}),
            patch("mediallm.api.discover_media", return_value=sample_workspace),
            patch("mediallm.core.llm.OllamaAdapter", return_value=mock_ollama_adapter),
        ):
            # Create MediaLLM instance first
            mediallm = MediaLLM()
            # Then patch the _llm.parse_query method directly
            with (
                patch.object(
                    mediallm._llm,
                    "parse_query",
                    side_effect=TranslationError("Cannot parse query"),
                ),
                pytest.raises(TranslationError),
            ):
                mediallm.generate_command("invalid query")

    def test_generate_command_runtime_error(self, mock_discover_media, mock_ollama_adapter, sample_workspace):
        """Test generate_command handles unexpected errors."""
        mock_discover_media.return_value = sample_workspace

        mock_ollama = Mock()
        mock_ollama.Client.return_value = mock_ollama_adapter.client

        mock_intent = MediaIntent(
            action=Action.convert,
            inputs=[Path("input.mp4")],
            video_codec="libx264",
            audio_codec="aac",
        )

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            with patch("mediallm.api.discover_media", return_value=sample_workspace):
                with patch("mediallm.core.llm.OllamaAdapter", return_value=mock_ollama_adapter):
                    with patch("mediallm.core.llm.LLM") as mock_llm_class:
                        mock_llm = Mock()
                        mock_llm_class.return_value = mock_llm
                        mock_llm.parse_query.return_value = mock_intent

                        with patch(
                            "mediallm.api.dispatch_task",
                            side_effect=Exception("Dispatch failed"),
                        ):
                            mediallm = MediaLLM()
                            with pytest.raises(RuntimeError, match="Failed to generate commands"):
                                mediallm.generate_command("convert video")


class TestMediaLLMWorkspace:
    """Test MediaLLM workspace functionality."""

    def test_scan_workspace_default(self, sample_workspace):
        """Test scan_workspace with default directory."""
        mock_ollama = Mock()
        mock_client = Mock()
        mock_ollama.Client.return_value = mock_client

        # Mock the models list response
        mock_models_response = Mock()
        mock_models_response.models = [Mock(model="llama3.1:latest")]
        mock_client.list.return_value = mock_models_response

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            with patch("mediallm.api.discover_media", return_value=sample_workspace) as mock_discover:
                mediallm = MediaLLM()
                result = mediallm.scan_workspace()

                assert result == sample_workspace
                assert mediallm._workspace == sample_workspace
                mock_discover.assert_called_once()

    def test_scan_workspace_custom_directory(self, sample_workspace):
        """Test scan_workspace with custom directory."""
        mock_ollama = Mock()
        mock_client = Mock()
        mock_ollama.Client.return_value = mock_client

        # Mock the models list response
        mock_models_response = Mock()
        mock_models_response.models = [Mock(model="llama3.1:latest")]
        mock_client.list.return_value = mock_models_response

        custom_dir = "/custom/scan/path"

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            with patch("mediallm.api.discover_media", return_value=sample_workspace) as mock_discover:
                mediallm = MediaLLM()
                result = mediallm.scan_workspace(custom_dir)

                assert result == sample_workspace
                assert mediallm._workspace == sample_workspace
                mock_discover.assert_called_once_with(cwd=Path(custom_dir), show_summary=False)

    def test_available_files_property(self, sample_workspace):
        """Test available_files property."""
        mock_ollama = Mock()
        mock_client = Mock()
        mock_ollama.Client.return_value = mock_client

        # Mock the models list response
        mock_models_response = Mock()
        mock_models_response.models = [Mock(model="llama3.1:latest")]
        mock_client.list.return_value = mock_models_response

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            mediallm = MediaLLM(workspace=sample_workspace)
            files = mediallm.available_files

            assert "videos" in files
            assert "audios" in files
            assert "images" in files
            assert "subtitles" in files
            assert files["videos"] == sample_workspace["videos"]
            assert files["audios"] == sample_workspace["audios"]
            assert files["images"] == sample_workspace["images"]
            assert files["subtitles"] == sample_workspace["subtitle_files"]


class TestDiscoverMedia:
    """Test discover_media function."""

    def test_discover_media_default_params(self, sample_workspace):
        """Test discover_media with default parameters."""
        with patch(
            "mediallm.analysis.workspace_scanner._discovery.discover_media",
            return_value=sample_workspace,
        ) as mock_discover:
            result = discover_media()

            assert result == sample_workspace
            mock_discover.assert_called_once_with(None, True)

    def test_discover_media_custom_params(self, sample_workspace):
        """Test discover_media with custom parameters."""
        custom_path = Path("/custom/path")

        with patch(
            "mediallm.analysis.workspace_scanner._discovery.discover_media",
            return_value=sample_workspace,
        ) as mock_discover:
            result = discover_media(cwd=custom_path, show_summary=False)

            assert result == sample_workspace
            mock_discover.assert_called_once_with(custom_path, False)

    def test_discover_media_empty_result(self):
        """Test discover_media with empty result."""
        empty_workspace = {
            "cwd": "/empty/workspace",
            "videos": [],
            "audios": [],
            "images": [],
            "subtitle_files": [],
            "info": [],
        }

        with patch(
            "mediallm.analysis.workspace_scanner._discovery.discover_media",
            return_value=empty_workspace,
        ):
            result = discover_media()

            assert result == empty_workspace
            assert result["videos"] == []
            assert result["audios"] == []


class TestErrorHandling:
    """Test error handling across MediaLLM wrapper."""

    def test_translation_error_propagation(self, mock_discover_media, mock_ollama_adapter, sample_workspace):
        """Test TranslationError is properly propagated."""
        mock_discover_media.return_value = sample_workspace

        mock_ollama = Mock()
        mock_ollama.Client.return_value = mock_ollama_adapter.client

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            with patch("mediallm.api.discover_media", return_value=sample_workspace):
                with patch("mediallm.core.llm.OllamaAdapter", return_value=mock_ollama_adapter):
                    # Create MediaLLM instance first
                    mediallm = MediaLLM()
                    # Then patch the _llm.parse_query method directly
                    with (
                        patch.object(
                            mediallm._llm,
                            "parse_query",
                            side_effect=TranslationError("Cannot understand request"),
                        ),
                        pytest.raises(TranslationError, match="Cannot understand request"),
                    ):
                        mediallm.generate_command("invalid nonsense request")

    def test_runtime_error_initialization(self):
        """Test RuntimeError during initialization."""
        mock_ollama = Mock()
        mock_ollama.Client.side_effect = RuntimeError("Ollama not running")

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            with pytest.raises(RuntimeError, match="Failed to initialize Ollama provider"):
                MediaLLM()

    def test_value_error_validation(self):
        """Test ValueError for invalid inputs."""
        with patch("mediallm.core.llm.OllamaAdapter"):
            mediallm = MediaLLM()

            # Test empty request
            with pytest.raises(ValueError, match="Request cannot be empty"):
                mediallm.generate_command("")

            # Test too long request
            long_request = "x" * 10001
            with pytest.raises(ValueError, match="Request too long"):
                mediallm.generate_command(long_request)

    def test_exception_chaining(self, mock_discover_media, mock_ollama_adapter, sample_workspace):
        """Test proper exception chaining."""
        mock_discover_media.return_value = sample_workspace

        mock_ollama = Mock()
        mock_ollama.Client.return_value = mock_ollama_adapter.client

        mock_intent = MediaIntent(
            action=Action.convert,
            inputs=[Path("input.mp4")],
            video_codec="libx264",
            audio_codec="aac",
        )

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            with patch("mediallm.api.discover_media", return_value=sample_workspace):
                with patch("mediallm.core.llm.OllamaAdapter", return_value=mock_ollama_adapter):
                    with patch("mediallm.core.llm.LLM") as mock_llm_class:
                        mock_llm = Mock()
                        mock_llm_class.return_value = mock_llm
                        mock_llm.parse_query.return_value = mock_intent

                        original_error = Exception("Original error message")
                        with patch("mediallm.api.dispatch_task", side_effect=original_error):
                            mediallm = MediaLLM()

                            with pytest.raises(RuntimeError) as exc_info:
                                mediallm.generate_command("convert video")

                            # Check that original exception is chained
                            assert exc_info.value.__cause__ == original_error


@pytest.mark.parametrize(
    ("action", "expected_codec"),
    [
        (Action.convert, "libx264"),
        (Action.compress, "libx265"),
        (Action.extract_audio, None),
    ],
)
def test_media_intent_creation_parameterized(action, expected_codec):
    """Test MediaIntent creation with different actions."""
    intent = MediaIntent(
        action=action,
        inputs=[Path("test.mp4")],
        video_codec=expected_codec,
        audio_codec="aac",
    )

    assert intent.action == action
    assert intent.video_codec == expected_codec
    assert len(intent.inputs) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
