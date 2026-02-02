#!/usr/bin/env python3
# Author: Arun Brahma
"""Tests for path traversal prevention in MediaLLM."""

from __future__ import annotations

from pathlib import Path

import pytest

from mediallm.processing.media_file_handler import MediaFileHandler
from mediallm.processing.media_file_handler import expand_globs
from mediallm.processing.media_file_handler import is_safe_path
from mediallm.safety.access_control import AccessController


class TestPathTraversalPrevention:
    """Test suite for path traversal attack prevention."""

    @pytest.mark.security
    @pytest.mark.parametrize(
        "malicious_path",
        [
            # Unix path traversal
            "../../../etc/passwd",
            "../../etc/shadow",
            "/etc/passwd",
            "/proc/self/environ",
            "/sys/kernel/debug",
            "/dev/sda",
            "/boot/vmlinuz",
            # Windows path traversal
            "..\\..\\windows\\system32\\config\\sam",
            "C:\\Windows\\System32\\config\\SAM",
            "..\\..\\..\\windows\\system32",
            # Mixed traversal
            "input/../../../etc/passwd",
            "videos/../../../../../../etc/shadow",
            # Encoded traversal (these should be literal strings)
            "../%2e%2e/etc/passwd",
            # Double encoding
            "....//....//etc/passwd",
            # Triple dots (unusual but should be caught)
            ".../etc/passwd",
            # Null byte injection (should be sanitized)
            "../etc/passwd\x00.mp4",
            # Home directory access
            "~/.ssh/id_rsa",
            "~/.aws/credentials",
            "~/.config/sensitive",
            # Root paths
            "/",
            "\\",
            "C:\\",
            "C:/",
        ],
    )
    def test_rejects_path_traversal(self, malicious_path: str, tmp_path: Path) -> None:
        """Test that path traversal attempts are rejected."""
        allowed = [tmp_path]
        assert not is_safe_path(
            malicious_path, allowed
        ), f"Should reject path traversal: {malicious_path}"

    @pytest.mark.security
    @pytest.mark.parametrize(
        "safe_path",
        [
            "video.mp4",
            "videos/video.mp4",
            "my_project/media/video.mp4",
            "video with spaces.mp4",
            "video-with-dashes.mp4",
            "video_with_underscores.mp4",
            "VIDEO.MP4",
            "video.final.mp4",
        ],
    )
    def test_allows_safe_paths(self, safe_path: str, tmp_path: Path) -> None:
        """Test that legitimate paths within allowed directories are accepted."""
        # Create the actual file/directory structure
        full_path = tmp_path / safe_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.touch()

        allowed = [tmp_path]
        assert is_safe_path(
            full_path, allowed
        ), f"Should allow safe path: {safe_path}"

    @pytest.mark.security
    def test_path_must_be_within_allowed_directories(self, tmp_path: Path) -> None:
        """Test that paths outside allowed directories are rejected."""
        # Create a file in tmp_path
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()
        allowed_file = allowed_dir / "video.mp4"
        allowed_file.touch()

        # Create a file outside allowed directory
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        outside_file = outside_dir / "video.mp4"
        outside_file.touch()

        allowed = [allowed_dir]

        # File inside allowed dir should be accepted
        assert is_safe_path(allowed_file, allowed), "File in allowed dir should be accepted"

        # File outside allowed dir should be rejected
        assert not is_safe_path(
            outside_file, allowed
        ), "File outside allowed dir should be rejected"

    @pytest.mark.security
    def test_symlink_resolution(self, tmp_path: Path) -> None:
        """Test that symlinks pointing outside allowed dirs are rejected."""
        # Create allowed directory with a file
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        # Create a directory outside allowed
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        outside_file = outside_dir / "secret.txt"
        outside_file.write_text("secret")

        # Create symlink inside allowed dir pointing to outside
        symlink_path = allowed_dir / "sneaky_link"
        try:
            symlink_path.symlink_to(outside_file)
        except OSError:
            pytest.skip("Cannot create symlinks on this system")

        allowed = [allowed_dir]

        # The symlink's resolved path is outside allowed dirs
        assert not is_safe_path(
            symlink_path, allowed
        ), "Symlink escaping allowed dir should be rejected"

    @pytest.mark.security
    @pytest.mark.parametrize(
        "dangerous_system_path",
        [
            "/etc",
            "/proc",
            "/sys",
            "/dev",
            "/boot",
            "C:\\Windows",
            "C:\\System32",
            "C:\\Program Files",
        ],
    )
    def test_rejects_dangerous_system_paths(self, dangerous_system_path: str) -> None:
        """Test that known dangerous system paths are rejected."""
        allowed = [Path.cwd()]  # Normal working directory
        assert not is_safe_path(
            dangerous_system_path, allowed
        ), f"Should reject dangerous system path: {dangerous_system_path}"


