#!/usr/bin/env python3
# Author: Arun Brahma
"""Tests for command injection prevention in CommandExecutor."""

from __future__ import annotations

import pytest

from mediallm.processing.command_executor import CommandExecutor


class TestCommandInjectionPrevention:
    """Test suite for command injection prevention."""

    @pytest.fixture
    def executor(self) -> CommandExecutor:
        """Create a CommandExecutor instance for testing."""
        return CommandExecutor()

    @pytest.mark.security
    @pytest.mark.parametrize(
        "malicious_input",
        [
            # Shell command injection via semicolon
            ["ffmpeg", "-i", "test.mp4", ";", "rm", "-rf", "/"],
            # Command substitution
            ["ffmpeg", "-i", "$(cat /etc/passwd)", "-o", "out.mp4"],
            # Pipe injection
            ["ffmpeg", "-i", "test.mp4", "|", "curl", "evil.com"],
            # Backtick command substitution
            ["ffmpeg", "-i", "`whoami`", "-o", "out.mp4"],
            # Variable expansion
            ["ffmpeg", "-i", "${HOME}/.ssh/id_rsa", "-o", "out.mp4"],
            # Background execution
            ["ffmpeg", "-i", "test.mp4", "&", "malicious_command"],
            # rm command injection
            ["ffmpeg", "-i", "test.mp4", "rm", "-rf", "/tmp"],
            # sudo injection
            ["ffmpeg", "-i", "test.mp4", "sudo", "rm", "-rf", "/"],
            # chmod injection
            ["ffmpeg", "-i", "test.mp4", "chmod", "777", "/etc/passwd"],
            # dd command injection (disk destruction)
            ["ffmpeg", "-i", "test.mp4", "dd", "if=/dev/zero", "of=/dev/sda"],
            # mkfs injection
            ["ffmpeg", "-i", "test.mp4", "mkfs", "/dev/sda"],
            # System call injection
            ["ffmpeg", "-i", "test.mp4", "system(rm -rf /)"],
            # Exec call injection
            ["ffmpeg", "-i", "test.mp4", "exec(/bin/sh)"],
            # Eval injection
            ["ffmpeg", "-i", "test.mp4", "eval(malicious_code)"],
            # Windows del command
            ["ffmpeg", "-i", "test.mp4", "del", "/s", "C:\\Windows"],
            # Windows format command
            ["ffmpeg", "-i", "test.mp4", "format", "C:"],
            # Output redirection to system file
            ["ffmpeg", "-i", "test.mp4", ">/etc/passwd"],
        ],
    )
    def test_rejects_shell_injection(
        self, executor: CommandExecutor, malicious_input: list[str]
    ) -> None:
        """Test that command executor rejects shell injection attempts."""
        assert not executor._is_command_secure(
            malicious_input
        ), f"Should reject: {' '.join(malicious_input)}"

    @pytest.mark.security
    @pytest.mark.parametrize(
        "safe_input",
        [
            # Basic video conversion
            ["ffmpeg", "-i", "input.mp4", "-c:v", "libx264", "output.mp4"],
            # Video with spaces in filename (valid)
            ["ffmpeg", "-i", "my video.mp4", "-vf", "scale=1920:1080", "out.mp4"],
            # Audio extraction
            ["ffmpeg", "-i", "video.mp4", "-q:a", "0", "-map", "a", "audio.mp3"],
            # Thumbnail extraction
            ["ffmpeg", "-i", "video.mp4", "-ss", "00:01:00", "-vframes", "1", "thumb.jpg"],
            # Video compression
            ["ffmpeg", "-i", "video.mp4", "-crf", "28", "-c:v", "libx265", "compressed.mp4"],
            # Video trimming
            ["ffmpeg", "-i", "video.mp4", "-ss", "00:00:10", "-to", "00:00:30", "trimmed.mp4"],
            # Format conversion
            ["ffmpeg", "-i", "video.avi", "-c:v", "copy", "-c:a", "copy", "video.mp4"],
            # Video with filter chain
            [
                "ffmpeg",
                "-i",
                "video.mp4",
                "-vf",
                "scale=1280:720,fps=30",
                "output.mp4",
            ],
            # File with "format" in the name (should NOT match "format" command)
            ["ffmpeg", "-i", "formatting_video.mp4", "-c:v", "libx264", "output.mp4"],
            # File with "rm" in the name (should NOT match "rm" command)
            ["ffmpeg", "-i", "arm_wrestling.mp4", "-c:v", "libx264", "output.mp4"],
            # File with "del" in the name (should NOT match "del" command)
            ["ffmpeg", "-i", "deleted_scenes.mp4", "-c:v", "libx264", "output.mp4"],
            # Hardware acceleration flag (valid ffmpeg)
            ["ffmpeg", "-hwaccel", "cuda", "-i", "video.mp4", "output.mp4"],
        ],
    )
    def test_allows_safe_commands(
        self, executor: CommandExecutor, safe_input: list[str]
    ) -> None:
        """Test that command executor allows safe FFmpeg commands."""
        assert executor._is_command_secure(
            safe_input
        ), f"Should allow: {' '.join(safe_input)}"

    @pytest.mark.security
    @pytest.mark.parametrize(
        "invalid_executable",
        [
            # Non-ffmpeg executables
            ["python", "-c", "print('hello')"],
            ["bash", "-c", "echo test"],
            ["sh", "-c", "ls"],
            ["curl", "http://example.com"],
            ["wget", "http://example.com"],
            # Empty command
            [],
            # None-like command
            [""],
        ],
    )
    def test_rejects_non_ffmpeg_executables(
        self, executor: CommandExecutor, invalid_executable: list[str]
    ) -> None:
        """Test that command executor only accepts ffmpeg/ffprobe executables."""
        assert not executor._is_command_secure(
            invalid_executable
        ), f"Should reject non-ffmpeg: {invalid_executable}"

    @pytest.mark.security
    def test_ffprobe_is_allowed(self, executor: CommandExecutor) -> None:
        """Test that ffprobe commands are allowed."""
        safe_ffprobe = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            "video.mp4",
        ]
        assert executor._is_command_secure(
            safe_ffprobe
        ), "ffprobe commands should be allowed"

    @pytest.mark.security
    def test_word_boundary_prevents_false_positives(
        self, executor: CommandExecutor
    ) -> None:
        """Test that word boundaries prevent false positives.

        For example, 'format' should not match 'formatting', and 'rm' should
        not match 'arm' or 'storm'.
        """
        # These should all be safe - they contain dangerous substrings but not
        # as standalone commands
        test_cases = [
            (["ffmpeg", "-i", "arm.mp4", "out.mp4"], "arm contains 'rm'"),
            (["ffmpeg", "-i", "storm.mp4", "out.mp4"], "storm contains 'rm'"),
            (["ffmpeg", "-i", "formatting.mp4", "out.mp4"], "formatting contains 'format'"),
            (["ffmpeg", "-i", "reformat.mp4", "out.mp4"], "reformat contains 'format'"),
            (["ffmpeg", "-i", "delete.mp4", "out.mp4"], "delete contains 'del'"),
            (["ffmpeg", "-i", "model.mp4", "out.mp4"], "model contains 'del'"),
            (["ffmpeg", "-i", "exec_summary.mp4", "out.mp4"], "exec_summary contains 'exec'"),
            (["ffmpeg", "-i", "systemd.mp4", "out.mp4"], "systemd contains 'system'"),
        ]

        for cmd, description in test_cases:
            assert executor._is_command_secure(cmd), (
                f"False positive for {description}: {' '.join(cmd)}"
            )

    @pytest.mark.security
    def test_case_insensitive_detection(self, executor: CommandExecutor) -> None:
        """Test that dangerous patterns are detected regardless of case."""
        # These should all be rejected
        test_cases = [
            ["ffmpeg", "-i", "test.mp4", "RM", "-RF", "/"],
            ["ffmpeg", "-i", "test.mp4", "Rm", "-rF", "/"],
            ["ffmpeg", "-i", "test.mp4", "SUDO", "rm"],
            ["ffmpeg", "-i", "test.mp4", "SuDo", "rm"],
            ["ffmpeg", "-i", "test.mp4", "CHMOD", "777", "/"],
            ["ffmpeg", "-i", "test.mp4", "DD", "if=/dev/zero"],
        ]

        for cmd in test_cases:
            assert not executor._is_command_secure(cmd), (
                f"Case-insensitive detection failed for: {' '.join(cmd)}"
            )


class TestCommandValidation:
    """Test suite for command validation in execution pipeline."""

    @pytest.fixture
    def executor(self) -> CommandExecutor:
        """Create a CommandExecutor instance for testing."""
        return CommandExecutor()

    @pytest.mark.security
    def test_validate_command_raises_on_insecure(self, executor: CommandExecutor) -> None:
        """Test that _validate_command_security raises ExecError for insecure commands."""
        from mediallm.utils.exceptions import ExecError

        malicious_cmd = ["ffmpeg", "-i", "test.mp4", ";", "rm", "-rf", "/"]

        with pytest.raises(ExecError) as exc_info:
            executor._validate_command_security(malicious_cmd)

        assert "security validation" in str(exc_info.value).lower()

    @pytest.mark.security
    def test_validate_command_passes_for_safe(self, executor: CommandExecutor) -> None:
        """Test that _validate_command_security passes for safe commands."""
        safe_cmd = ["ffmpeg", "-i", "input.mp4", "-c:v", "libx264", "output.mp4"]

        # Should not raise
        executor._validate_command_security(safe_cmd)