class TestGlobExpansionSecurity:
    """Test suite for secure glob pattern expansion."""

    @pytest.mark.security
    @pytest.mark.parametrize(
        "malicious_glob",
        [
            # Path traversal in glob
            "../*.mp4",
            "../../*.mp4",
            "/**/*.mp4",  # Root glob
            "/etc/*",
            "/proc/*",
            # Dangerous system directories
            "/etc/passwd*",
            "/sys/**/*",
            "~/.ssh/*",
            "~/.aws/*",
            # Excessive wildcards (potential DoS)
            "**********",
            "{" * 5 + "test" + "}" * 5,
            # Windows paths
            "C:\\Windows\\*",
            "C:\\System32\\*",
        ],
    )
    def test_rejects_malicious_glob_patterns(
        self, malicious_glob: str, tmp_path: Path
    ) -> None:
        """Test that malicious glob patterns are rejected or return empty."""
        allowed = [tmp_path]
        result = expand_globs([malicious_glob], allowed)
        assert len(result) == 0, f"Should reject or return empty for: {malicious_glob}"

    @pytest.mark.security
    def test_glob_results_validated_against_allowed_dirs(self, tmp_path: Path) -> None:
        """Test that glob results are validated against allowed directories."""
        # Create files in allowed and not-allowed directories
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()
        (allowed_dir / "video1.mp4").touch()
        (allowed_dir / "video2.mp4").touch()

        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        (outside_dir / "video3.mp4").touch()

        # Only allow the 'allowed' directory
        allowed = [allowed_dir]

        # Glob from allowed directory
        results = expand_globs([str(allowed_dir / "*.mp4")], allowed)

        # Should only return files from allowed directory
        assert len(results) == 2
        for path in results:
            assert path.parent == allowed_dir

    @pytest.mark.security
    def test_glob_limit_prevents_dos(self, tmp_path: Path) -> None:
        """Test that glob results are limited to prevent DoS attacks."""
        # Create many files
        for i in range(100):
            (tmp_path / f"video_{i:03d}.mp4").touch()

        allowed = [tmp_path]
        results = expand_globs([str(tmp_path / "*.mp4")], allowed)

        # Results should be limited (check against MAX_GLOB_RESULTS)
        assert len(results) <= MediaFileHandler._MAX_GLOB_RESULTS


class TestFilenamesSanitization:
    """Test suite for filename sanitization."""

    @pytest.mark.security
    @pytest.mark.parametrize(
        "malicious_filename,expected_sanitized",
        [
            # Path traversal in filename
            ("../../../etc/passwd.mp4", "etc_passwd.mp4"),
            ("..\\..\\windows\\system.mp4", "windows_system.mp4"),
            # Shell characters
            ("video;rm -rf /.mp4", "video_rm_-rf_.mp4"),
            ("video|cat /etc/passwd.mp4", "video_cat_etc_passwd.mp4"),
            ("video`whoami`.mp4", "video_whoami_.mp4"),
            ("video$(ls).mp4", "video__ls_.mp4"),
            # Null bytes
            ("video\x00.mp4", "video.mp4"),
            # Control characters
            ("video\x01\x02\x03.mp4", "video.mp4"),
            # Reserved Windows names
            ("CON.mp4", "safe_CON.mp4"),
            ("PRN.mp4", "safe_PRN.mp4"),
            ("AUX.mp4", "safe_AUX.mp4"),
            ("NUL.mp4", "safe_NUL.mp4"),
            ("COM1.mp4", "safe_COM1.mp4"),
            ("LPT1.mp4", "safe_LPT1.mp4"),
            # Multiple dots (potential extension confusion)
            ("video..mp4", "video.mp4"),
            ("video...mp4", "video.mp4"),
            # Leading/trailing dots
            (".hidden.mp4", "hidden.mp4"),
            ("video.", "video"),
            # Empty or whitespace
            ("   ", "sanitized_file"),
            ("", "sanitized_file"),
        ],
    )
    def test_sanitizes_dangerous_filenames(
        self, malicious_filename: str, expected_sanitized: str
    ) -> None:
        """Test that dangerous filenames are properly sanitized."""
        from mediallm.processing.media_file_handler import sanitize_filename

        result = sanitize_filename(malicious_filename)
        # Check that dangerous characters are removed
        assert ".." not in result
        assert "\x00" not in result
        assert ";" not in result
        assert "|" not in result
        assert "`" not in result

    @pytest.mark.security
    def test_sanitize_preserves_valid_characters(self) -> None:
        """Test that sanitization preserves valid filename characters."""
        from mediallm.processing.media_file_handler import sanitize_filename

        valid_filename = "my_video-file.final.mp4"
        result = sanitize_filename(valid_filename)

        # Should preserve alphanumeric, underscore, hyphen, dot
        assert "my_video" in result
        assert "file" in result
        assert ".mp4" in result

    @pytest.mark.security
    def test_sanitize_truncates_long_filenames(self) -> None:
        """Test that very long filenames are truncated safely."""
        from mediallm.processing.media_file_handler import sanitize_filename

        long_filename = "a" * 300 + ".mp4"
        result = sanitize_filename(long_filename)

        assert len(result) <= 255
        assert result.endswith(".mp4")  # Extension should be preserved
